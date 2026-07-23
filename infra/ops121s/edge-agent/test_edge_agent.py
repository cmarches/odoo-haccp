"""Tests unitaires pour haccp-edge-agent (ChirpStack MQTT -> buffer -> bridge Odoo)."""
import http.client
import json
import os
import tempfile
import threading
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from edge_agent import Buffer, Reading, flush_buffer, forward_reading, on_message, parse_uplink


class TestParseUplink(unittest.TestCase):
    def test_frigo_temperature_mapped(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-frigo-positif"},
            "object": {"temperature_1": 3.5, "humidity": 62.1},
        }
        reading = parse_uplink(payload)
        self.assertEqual(
            reading,
            Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192),
        )

    def test_congelateur_temperature_mapped(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-congelateur"},
            "object": {"temperature_1": -18.0},
        }
        reading = parse_uplink(payload)
        self.assertEqual(
            reading,
            Reading(qcp_id=2, value=-18.0, tag="Congelateur_Temperature", quality=192),
        )

    def test_stockage_humidity_mapped(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-stockage-sec"},
            "object": {"humidity": 55.0, "temperature_1": 19.0},
        }
        reading = parse_uplink(payload)
        self.assertEqual(
            reading,
            Reading(qcp_id=3, value=55.0, tag="Stockage_Humidity", quality=192),
        )

    def test_unknown_device_returns_none(self):
        payload = {
            "deviceInfo": {"deviceName": "capteur-inconnu"},
            "object": {"temperature_1": 3.5},
        }
        self.assertIsNone(parse_uplink(payload))

    def test_missing_mapped_field_returns_none(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-frigo-positif"},
            "object": {"humidity": 62.1},
        }
        self.assertIsNone(parse_uplink(payload))

    def test_missing_device_info_returns_none(self):
        self.assertIsNone(parse_uplink({"object": {"temperature_1": 3.5}}))

    def test_missing_object_returns_none(self):
        self.assertIsNone(parse_uplink({"deviceInfo": {"deviceName": "lht65-frigo-positif"}}))

    def test_non_dict_device_info_returns_none(self):
        payload = {
            "deviceInfo": None,
            "object": {"temperature_1": 3.5},
        }
        self.assertIsNone(parse_uplink(payload))

    def test_non_numeric_value_returns_none(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-frigo-positif"},
            "object": {"temperature_1": "N/A"},
        }
        self.assertIsNone(parse_uplink(payload))


class TestBuffer(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.buffer = Buffer(self.db_path)

    def tearDown(self):
        self.buffer.close()
        os.remove(self.db_path)

    def test_enqueue_then_pending_returns_reading(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        self.buffer.enqueue(reading)
        pending = self.buffer.pending()
        self.assertEqual(len(pending), 1)
        _row_id, got = pending[0]
        self.assertEqual(got, reading)

    def test_remove_deletes_row(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        self.buffer.enqueue(reading)
        row_id, _ = self.buffer.pending()[0]
        self.buffer.remove(row_id)
        self.assertEqual(self.buffer.pending(), [])

    def test_pending_preserves_insertion_order(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.enqueue(Reading(qcp_id=2, value=2.0, tag="Congelateur_Temperature", quality=192))
        pending = self.buffer.pending()
        self.assertEqual(
            [r.tag for _row_id, r in pending],
            ["Frigo_Temperature", "Congelateur_Temperature"],
        )

    def test_reopening_same_db_path_preserves_pending_rows(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.close()
        reopened = Buffer(self.db_path)
        self.assertEqual(len(reopened.pending()), 1)
        reopened.close()

    def test_concurrent_enqueue_from_multiple_threads_is_safe(self):
        num_threads = 4
        writes_per_thread = 25
        errors = []

        def worker():
            try:
                for i in range(writes_per_thread):
                    self.buffer.enqueue(
                        Reading(qcp_id=1, value=float(i), tag="Frigo_Temperature", quality=192)
                    )
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(self.buffer.pending()), num_threads * writes_per_thread)


class TestForwardReading(unittest.TestCase):
    def test_success_returns_true(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        with patch("edge_agent.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    def test_non_2xx_status_returns_false(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__enter__.return_value = mock_response
        with patch("edge_agent.urllib.request.urlopen", return_value=mock_response):
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertFalse(result)

    def test_connection_error_returns_false(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        with patch(
            "edge_agent.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertFalse(result)

    def test_sends_expected_json_body(self):
        reading = Reading(qcp_id=2, value=-18.0, tag="Congelateur_Temperature", quality=192)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        with patch("edge_agent.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        sent_request = mock_urlopen.call_args[0][0]
        body = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(
            body,
            {"qcp_id": 2, "value": -18.0, "tag": "Congelateur_Temperature", "quality": 192},
        )

    def test_remote_disconnected_returns_false(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        with patch(
            "edge_agent.urllib.request.urlopen",
            side_effect=http.client.RemoteDisconnected(
                "Remote end closed connection without response"
            ),
        ):
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertFalse(result)

    def test_http_error_returns_false(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        with patch(
            "edge_agent.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://x", code=500, msg="Internal Server Error", hdrs={}, fp=None
            ),
        ):
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertFalse(result)


class TestFlushBuffer(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.buffer = Buffer(self.db_path)

    def tearDown(self):
        self.buffer.close()
        os.remove(self.db_path)

    def test_flush_sends_all_and_empties_buffer(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.enqueue(Reading(qcp_id=2, value=2.0, tag="Congelateur_Temperature", quality=192))
        with patch("edge_agent.forward_reading", return_value=True) as mock_forward:
            flush_buffer(self.buffer, "http://bridge/quality-check", timeout=5)
        self.assertEqual(self.buffer.pending(), [])
        self.assertEqual(mock_forward.call_count, 2)

    def test_flush_stops_at_first_failure_and_keeps_rest(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.enqueue(Reading(qcp_id=2, value=2.0, tag="Congelateur_Temperature", quality=192))
        with patch("edge_agent.forward_reading", return_value=False) as mock_forward:
            flush_buffer(self.buffer, "http://bridge/quality-check", timeout=5)
        self.assertEqual(len(self.buffer.pending()), 2)
        mock_forward.assert_called_once()

    def test_flush_on_empty_buffer_does_nothing(self):
        with patch("edge_agent.forward_reading") as mock_forward:
            flush_buffer(self.buffer, "http://bridge/quality-check", timeout=5)
        mock_forward.assert_not_called()


class TestOnMessage(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.buffer = Buffer(self.db_path)

    def tearDown(self):
        self.buffer.close()
        os.remove(self.db_path)

    @staticmethod
    def _make_msg(topic, payload_dict=None, raw_payload=None):
        msg = MagicMock()
        msg.topic = topic
        if raw_payload is not None:
            msg.payload = raw_payload
        else:
            msg.payload = json.dumps(payload_dict).encode("utf-8")
        return msg

    def test_valid_uplink_enqueues_reading(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-frigo-positif"},
            "object": {"temperature_1": 3.5, "humidity": 62.1, "battery_voltage": 3.6},
        }
        msg = self._make_msg("application/app1/device/xyz/event/up", payload)
        on_message(MagicMock(), {"buffer": self.buffer}, msg)
        pending = self.buffer.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0][1].tag, "Frigo_Temperature")
        self.assertEqual(pending[0][1].value, 3.5)

    def test_unmapped_device_does_not_enqueue(self):
        payload = {"deviceInfo": {"deviceName": "unknown-device"}, "object": {"temperature_1": 3.5}}
        msg = self._make_msg("application/app1/device/xyz/event/up", payload)
        on_message(MagicMock(), {"buffer": self.buffer}, msg)
        self.assertEqual(self.buffer.pending(), [])

    def test_invalid_json_does_not_raise_and_does_not_enqueue(self):
        msg = self._make_msg("application/app1/device/xyz/event/up", raw_payload=b"not json")
        on_message(MagicMock(), {"buffer": self.buffer}, msg)
        self.assertEqual(self.buffer.pending(), [])

    def test_missing_buffer_in_userdata_does_not_raise(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-frigo-positif"},
            "object": {"temperature_1": 3.5},
        }
        msg = self._make_msg("application/app1/device/xyz/event/up", payload)
        on_message(MagicMock(), {}, msg)


if __name__ == "__main__":
    unittest.main()

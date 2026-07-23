"""Tests unitaires pour haccp-edge-agent (ChirpStack MQTT -> buffer -> bridge Odoo)."""
import os
import tempfile
import threading
import unittest

from edge_agent import Buffer, Reading, parse_uplink


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


if __name__ == "__main__":
    unittest.main()

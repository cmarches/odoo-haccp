import importlib.util
import io
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

MODULE_PATH = Path(__file__).resolve().parent.parent / "demo-simulate-sensor.py"
_spec = importlib.util.spec_from_file_location("demo_simulate_sensor", MODULE_PATH)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


class TestListDevices(unittest.TestCase):
    def test_list_devices_prints_known_devices_and_returns_0(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = demo.main(["--list-devices"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("lht65-frigo-positif", output)
        self.assertIn("lht65-congelateur", output)
        self.assertIn("lht65-stockage-sec", output)


class TestBuildSimulateUrl(unittest.TestCase):
    def test_builds_correct_url(self):
        url = demo.build_simulate_url("eu1", "haccp-restaurant-poc", "lht65-frigo-positif")
        self.assertEqual(
            url,
            "https://eu1.cloud.thethings.network/api/v3/as/applications/"
            "haccp-restaurant-poc/devices/lht65-frigo-positif/up/simulate",
        )


class TestBuildUplinkBody(unittest.TestCase):
    def test_builds_correct_body(self):
        body = demo.build_uplink_body(
            "lht65-frigo-positif", "haccp-restaurant-poc", "temperature_1", 12.0
        )
        self.assertEqual(body["end_device_ids"]["device_id"], "lht65-frigo-positif")
        self.assertEqual(
            body["end_device_ids"]["application_ids"]["application_id"],
            "haccp-restaurant-poc",
        )
        self.assertEqual(body["uplink_message"]["decoded_payload"], {"temperature_1": 12.0})
        self.assertEqual(body["uplink_message"]["f_port"], 1)


class TestMainMissingApiKey(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_exits_1_without_api_key(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 1)
        self.assertIn("TTN_API_KEY", stderr.getvalue())


class TestMainMissingArgs(unittest.TestCase):
    @patch.dict(os.environ, {"TTN_API_KEY": "fake-key"}, clear=True)
    def test_exits_1_without_device_or_value(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main([])
        self.assertEqual(code, 1)


class TestSendSimulatedUplink(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_sends_post_with_bearer_auth_and_returns_status_and_body(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        status, body = demo.send_simulated_uplink(
            "https://eu1.cloud.thethings.network/api/v3/as/applications/x/devices/y/up/simulate",
            "fake-api-key",
            {"end_device_ids": {"device_id": "y"}},
        )

        self.assertEqual(status, 200)
        self.assertEqual(body, '{"ok": true}')
        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.get_method(), "POST")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer fake-api-key")
        self.assertEqual(sent_request.get_header("Content-type"), "application/json")

    @patch("urllib.request.urlopen")
    def test_http_error_returns_status_and_error_body(self, mock_urlopen):
        error_body = io.BytesIO(b'{"error": "permission_denied"}')
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://eu1.cloud.thethings.network/...",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=error_body,
        )

        status, body = demo.send_simulated_uplink(
            "https://eu1.cloud.thethings.network/api/v3/as/applications/x/devices/y/up/simulate",
            "fake-api-key",
            {"end_device_ids": {"device_id": "y"}},
        )

        self.assertEqual(status, 403)
        self.assertEqual(body, '{"error": "permission_denied"}')


if __name__ == "__main__":
    unittest.main()

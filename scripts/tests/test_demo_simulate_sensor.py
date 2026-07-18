import importlib.util
import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()

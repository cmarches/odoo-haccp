import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parent.parent / "demo-simulate-sensor-chirpstack.py"
_spec = importlib.util.spec_from_file_location("demo_simulate_sensor_chirpstack", MODULE_PATH)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


class TestBuildTopic(unittest.TestCase):
    def test_builds_correct_topic(self):
        topic = demo.build_topic("haccp-restaurant-poc", "lht65-frigo-positif")
        self.assertEqual(
            topic, "application/haccp-restaurant-poc/device/lht65-frigo-positif/event/up"
        )


class TestBuildUplinkPayload(unittest.TestCase):
    def test_builds_correct_payload_temperature(self):
        payload = demo.build_uplink_payload("lht65-frigo-positif", "temperature_1", 12.0)
        self.assertEqual(
            payload,
            {"deviceInfo": {"deviceName": "lht65-frigo-positif"}, "object": {"temperature_1": 12.0}},
        )

    def test_builds_correct_payload_humidity(self):
        payload = demo.build_uplink_payload("lht65-stockage-sec", "humidity", 90.0)
        self.assertEqual(
            payload,
            {"deviceInfo": {"deviceName": "lht65-stockage-sec"}, "object": {"humidity": 90.0}},
        )


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


class TestMainMissingArgs(unittest.TestCase):
    def test_exits_1_without_device_or_value(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main([])
        self.assertEqual(code, 1)
        self.assertIn("ERREUR", stderr.getvalue())


class TestMqttPortFromEnv(unittest.TestCase):
    def test_invalid_mqtt_port_env_falls_back_to_default(self):
        stderr = io.StringIO()
        with patch.dict("os.environ", {"MQTT_PORT": "not-a-number"}), patch("sys.stderr", stderr):
            code = demo.main(["--list-devices"])
        self.assertEqual(code, 0)
        self.assertIn("AVERTISSEMENT", stderr.getvalue())


class TestMainSuccess(unittest.TestCase):
    def test_success_publishes_and_returns_0(self):
        stdout = io.StringIO()
        with patch.object(demo, "publish_uplink") as mock_publish, patch("sys.stdout", stdout):
            code = demo.main([
                "--device", "lht65-frigo-positif",
                "--value", "12.0",
                "--application-id", "haccp-restaurant-poc",
                "--mqtt-host", "127.0.0.1",
                "--mqtt-port", "1883",
            ])
        self.assertEqual(code, 0)
        mock_publish.assert_called_once_with(
            "127.0.0.1",
            1883,
            "application/haccp-restaurant-poc/device/lht65-frigo-positif/event/up",
            {"deviceInfo": {"deviceName": "lht65-frigo-positif"}, "object": {"temperature_1": 12.0}},
        )
        self.assertIn("OK", stdout.getvalue())

    def test_humidity_field_builds_correct_payload(self):
        with patch.object(demo, "publish_uplink") as mock_publish:
            demo.main([
                "--device", "lht65-stockage-sec",
                "--value", "90.0",
                "--field", "humidity",
            ])
        called_payload = mock_publish.call_args[0][3]
        self.assertEqual(
            called_payload,
            {"deviceInfo": {"deviceName": "lht65-stockage-sec"}, "object": {"humidity": 90.0}},
        )


class TestMainMqttError(unittest.TestCase):
    def test_mqtt_error_prints_message_and_returns_1(self):
        stderr = io.StringIO()
        with patch.object(demo, "publish_uplink", side_effect=ConnectionRefusedError("refused")), \
             patch("sys.stderr", stderr):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 1)
        self.assertIn("ERREUR MQTT", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

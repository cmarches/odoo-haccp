import importlib.util
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()

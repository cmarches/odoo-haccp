"""Tests unitaires pour haccp-edge-agent (ChirpStack MQTT -> buffer -> bridge Odoo)."""
import unittest

from edge_agent import Reading, parse_uplink


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


if __name__ == "__main__":
    unittest.main()

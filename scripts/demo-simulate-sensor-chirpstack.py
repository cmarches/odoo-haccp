#!/usr/bin/env python3
"""
Simule un uplink ChirpStack (publication MQTT directe) pour declencher le
pipeline HACCP complet en demo : Mosquitto -> haccp-edge-agent -> bridge ->
Odoo -> SMS.

Contrairement a demo-simulate-sensor.py (TTN), ChirpStack n'expose pas d'API
"simulate uplink" : ce script publie directement sur le topic MQTT que
ChirpStack publierait apres avoir decode un vrai uplink radio. Le codec
ChirpStack (device profile) n'est donc PAS exerce par ce script — seule la
chaine MQTT -> haccp-edge-agent -> Odoo l'est. Voir
docs/operations/chirpstack-deploiement-ops121s.md pour valider le codec
separement une fois un vrai device profile configure.

Usage:
  python3 demo-simulate-sensor-chirpstack.py --device lht65-frigo-positif --value 12.0
  python3 demo-simulate-sensor-chirpstack.py --device lht65-stockage-sec --value 90.0 --field humidity
  python3 demo-simulate-sensor-chirpstack.py --list-devices

Variables d'environnement :
  CHIRPSTACK_APPLICATION_ID  (optionnel, defaut "haccp-restaurant-poc")
  MQTT_HOST                  (optionnel, defaut "127.0.0.1")
  MQTT_PORT                  (optionnel, defaut 1883)
"""
import argparse
import json
import os
import sys

KNOWN_DEVICES = {
    "lht65-frigo-positif": {"field": "temperature_1", "seuil": "<= 4°C", "valeur_demo": 12.0},
    "lht65-congelateur": {"field": "temperature_1", "seuil": "<= -15°C", "valeur_demo": -5.0},
    "lht65-stockage-sec": {"field": "humidity", "seuil": "<= 75%", "valeur_demo": 90.0},
}


def build_topic(application_id, device_id):
    return f"application/{application_id}/device/{device_id}/event/up"


def build_uplink_payload(device_id, field, value):
    return {
        "deviceInfo": {"deviceName": device_id},
        "object": {field: value},
    }


if __name__ == "__main__":
    pass

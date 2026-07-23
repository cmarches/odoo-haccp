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


def print_list_devices():
    print("Devices connus :")
    for device_id, info in KNOWN_DEVICES.items():
        print(
            f"  {device_id:<22} champ={info['field']:<14} "
            f"seuil={info['seuil']:<10} valeur demo suggeree={info['valeur_demo']}"
        )


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Simule un uplink ChirpStack (MQTT direct) pour demo HACCP"
    )
    parser.add_argument("--device", help="deviceName ChirpStack (ex: lht65-frigo-positif)")
    parser.add_argument("--value", type=float, help="Valeur a injecter")
    parser.add_argument(
        "--field",
        default="temperature_1",
        choices=["temperature_1", "humidity"],
        help="Champ de l'objet decode a injecter (defaut: temperature_1)",
    )
    parser.add_argument(
        "--application-id",
        dest="application_id",
        default=os.environ.get("CHIRPSTACK_APPLICATION_ID", "haccp-restaurant-poc"),
        help="Application ID ChirpStack (defaut: variable CHIRPSTACK_APPLICATION_ID ou haccp-restaurant-poc)",
    )
    parser.add_argument(
        "--mqtt-host",
        dest="mqtt_host",
        default=os.environ.get("MQTT_HOST", "127.0.0.1"),
        help="Hote du broker MQTT (defaut: variable MQTT_HOST ou 127.0.0.1)",
    )
    parser.add_argument(
        "--mqtt-port",
        dest="mqtt_port",
        type=int,
        default=int(os.environ.get("MQTT_PORT", "1883")),
        help="Port du broker MQTT (defaut: variable MQTT_PORT ou 1883)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Affiche les devices connus avec leurs seuils et quitte",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.list_devices:
        print_list_devices()
        return 0

    if not args.device or args.value is None:
        print(
            "ERREUR : --device et --value sont requis (ou utiliser --list-devices)",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    pass

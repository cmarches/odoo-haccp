#!/usr/bin/env python3
"""
Simule un uplink LoRaWAN via l'API TTN pour déclencher le pipeline HACCP
complet en démo : TTN -> MQTT -> vNode -> bridge -> Odoo -> SMS.

Usage:
  python3 demo-simulate-sensor.py --device lht65-frigo-positif --value 12.0
  python3 demo-simulate-sensor.py --list-devices

Variables d'environnement :
  TTN_API_KEY   (requis)  Clé API TTN avec droit "Write application traffic"
  TTN_APP_ID    (optionnel, défaut "haccp-restaurant-poc")
  TTN_REGION    (optionnel, défaut "eu1")
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

KNOWN_DEVICES = {
    "lht65-frigo-positif": {"field": "temperature_1", "seuil": "<= 4°C", "valeur_demo": 12.0},
    "lht65-congelateur": {"field": "temperature_1", "seuil": "<= -15°C", "valeur_demo": -5.0},
    "lht65-stockage-sec": {"field": "humidity", "seuil": "<= 75%", "valeur_demo": 90.0},
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
        description="Simule un uplink LoRaWAN via l'API TTN pour démo HACCP"
    )
    parser.add_argument("--device", help="device_id TTN (ex: lht65-frigo-positif)")
    parser.add_argument("--value", type=float, help="Valeur à injecter")
    parser.add_argument(
        "--field", default="temperature_1", choices=["temperature_1", "humidity"]
    )
    parser.add_argument(
        "--app-id", dest="app_id", default=os.environ.get("TTN_APP_ID", "haccp-restaurant-poc")
    )
    parser.add_argument("--region", default=os.environ.get("TTN_REGION", "eu1"))
    parser.add_argument("--list-devices", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.list_devices:
        print_list_devices()
        return 0

    print("ERREUR : --device et --value sont requis (ou utiliser --list-devices)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

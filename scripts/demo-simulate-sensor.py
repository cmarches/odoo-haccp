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


def build_simulate_url(region, app_id, device_id):
    return (
        f"https://{region}.cloud.thethings.network/api/v3/as/applications/"
        f"{app_id}/devices/{device_id}/up/simulate"
    )


def build_uplink_body(device_id, app_id, field, value):
    return {
        "end_device_ids": {
            "device_id": device_id,
            "application_ids": {"application_id": app_id},
        },
        "uplink_message": {
            "f_port": 1,
            "decoded_payload": {field: value},
        },
    }


def send_simulated_uplink(url, api_key, body, timeout=10):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


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

    if not args.device or args.value is None:
        print(
            "ERREUR : --device et --value sont requis (ou utiliser --list-devices)",
            file=sys.stderr,
        )
        return 1

    api_key = os.environ.get("TTN_API_KEY")
    if not api_key:
        print(
            "ERREUR : variable d'environnement TTN_API_KEY manquante.\n"
            "Génère une clé dans la console TTN : Application -> API keys -> "
            'droit "Write application traffic (uplink and downlink)", puis :\n'
            "  export TTN_API_KEY=...",
            file=sys.stderr,
        )
        return 1

    print(f"Envoi d'un uplink simulé — device={args.device} {args.field}={args.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

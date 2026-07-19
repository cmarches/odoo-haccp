#!/usr/bin/env python3
"""
Simule un uplink LoRaWAN via l'API TTN pour déclencher le pipeline HACCP
complet en démo : TTN -> MQTT -> vNode -> bridge -> Odoo -> SMS.

Usage:
  python3 demo-simulate-sensor.py --device lht65-frigo-positif --value 12.0
  python3 demo-simulate-sensor.py --device lht65-stockage-sec --value 90.0 --field humidity
  python3 demo-simulate-sensor.py --list-devices

Variables d'environnement :
  TTN_API_KEY   (requis)  Clé API TTN avec droit "Write application traffic"
  TTN_APP_ID    (optionnel, défaut "haccp-restaurant-poc")
  TTN_REGION    (optionnel, défaut "eu1")
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_TEMPERATURE = 4.0
DEFAULT_HUMIDITY = 50.0
DEFAULT_BATTERY_VOLTAGE = 3.6

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


def encode_lht65_frm_payload(temperature_1=None, humidity=None, battery_voltage=None):
    """Encode 6 bytes décodés par le formatter uplink TTN du device
    lht65-frigo-positif : [0-1] battery_voltage (mV, 14 bits) [2-3]
    temperature_1*100 (int16 signé) [4-5] humidity*10 (uint16). Le formatter
    ignore tout octet au-delà de l'index 5 (évite le crash du décodeur
    officiel sur les bytes du capteur externe)."""
    if temperature_1 is None:
        temperature_1 = DEFAULT_TEMPERATURE
    if humidity is None:
        humidity = DEFAULT_HUMIDITY
    if battery_voltage is None:
        battery_voltage = DEFAULT_BATTERY_VOLTAGE

    battery_raw = int(round(battery_voltage * 1000)) & 0x3FFF
    temp_raw = int(round(temperature_1 * 100))
    if temp_raw < 0:
        temp_raw += 0x10000
    humidity_raw = int(round(humidity * 10))

    payload = bytes([
        (battery_raw >> 8) & 0xFF, battery_raw & 0xFF,
        (temp_raw >> 8) & 0xFF, temp_raw & 0xFF,
        (humidity_raw >> 8) & 0xFF, humidity_raw & 0xFF,
    ])
    return base64.b64encode(payload).decode("ascii")


def build_uplink_body(device_id, app_id, field, value):
    frm_payload = encode_lht65_frm_payload(**{field: value})
    return {
        "end_device_ids": {
            "device_id": device_id,
            "application_ids": {"application_id": app_id},
        },
        "uplink_message": {
            "f_port": 1,
            "frm_payload": frm_payload,
            # Requis par la validation TTN (uplink_message.settings) : EU868
            # SF7BW125, valeurs par défaut LoRaWAN standard pour ce simulateur.
            "settings": {
                "data_rate": {
                    "lora": {
                        "bandwidth": 125000,
                        "spreading_factor": 7,
                    },
                },
                "frequency": "868100000",
            },
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
        "--field",
        default="temperature_1",
        choices=["temperature_1", "humidity"],
        help="Champ du decoded_payload à injecter (défaut: temperature_1)",
    )
    parser.add_argument(
        "--app-id",
        dest="app_id",
        default=os.environ.get("TTN_APP_ID", "haccp-restaurant-poc"),
        help="Application ID TTN (défaut: variable TTN_APP_ID ou haccp-restaurant-poc)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("TTN_REGION", "eu1"),
        help="Région TTN (défaut: variable TTN_REGION ou eu1)",
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
    url = build_simulate_url(args.region, args.app_id, args.device)
    body = build_uplink_body(args.device, args.app_id, args.field, args.value)
    print(f"POST {url}")

    try:
        status, resp_text = send_simulated_uplink(url, api_key, body)
    except urllib.error.URLError as e:
        print(f"ERREUR réseau : {e}", file=sys.stderr)
        return 1

    if status >= 400:
        print(f"ERREUR TTN — HTTP {status}\n{resp_text}", file=sys.stderr)
        return 1

    print(f"OK — TTN a accepté l'uplink simulé (HTTP {status})")
    print("Observe maintenant en direct :")
    print("  - Odoo (quality.check / quality.alert) sur http://192.168.1.182:8029")
    print("  - Le téléphone configuré pour les SMS d'alerte")
    return 0


if __name__ == "__main__":
    sys.exit(main())

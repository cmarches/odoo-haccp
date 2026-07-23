#!/usr/bin/env python3
"""
HACCP Edge Agent — souscrit aux uplinks ChirpStack (MQTT), bufferise
localement en SQLite, et relaie vers haccp-odoo-bridge en HTTP.

Remplace vNode (MqttClient + RestApiClient) sur l'edge. Ne modifie pas
le contrat de haccp-odoo-bridge : POST /quality-check,
body {"qcp_id": int, "value": float, "tag": str, "quality": int}.
"""
import json
import logging
import os
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("haccp-edge-agent")

QUALITY_GOOD = 192

# (device ChirpStack deviceInfo.deviceName) -> champ decode a lire dans
# "object", tag Odoo correspondant, et qcp_id du quality.point associe.
# Reproduit exactement les 3 (device, champ) actuellement relayes par
# vNode RestApiClient (voir infra/ops121s/vnode/config/RestApiClient-config.n3c).
DEVICE_QCP_MAP = {
    "lht65-frigo-positif": {
        "field": "temperature_1", "tag": "Frigo_Temperature", "qcp_id": 1,
    },
    "lht65-congelateur": {
        "field": "temperature_1", "tag": "Congelateur_Temperature", "qcp_id": 2,
    },
    "lht65-stockage-sec": {
        "field": "humidity", "tag": "Stockage_Humidity", "qcp_id": 3,
    },
}


@dataclass(frozen=True)
class Reading:
    qcp_id: int
    value: float
    tag: str
    quality: int = QUALITY_GOOD


def parse_uplink(payload: dict) -> Optional[Reading]:
    device_name = payload.get("deviceInfo", {}).get("deviceName")
    mapping = DEVICE_QCP_MAP.get(device_name)
    if mapping is None:
        return None
    obj = payload.get("object") or {}
    value = obj.get(mapping["field"])
    if value is None:
        return None
    return Reading(qcp_id=mapping["qcp_id"], value=float(value), tag=mapping["tag"])


if __name__ == "__main__":
    pass

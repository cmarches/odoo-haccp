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
    try:
        device_name = payload.get("deviceInfo", {}).get("deviceName")
        mapping = DEVICE_QCP_MAP.get(device_name)
        if mapping is None:
            return None
        obj = payload.get("object") or {}
        value = obj.get(mapping["field"])
        if value is None:
            return None
        return Reading(qcp_id=mapping["qcp_id"], value=float(value), tag=mapping["tag"])
    except (AttributeError, TypeError, ValueError):
        return None


class Buffer:
    """File d'attente locale persistante (SQLite) pour les mesures a relayer."""

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                qcp_id INTEGER NOT NULL,
                value REAL NOT NULL,
                tag TEXT NOT NULL,
                quality INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def enqueue(self, reading: Reading) -> None:
        self._conn.execute(
            "INSERT INTO pending_readings (created_at, qcp_id, value, tag, quality) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                reading.qcp_id,
                reading.value,
                reading.tag,
                reading.quality,
            ),
        )
        self._conn.commit()

    def pending(self) -> List[Tuple[int, Reading]]:
        cursor = self._conn.execute(
            "SELECT id, qcp_id, value, tag, quality FROM pending_readings ORDER BY id ASC"
        )
        return [
            (row[0], Reading(qcp_id=row[1], value=row[2], tag=row[3], quality=row[4]))
            for row in cursor.fetchall()
        ]

    def remove(self, row_id: int) -> None:
        self._conn.execute("DELETE FROM pending_readings WHERE id = ?", (row_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


if __name__ == "__main__":
    pass

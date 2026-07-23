#!/usr/bin/env python3
"""
HACCP Edge Agent — souscrit aux uplinks ChirpStack (MQTT), bufferise
localement en SQLite, et relaie vers haccp-odoo-bridge en HTTP.

Remplace vNode (MqttClient + RestApiClient) sur l'edge. Ne modifie pas
le contrat de haccp-odoo-bridge : POST /quality-check,
body {"qcp_id": int, "value": float, "tag": str, "quality": int}.
"""
import http.client
import json
import logging
import os
import sqlite3
import threading
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
    """File d'attente locale persistante (SQLite) pour les mesures a relayer.

    Partagee entre le thread reseau MQTT (paho-mqtt loop_start, qui appelle
    enqueue() depuis on_message) et le thread principal (boucle de flush qui
    appelle pending()/remove()). check_same_thread=False leve l'interdiction
    sqlite3 par defaut, et un verrou grossier serialise les acces car une
    connexion sqlite3 n'est pas surete pour une execution concurrente de
    requetes depuis plusieurs threads a la fois. Charge faible (quelques
    capteurs toutes les 10-20 min) : un verrou unique par methode suffit.
    """

    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id, qcp_id, value, tag, quality FROM pending_readings ORDER BY id ASC"
            )
            rows = cursor.fetchall()
        return [
            (row[0], Reading(qcp_id=row[1], value=row[2], tag=row[3], quality=row[4]))
            for row in rows
        ]

    def remove(self, row_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM pending_readings WHERE id = ?", (row_id,))
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def forward_reading(reading: Reading, bridge_url: str, timeout: float) -> bool:
    body = json.dumps(
        {
            "qcp_id": reading.qcp_id,
            "value": reading.value,
            "tag": reading.tag,
            "quality": reading.quality,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        bridge_url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ok = 200 <= resp.status < 300
            if not ok:
                log.warning("Bridge a repondu %s pour tag=%s", resp.status, reading.tag)
            return ok
    except (urllib.error.URLError, TimeoutError, http.client.HTTPException) as e:
        log.warning("Echec envoi vers le bridge (tag=%s): %s", reading.tag, e)
        return False


def flush_buffer(buffer: Buffer, bridge_url: str, timeout: float) -> None:
    """Envoie les mesures en attente dans l'ordre, s'arrete au premier echec
    pour preserver l'ordre et eviter de marteler un backend indisponible."""
    for row_id, reading in buffer.pending():
        if not forward_reading(reading, bridge_url, timeout):
            break
        buffer.remove(row_id)


def on_message(client, userdata, msg) -> None:
    """Callback MQTT (signature paho: client, userdata, msg).
    userdata doit etre {"buffer": Buffer(...)} (voir main())."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.warning("Payload MQTT invalide sur %s: %s", msg.topic, e)
        return
    reading = parse_uplink(payload)
    if reading is None:
        log.debug("Uplink ignore (device/champ non mappe): %s", msg.topic)
        return
    userdata["buffer"].enqueue(reading)
    log.info("Mesure mise en file: tag=%s value=%s", reading.tag, reading.value)


if __name__ == "__main__":
    pass

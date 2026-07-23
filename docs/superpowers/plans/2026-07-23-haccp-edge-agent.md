# HACCP Edge Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `haccp-edge-agent`, a Python service that replaces vNode on the edge: it subscribes to ChirpStack uplink events over MQTT, maps sensor readings to HACCP quality control points, buffers them locally against backend outages, and forwards them to the existing `haccp-odoo-bridge` over HTTP.

**Architecture:** Single-file service with pure, independently testable functions (`parse_uplink`, `Buffer`, `forward_reading`, `flush_buffer`, `on_message`) wired together in `main()`. Every received uplink is written to a local SQLite queue first; a periodic loop is the *only* code path that ever calls the bridge, in FIFO order, stopping on the first failure to avoid reordering or hammering a down backend. This mirrors the resilience decision in `docs/superpowers/specs/2026-07-22-architecture-sans-vnode-design.md` §6-7: `haccp-odoo-bridge` is unmodified — the agent reproduces its existing HTTP contract (`POST /quality-check`, body `{qcp_id, value, tag, quality}`).

**Tech Stack:** Python 3, stdlib only for all business logic (`sqlite3`, `urllib.request`, `json`, `dataclasses`) — matches the existing `bridge.py` convention of no external dependencies. `paho-mqtt` is the one external dependency, imported only inside `main()`, so the full unit test suite runs without installing it.

**Scope note:** This plan covers the agent software only. Adding ChirpStack to `infra/ops121s/docker-compose.yml` and migrating the live POC off vNode are separate follow-ups (spec §12, items 2-3) — deliberately out of scope here so this plan produces working, independently testable software on its own.

---

## Context an engineer needs before starting

- **Design spec:** `docs/superpowers/specs/2026-07-22-architecture-sans-vnode-design.md` — read §6 (architecture cible), §7 (impact sur les composants existants) and §11 (questions ouvertes) before starting.
- **Bridge contract (unmodified target):** `infra/ops121s/odoo-bridge/bridge.py` — `POST /quality-check` expects JSON `{"qcp_id": int, "value": float, "tag": str, "quality": int}`. Any `quality < 64` is treated as bad and skipped by the bridge itself — the agent should always send `quality=192` (Good), since a decoded ChirpStack uplink has already passed LoRaWAN MIC validation.
- **Existing device → tag → QCP mapping** (from the vNode config being replaced, `docs/operations/architecture-ops121s-vnode.md` §3.1-3.2 and `infra/ops121s/vnode/config/RestApiClient-config.n3c`) — only these three (device, field) pairs are ever forwarded today, and the agent must reproduce exactly this set, not the full 6-tag list:

  | Device (ChirpStack `deviceInfo.deviceName`) | Decoded field (`object.<field>`) | Tag | `qcp_id` |
  |---|---|---|---|
  | `lht65-frigo-positif` | `temperature_1` | `Frigo_Temperature` | 1 |
  | `lht65-congelateur` | `temperature_1` | `Congelateur_Temperature` | 2 |
  | `lht65-stockage-sec` | `humidity` | `Stockage_Humidity` | 3 |

- **ChirpStack uplink event shape (assumption, not yet verified against a live broker):** ChirpStack v4's MQTT integration publishes uplinks on topic `application/{application_id}/device/{dev_eui}/event/up` with a JSON body containing `deviceInfo.deviceName` (string) and `object` (dict of already-decoded fields, produced by the device profile's codec — same decode logic as the TTN formatter documented in `architecture-ops121s-vnode.md` §3.1, just configured as a ChirpStack codec instead). **This must be validated against a real ChirpStack instance once deployed** (tracked in Task 6 as an explicit follow-up note, and in spec §11 question 3) — if field names differ, only `parse_uplink()` (Task 1) needs updating, nothing else.
- **Known limitation carried over from the current architecture, not a regression:** neither vNode's buffer nor this agent's buffer preserves the original sensor timestamp through a replay — a buffered-then-replayed `quality.check` gets `create_date` at replay time in Odoo, not at measurement time. Out of scope to fix here.
- **Test pattern to follow:** `infra/ops121s/odoo-bridge/test_bridge_oca.py` — plain `unittest.TestCase`, `unittest.mock.patch`/`MagicMock`, test file lives next to the module it tests and imports it directly (`import edge_agent`).

---

## Task 1: `Reading`, `DEVICE_QCP_MAP`, and `parse_uplink()`

**Files:**
- Create: `infra/ops121s/edge-agent/edge_agent.py`
- Create: `infra/ops121s/edge-agent/test_edge_agent.py`

- [ ] **Step 1: Write the failing tests**

Create `infra/ops121s/edge-agent/test_edge_agent.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'edge_agent'`

- [ ] **Step 3: Write minimal implementation**

Create `infra/ops121s/edge-agent/edge_agent.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/edge-agent/edge_agent.py infra/ops121s/edge-agent/test_edge_agent.py
git commit -m "feat(edge-agent): add Reading, DEVICE_QCP_MAP, and parse_uplink"
```

---

## Task 2: `Buffer` (file d'attente SQLite locale)

**Files:**
- Modify: `infra/ops121s/edge-agent/test_edge_agent.py`
- Modify: `infra/ops121s/edge-agent/edge_agent.py`

- [ ] **Step 1: Write the failing tests**

Add to the top imports of `test_edge_agent.py` (replace the existing `import unittest` line with):

```python
import os
import tempfile
import unittest

from edge_agent import Buffer, Reading, parse_uplink
```

Add to `test_edge_agent.py`:

```python
class TestBuffer(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.buffer = Buffer(self.db_path)

    def tearDown(self):
        self.buffer.close()
        os.remove(self.db_path)

    def test_enqueue_then_pending_returns_reading(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        self.buffer.enqueue(reading)
        pending = self.buffer.pending()
        self.assertEqual(len(pending), 1)
        _row_id, got = pending[0]
        self.assertEqual(got, reading)

    def test_remove_deletes_row(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        self.buffer.enqueue(reading)
        row_id, _ = self.buffer.pending()[0]
        self.buffer.remove(row_id)
        self.assertEqual(self.buffer.pending(), [])

    def test_pending_preserves_insertion_order(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.enqueue(Reading(qcp_id=2, value=2.0, tag="Congelateur_Temperature", quality=192))
        pending = self.buffer.pending()
        self.assertEqual(
            [r.tag for _row_id, r in pending],
            ["Frigo_Temperature", "Congelateur_Temperature"],
        )

    def test_reopening_same_db_path_preserves_pending_rows(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.close()
        reopened = Buffer(self.db_path)
        self.assertEqual(len(reopened.pending()), 1)
        reopened.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: FAIL with `ImportError: cannot import name 'Buffer' from 'edge_agent'`

- [ ] **Step 3: Write minimal implementation**

Add to `edge_agent.py`, after the `parse_uplink` function:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/edge-agent/test_edge_agent.py infra/ops121s/edge-agent/edge_agent.py
git commit -m "feat(edge-agent): add SQLite-backed Buffer for pending readings"
```

---

## Task 3: `forward_reading()` (POST HTTP vers le bridge)

**Files:**
- Modify: `infra/ops121s/edge-agent/test_edge_agent.py`
- Modify: `infra/ops121s/edge-agent/edge_agent.py`

- [ ] **Step 1: Write the failing tests**

Add to the top imports of `test_edge_agent.py`:

```python
import json
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from edge_agent import Buffer, Reading, forward_reading, parse_uplink
```

Add to `test_edge_agent.py`:

```python
class TestForwardReading(unittest.TestCase):
    def test_success_returns_true(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        with patch("edge_agent.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    def test_non_2xx_status_returns_false(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__enter__.return_value = mock_response
        with patch("edge_agent.urllib.request.urlopen", return_value=mock_response):
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertFalse(result)

    def test_connection_error_returns_false(self):
        reading = Reading(qcp_id=1, value=3.5, tag="Frigo_Temperature", quality=192)
        with patch(
            "edge_agent.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        self.assertFalse(result)

    def test_sends_expected_json_body(self):
        reading = Reading(qcp_id=2, value=-18.0, tag="Congelateur_Temperature", quality=192)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        with patch("edge_agent.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            forward_reading(reading, "http://127.0.0.1:5001/quality-check", timeout=5)
        sent_request = mock_urlopen.call_args[0][0]
        body = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(
            body,
            {"qcp_id": 2, "value": -18.0, "tag": "Congelateur_Temperature", "quality": 192},
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: FAIL with `ImportError: cannot import name 'forward_reading' from 'edge_agent'`

- [ ] **Step 3: Write minimal implementation**

Add to `edge_agent.py`, after the `Buffer` class:

```python
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
    except (urllib.error.URLError, TimeoutError) as e:
        log.warning("Echec envoi vers le bridge (tag=%s): %s", reading.tag, e)
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/edge-agent/test_edge_agent.py infra/ops121s/edge-agent/edge_agent.py
git commit -m "feat(edge-agent): add forward_reading HTTP POST to haccp-odoo-bridge"
```

---

## Task 4: `flush_buffer()` (vidange ordonnee, s'arrete au premier echec)

**Files:**
- Modify: `infra/ops121s/edge-agent/test_edge_agent.py`
- Modify: `infra/ops121s/edge-agent/edge_agent.py`

- [ ] **Step 1: Write the failing tests**

Update the import line in `test_edge_agent.py` to:

```python
from edge_agent import Buffer, Reading, flush_buffer, forward_reading, parse_uplink
```

Add to `test_edge_agent.py`:

```python
class TestFlushBuffer(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.buffer = Buffer(self.db_path)

    def tearDown(self):
        self.buffer.close()
        os.remove(self.db_path)

    def test_flush_sends_all_and_empties_buffer(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.enqueue(Reading(qcp_id=2, value=2.0, tag="Congelateur_Temperature", quality=192))
        with patch("edge_agent.forward_reading", return_value=True) as mock_forward:
            flush_buffer(self.buffer, "http://bridge/quality-check", timeout=5)
        self.assertEqual(self.buffer.pending(), [])
        self.assertEqual(mock_forward.call_count, 2)

    def test_flush_stops_at_first_failure_and_keeps_rest(self):
        self.buffer.enqueue(Reading(qcp_id=1, value=1.0, tag="Frigo_Temperature", quality=192))
        self.buffer.enqueue(Reading(qcp_id=2, value=2.0, tag="Congelateur_Temperature", quality=192))
        with patch("edge_agent.forward_reading", return_value=False) as mock_forward:
            flush_buffer(self.buffer, "http://bridge/quality-check", timeout=5)
        self.assertEqual(len(self.buffer.pending()), 2)
        mock_forward.assert_called_once()

    def test_flush_on_empty_buffer_does_nothing(self):
        with patch("edge_agent.forward_reading") as mock_forward:
            flush_buffer(self.buffer, "http://bridge/quality-check", timeout=5)
        mock_forward.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: FAIL with `ImportError: cannot import name 'flush_buffer' from 'edge_agent'`

- [ ] **Step 3: Write minimal implementation**

Add to `edge_agent.py`, after `forward_reading`:

```python
def flush_buffer(buffer: Buffer, bridge_url: str, timeout: float) -> None:
    """Envoie les mesures en attente dans l'ordre, s'arrete au premier echec
    pour preserver l'ordre et eviter de marteler un backend indisponible."""
    for row_id, reading in buffer.pending():
        if not forward_reading(reading, bridge_url, timeout):
            break
        buffer.remove(row_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: PASS (18 tests)

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/edge-agent/test_edge_agent.py infra/ops121s/edge-agent/edge_agent.py
git commit -m "feat(edge-agent): add flush_buffer, ordered drain that stops on failure"
```

---

## Task 5: `on_message()` (callback MQTT)

**Files:**
- Modify: `infra/ops121s/edge-agent/test_edge_agent.py`
- Modify: `infra/ops121s/edge-agent/edge_agent.py`

- [ ] **Step 1: Write the failing tests**

Update the import line in `test_edge_agent.py` to:

```python
from edge_agent import Buffer, Reading, flush_buffer, forward_reading, on_message, parse_uplink
```

Add to `test_edge_agent.py`:

```python
class TestOnMessage(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.buffer = Buffer(self.db_path)

    def tearDown(self):
        self.buffer.close()
        os.remove(self.db_path)

    @staticmethod
    def _make_msg(topic, payload_dict=None, raw_payload=None):
        msg = MagicMock()
        msg.topic = topic
        if raw_payload is not None:
            msg.payload = raw_payload
        else:
            msg.payload = json.dumps(payload_dict).encode("utf-8")
        return msg

    def test_valid_uplink_enqueues_reading(self):
        payload = {
            "deviceInfo": {"deviceName": "lht65-frigo-positif"},
            "object": {"temperature_1": 3.5, "humidity": 62.1, "battery_voltage": 3.6},
        }
        msg = self._make_msg("application/app1/device/xyz/event/up", payload)
        on_message(MagicMock(), {"buffer": self.buffer}, msg)
        pending = self.buffer.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0][1].tag, "Frigo_Temperature")
        self.assertEqual(pending[0][1].value, 3.5)

    def test_unmapped_device_does_not_enqueue(self):
        payload = {"deviceInfo": {"deviceName": "unknown-device"}, "object": {"temperature_1": 3.5}}
        msg = self._make_msg("application/app1/device/xyz/event/up", payload)
        on_message(MagicMock(), {"buffer": self.buffer}, msg)
        self.assertEqual(self.buffer.pending(), [])

    def test_invalid_json_does_not_raise_and_does_not_enqueue(self):
        msg = self._make_msg("application/app1/device/xyz/event/up", raw_payload=b"not json")
        on_message(MagicMock(), {"buffer": self.buffer}, msg)
        self.assertEqual(self.buffer.pending(), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: FAIL with `ImportError: cannot import name 'on_message' from 'edge_agent'`

- [ ] **Step 3: Write minimal implementation**

Add to `edge_agent.py`, after `flush_buffer`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: PASS (21 tests)

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/edge-agent/test_edge_agent.py infra/ops121s/edge-agent/edge_agent.py
git commit -m "feat(edge-agent): add on_message MQTT callback wiring parse_uplink to Buffer"
```

---

## Task 6: `main()` (cablage MQTT + boucle de vidange) — non teste unitairement

**Files:**
- Modify: `infra/ops121s/edge-agent/edge_agent.py`
- Create: `infra/ops121s/edge-agent/requirements.txt`

This is wiring/IO code (real MQTT connection, real sleep loop) — not meaningfully unit-testable without a live broker. It is validated manually against a real ChirpStack instance once deployed (see the note in Task 7). No test file changes in this task.

- [ ] **Step 1: Create the requirements file**

Create `infra/ops121s/edge-agent/requirements.txt`:

```
paho-mqtt==1.6.1
```

- [ ] **Step 2: Write `main()`**

Replace the `if __name__ == "__main__": pass` placeholder at the bottom of `edge_agent.py` with:

```python
def main() -> None:
    import paho.mqtt.client as mqtt  # import local : garde le reste du module testable sans paho

    mqtt_host = os.environ.get("MQTT_HOST", "127.0.0.1")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    application_id = os.environ.get("CHIRPSTACK_APPLICATION_ID", "")
    if not application_id:
        raise SystemExit("CHIRPSTACK_APPLICATION_ID environment variable is required")
    bridge_url = os.environ.get("ODOO_BRIDGE_URL", "http://127.0.0.1:5001/quality-check")
    buffer_db_path = os.environ.get("BUFFER_DB_PATH", "buffer.db")
    flush_interval = float(os.environ.get("FLUSH_INTERVAL_SECONDS", "10"))
    http_timeout = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "10"))

    buffer = Buffer(buffer_db_path)
    topic = f"application/{application_id}/device/+/event/up"

    def _on_connect(client, userdata, flags, rc):
        log.info("Connecte au broker MQTT %s:%s (rc=%s) — souscription %s", mqtt_host, mqtt_port, rc, topic)
        client.subscribe(topic)

    client = mqtt.Client(userdata={"buffer": buffer})
    client.on_connect = _on_connect
    client.on_message = on_message
    client.connect(mqtt_host, mqtt_port)
    client.loop_start()

    log.info(
        "haccp-edge-agent demarre — MQTT %s:%s, bridge %s, buffer %s",
        mqtt_host, mqtt_port, bridge_url, buffer_db_path,
    )
    try:
        while True:
            flush_buffer(buffer, bridge_url, http_timeout)
            time.sleep(flush_interval)
    except KeyboardInterrupt:
        log.info("Arret demande")
    finally:
        client.loop_stop()
        buffer.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the module still imports cleanly without paho-mqtt installed**

Run: `cd infra/ops121s/edge-agent && python3 -c "import edge_agent; print('import OK')"`
Expected: `import OK` — confirms the local `import paho.mqtt.client` inside `main()` doesn't break importing the module for tests.

- [ ] **Step 4: Run the full test suite once more**

Run: `cd infra/ops121s/edge-agent && python3 -m unittest test_edge_agent -v`
Expected: PASS (21 tests) — unchanged, `main()` has no unit tests by design (see task header).

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/edge-agent/edge_agent.py infra/ops121s/edge-agent/requirements.txt
git commit -m "feat(edge-agent): wire main() — MQTT client, subscribe, periodic flush loop"
```

---

## Task 7: Déploiement (systemd) et documentation des variables d'environnement

**Files:**
- Create: `infra/ops121s/edge-agent/haccp-edge-agent.service`

- [ ] **Step 1: Create the systemd unit**

Create `infra/ops121s/edge-agent/haccp-edge-agent.service`, mirroring the existing `infra/ops121s/odoo-bridge/haccp-odoo-bridge.service` pattern:

```ini
[Unit]
Description=HACCP Edge Agent — ChirpStack MQTT -> buffer local -> Odoo bridge
After=network.target

[Service]
Type=simple
User=christian
WorkingDirectory=/home/christian/haccp/edge-agent
ExecStart=/usr/bin/python3 /home/christian/haccp/edge-agent/edge_agent.py
EnvironmentFile=/home/christian/haccp/edge-agent/edge-agent.env
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=haccp-edge-agent

[Install]
WantedBy=multi-user.target
```

`edge-agent.env` (not committed — same `*.env` gitignore rule as `bridge.env`) must define at minimum:

```
CHIRPSTACK_APPLICATION_ID=<id application ChirpStack>
```

Optional overrides (defaults shown, matching what `main()` falls back to): `MQTT_HOST=127.0.0.1`, `MQTT_PORT=1883`, `ODOO_BRIDGE_URL=http://127.0.0.1:5001/quality-check`, `BUFFER_DB_PATH=/home/christian/haccp/edge-agent/buffer.db`, `FLUSH_INTERVAL_SECONDS=10`, `HTTP_TIMEOUT_SECONDS=10`.

- [ ] **Step 2: Commit**

```bash
git add infra/ops121s/edge-agent/haccp-edge-agent.service
git commit -m "chore(edge-agent): add systemd unit for deployment"
```

---

## Not covered by this plan (tracked separately, per spec §12)

- Adding ChirpStack to `infra/ops121s/docker-compose.yml` and configuring a device profile codec that produces `object.temperature_1` / `object.humidity` — required before `main()` can be validated against a real broker.
- Validating the ChirpStack uplink event JSON shape assumed in `parse_uplink()` against a real payload once ChirpStack is deployed (spec §11 question 3) — if field names differ, only `parse_uplink()` needs changing.
- Replacing `scripts/demo-simulate-sensor.py` (built for the TTN Simulate Uplink API) with a ChirpStack equivalent (spec §11 question 2).
- Progressive migration of the live POC off vNode: running `haccp-edge-agent` alongside vNode, cross-validating, then decommissioning vNode (spec §12 item 3) — and updating `docs/operations/architecture-ops121s-vnode.md` once that migration actually happens, since it currently correctly documents the still-live vNode setup.
- The "on change vs continuous transmission" question from spec §11 question 1 is resolved by this plan: `haccp-edge-agent` forwards **every** received uplink (no change-detection filtering), for code simplicity and a more continuous HACCP audit trail. Typical LHT65 report intervals (~10-20 min) keep the resulting Odoo record volume trivial.

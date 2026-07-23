# ChirpStack Demo Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a ChirpStack service skeleton to the OPS121S docker-compose stack, and build `demo-simulate-sensor-chirpstack.py`, a CLI tool that publishes a simulated sensor uplink directly onto the MQTT topic ChirpStack would use — so `haccp-edge-agent` (built in the previous plan) can be demoed end-to-end without a physical LoRaWAN gateway.

**Architecture:** ChirpStack has no "simulate uplink" API equivalent to TTN's (used by the existing `demo-simulate-sensor.py`). Instead of simulating a full LoRaWAN radio frame through ChirpStack's own device-profile codec, this plan takes the simpler, robust path already used elsewhere in this project: publish an already-decoded JSON event directly to the MQTT topic `application/{application_id}/device/{device_id}/event/up` — exactly the shape `haccp-edge-agent`'s `parse_uplink()` expects. This exercises the real Mosquitto → `haccp-edge-agent` → `haccp-odoo-bridge` → Odoo → SMS chain end-to-end, but does **not** exercise ChirpStack's own LoRaWAN/codec layer — that must be validated separately once a real device profile is configured (tracked in the runbook, not this plan).

**Tech Stack:** Docker Compose (YAML) for the ChirpStack service skeleton. Python 3, stdlib only for the demo script's testable logic; `paho-mqtt` is the one external dependency for the actual MQTT publish, imported locally so the test suite runs without it installed — same pattern as `haccp-edge-agent`.

**Scope note:** This plan covers only what's testable/reviewable without touching real infrastructure: the docker-compose service definitions (structurally validated, not started — no Docker available in this environment) and the demo script (fully unit tested). Two things are explicitly **out of scope** here and covered instead by a manual runbook to execute together later, not autonomously:
- Filling in ChirpStack's actual `.toml` configuration files (schema/exact content depends on the ChirpStack version being deployed — verify against the official quickstart at deploy time, not fabricated here).
- Configuring ChirpStack itself (tenant/application/device profile/codec) via its web UI, provisioning devices, and deploying `haccp-edge-agent` + this compose change to the real OPS121S.

See `docs/operations/chirpstack-deploiement-ops121s.md` (companion runbook, written alongside this plan) for that part.

---

## Context an engineer needs before starting

- **Design spec:** `docs/superpowers/specs/2026-07-22-architecture-sans-vnode-design.md` — §6 (ChirpStack runs locally on the edge, not on a separate VPS or via TTN).
- **`haccp-edge-agent` plan and code:** `docs/superpowers/plans/2026-07-23-haccp-edge-agent.md` and `infra/ops121s/edge-agent/edge_agent.py`. Specifically, `parse_uplink()` expects a JSON body shaped `{"deviceInfo": {"deviceName": "<device id>"}, "object": {"<field>": <value>}}`, and the agent subscribes to `application/{CHIRPSTACK_APPLICATION_ID}/device/+/event/up` — the `+` wildcard means the actual device-id segment in the topic is not parsed by the agent at all; only the body's `deviceInfo.deviceName` matters for routing.
- **Existing TTN demo script for reference/pattern:** `scripts/demo-simulate-sensor.py` and its test `scripts/tests/test_demo_simulate_sensor.py` — this plan's script mirrors the same CLI shape (`--device`, `--value`, `--field`, `--list-devices`), same `KNOWN_DEVICES` table, same test-file location convention (`scripts/tests/`, loaded via `importlib.util.spec_from_file_location` since the test file lives in a different directory than the script).
- **Existing docker-compose stack:** `infra/ops121s/docker-compose.yml` — currently `mosquitto`, `influxdb`, `portainer` on a `haccp-net` bridge network; vNode is explicitly excluded (native install, not dockerized — irrelevant to this plan, vNode is being decommissioned per the design spec, not touched here).
- **No Docker available in this environment** — Task 1's "verification" is limited to structural YAML validation (parsing the file with PyYAML, checking for duplicate keys/valid syntax), not actually starting containers. Real validation happens on the OPS121S during the runbook.
- **Image tags and TOML config schema are assumptions, not verified facts** — `chirpstack/chirpstack:4` and `chirpstack/chirpstack-gateway-bridge:4` are the project's real Docker Hub image names as of this plan's writing, but exact current tags and the TOML config file schema should be checked against ChirpStack's own documentation at actual deployment time (the runbook says this explicitly). This plan does not fabricate `.toml` file content — it creates placeholder config directories with a README documenting exactly what's needed.

---

## Task 1: ChirpStack service skeleton in `docker-compose.yml`

**Files:**
- Modify: `infra/ops121s/docker-compose.yml`
- Modify: `infra/ops121s/.env.example`
- Create: `infra/ops121s/chirpstack/config/.gitkeep`
- Create: `infra/ops121s/chirpstack/config/README.md`
- Create: `infra/ops121s/chirpstack/gateway-bridge-config/.gitkeep`
- Create: `infra/ops121s/chirpstack/gateway-bridge-config/README.md`

No code to unit test here — this is infrastructure config. "Verification" means structural YAML validation, since Docker isn't available in this environment.

- [ ] **Step 1: Add ChirpStack services to `docker-compose.yml`**

Insert these four services into `infra/ops121s/docker-compose.yml`, between the existing `portainer` service and the vNode comment:

```yaml
  postgres:
    image: postgres:14-alpine
    container_name: haccp-chirpstack-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=chirpstack
      - POSTGRES_USER=chirpstack
      - POSTGRES_PASSWORD=${CHIRPSTACK_POSTGRES_PASSWORD}
    volumes:
      - chirpstack_postgres_data:/var/lib/postgresql/data
    networks:
      - haccp-net

  redis:
    image: redis:7-alpine
    container_name: haccp-chirpstack-redis
    restart: unless-stopped
    volumes:
      - chirpstack_redis_data:/data
    networks:
      - haccp-net

  # ChirpStack tourne en local sur l'edge (pas sur un VPS, pas TTN) : voir
  # docs/superpowers/specs/2026-07-22-architecture-sans-vnode-design.md §6.
  # Fichiers de config .toml a completer avant premier demarrage — voir
  # infra/ops121s/chirpstack/config/README.md
  chirpstack:
    image: chirpstack/chirpstack:4
    container_name: haccp-chirpstack
    restart: unless-stopped
    command: -c /etc/chirpstack
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./chirpstack/config:/etc/chirpstack
    depends_on:
      - postgres
      - redis
      - mosquitto
    networks:
      - haccp-net

  # Traduit le protocole des gateways LoRaWAN physiques (Semtech UDP / Basic
  # Station) en evenements MQTT pour ChirpStack. Pas encore exerce par la
  # demo (scripts/demo-simulate-sensor-chirpstack.py publie directement sur
  # le topic MQTT final, en contournant ce service) — necessaire seulement
  # le jour ou un vrai gateway LoRaWAN (RAK7268 ou equivalent) est branche.
  chirpstack-gateway-bridge:
    image: chirpstack/chirpstack-gateway-bridge:4
    container_name: haccp-chirpstack-gateway-bridge
    restart: unless-stopped
    command: -c /etc/chirpstack-gateway-bridge
    ports:
      - "1700:1700/udp"
    volumes:
      - ./chirpstack/gateway-bridge-config:/etc/chirpstack-gateway-bridge
    depends_on:
      - mosquitto
    networks:
      - haccp-net
```

Add the two new named volumes to the `volumes:` section at the bottom of the file:

```yaml
  chirpstack_postgres_data:
  chirpstack_redis_data:
```

- [ ] **Step 2: Document the required Postgres password in `.env.example`**

Add to `infra/ops121s/.env.example`:

```
# ChirpStack — mot de passe Postgres interne (généré, pas besoin de le retenir)
# Générer avec : openssl rand -hex 24
CHIRPSTACK_POSTGRES_PASSWORD=changeme_chirpstack_postgres_password
```

- [ ] **Step 3: Create placeholder config directories with a README explaining the gap**

Create `infra/ops121s/chirpstack/config/.gitkeep` (empty file).

Create `infra/ops121s/chirpstack/config/README.md`:

```markdown
# Configuration ChirpStack — à compléter avant le premier déploiement

Ce dossier doit contenir les fichiers `.toml` de configuration de ChirpStack
(app server + network server, image `chirpstack/chirpstack:4`) : au minimum
`chirpstack.toml` et un fichier de plan de fréquence régional
(`region_eu868.toml` pour l'Europe).

**Ce contenu n'est volontairement pas fourni ici** — le schéma exact dépend
de la version de ChirpStack réellement déployée et évolue avec le produit.
À copier/adapter depuis le quickstart officiel ChirpStack (docker-compose)
au moment du déploiement réel sur l'OPS121S, pas avant :
https://www.chirpstack.io/docs/chirpstack/getting-started/docker.html

Points à configurer en particulier (déjà connus de ce projet) :
- Connexion Postgres : host `postgres`, db `chirpstack`, user `chirpstack`,
  password = `CHIRPSTACK_POSTGRES_PASSWORD` (voir `infra/ops121s/.env`).
- Connexion Redis : host `redis`.
- Intégration MQTT : host `mosquitto` (le broker déjà présent dans ce
  docker-compose), pas un nouveau broker.
- Plan de fréquence : EU868 (cohérent avec les capteurs LHT65 déjà en jeu
  dans ce POC).

Voir `docs/operations/chirpstack-deploiement-ops121s.md` pour la procédure
complète de déploiement (tenant, application, device profile + codec,
provisionnement des devices).
```

Create `infra/ops121s/chirpstack/gateway-bridge-config/.gitkeep` (empty file).

Create `infra/ops121s/chirpstack/gateway-bridge-config/README.md`:

```markdown
# Configuration ChirpStack Gateway Bridge — à compléter

Fichier `chirpstack-gateway-bridge.toml` attendu ici (image
`chirpstack/chirpstack-gateway-bridge:4`), non fourni pour la même raison
que `../config/README.md` — à copier/adapter depuis le quickstart officiel
au moment du déploiement réel :
https://www.chirpstack.io/docs/chirpstack-gateway-bridge/

Ce service n'est nécessaire que le jour où un vrai gateway LoRaWAN physique
(RAK7268 ou équivalent) est branché sur le réseau — pas exercé par
`scripts/demo-simulate-sensor-chirpstack.py`, qui contourne toute cette
couche pour la démo.
```

- [ ] **Step 4: Validate the compose file structurally**

Run:
```bash
python3 -c "
import yaml
with open('infra/ops121s/docker-compose.yml') as f:
    data = yaml.safe_load(f)
services = data['services']
assert 'postgres' in services
assert 'redis' in services
assert 'chirpstack' in services
assert 'chirpstack-gateway-bridge' in services
assert 'chirpstack_postgres_data' in data['volumes']
assert 'chirpstack_redis_data' in data['volumes']
print('OK — structure valide,', len(services), 'services,', len(data['volumes']), 'volumes')
"
```
Expected: `OK — structure valide, 7 services, 6 volumes` (mosquitto, influxdb, portainer, postgres, redis, chirpstack, chirpstack-gateway-bridge = 7 services; mosquitto_data, mosquitto_log, influxdb_data, portainer_data, chirpstack_postgres_data, chirpstack_redis_data = 6 volumes).

This only proves the YAML is well-formed and has the expected top-level keys — it does **not** prove the stack actually starts correctly (no Docker here). Real validation happens on the OPS121S per the runbook.

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/docker-compose.yml infra/ops121s/.env.example infra/ops121s/chirpstack/
git commit -m "feat(ops121s): add ChirpStack service skeleton to docker-compose"
```

---

## Task 2: `build_topic()` and `build_uplink_payload()` (pure functions)

**Files:**
- Create: `scripts/demo-simulate-sensor-chirpstack.py`
- Create: `scripts/tests/test_demo_simulate_sensor_chirpstack.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_demo_simulate_sensor_chirpstack.py`:

```python
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / "demo-simulate-sensor-chirpstack.py"
_spec = importlib.util.spec_from_file_location("demo_simulate_sensor_chirpstack", MODULE_PATH)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


class TestBuildTopic(unittest.TestCase):
    def test_builds_correct_topic(self):
        topic = demo.build_topic("haccp-restaurant-poc", "lht65-frigo-positif")
        self.assertEqual(
            topic, "application/haccp-restaurant-poc/device/lht65-frigo-positif/event/up"
        )


class TestBuildUplinkPayload(unittest.TestCase):
    def test_builds_correct_payload_temperature(self):
        payload = demo.build_uplink_payload("lht65-frigo-positif", "temperature_1", 12.0)
        self.assertEqual(
            payload,
            {"deviceInfo": {"deviceName": "lht65-frigo-positif"}, "object": {"temperature_1": 12.0}},
        )

    def test_builds_correct_payload_humidity(self):
        payload = demo.build_uplink_payload("lht65-stockage-sec", "humidity", 90.0)
        self.assertEqual(
            payload,
            {"deviceInfo": {"deviceName": "lht65-stockage-sec"}, "object": {"humidity": 90.0}},
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: FAIL — `FileNotFoundError` or `AttributeError` (module file doesn't exist yet)

- [ ] **Step 3: Write minimal implementation**

Create `scripts/demo-simulate-sensor-chirpstack.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor-chirpstack.py scripts/tests/test_demo_simulate_sensor_chirpstack.py
git commit -m "feat(scripts): add build_topic/build_uplink_payload for ChirpStack demo script"
```

---

## Task 3: `print_list_devices()` and `parse_args()`

**Files:**
- Modify: `scripts/tests/test_demo_simulate_sensor_chirpstack.py`
- Modify: `scripts/demo-simulate-sensor-chirpstack.py`

- [ ] **Step 1: Write the failing tests**

Add to the top imports of `test_demo_simulate_sensor_chirpstack.py`:

```python
import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch
```

Add:

```python
class TestListDevices(unittest.TestCase):
    def test_list_devices_prints_known_devices_and_returns_0(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = demo.main(["--list-devices"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("lht65-frigo-positif", output)
        self.assertIn("lht65-congelateur", output)
        self.assertIn("lht65-stockage-sec", output)


class TestMainMissingArgs(unittest.TestCase):
    def test_exits_1_without_device_or_value(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = demo.main([])
        self.assertEqual(code, 1)
        self.assertIn("ERREUR", stderr.getvalue())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: FAIL — `AttributeError: module 'demo_simulate_sensor_chirpstack' has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

Add to `demo-simulate-sensor-chirpstack.py`, after `build_uplink_payload`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor-chirpstack.py scripts/tests/test_demo_simulate_sensor_chirpstack.py
git commit -m "feat(scripts): add print_list_devices, parse_args, and main skeleton"
```

---

## Task 4: `publish_uplink()` (thin MQTT wrapper, not unit tested)

**Files:**
- Modify: `scripts/demo-simulate-sensor-chirpstack.py`
- Create: `scripts/requirements.txt`

Mirrors `haccp-edge-agent`'s `main()` design: the actual network call is a thin, deliberately-untested wrapper (real MQTT publish, no meaningful unit test without a live broker), imported locally so the rest of the script stays testable without `paho-mqtt` installed.

- [ ] **Step 1: Create the requirements file**

Create `scripts/requirements.txt`:

```
paho-mqtt==1.6.1
```

- [ ] **Step 2: Add `publish_uplink()`**

Add to `demo-simulate-sensor-chirpstack.py`, after `build_uplink_payload` (before `print_list_devices`):

```python
def publish_uplink(mqtt_host, mqtt_port, topic, payload):
    import paho.mqtt.publish as mqtt_publish  # import local : garde le script testable sans paho

    mqtt_publish.single(
        topic,
        payload=json.dumps(payload),
        hostname=mqtt_host,
        port=mqtt_port,
        qos=0,
    )
```

- [ ] **Step 3: Verify the module still imports cleanly without paho-mqtt installed**

Run: `cd scripts && python3 -c "import importlib.util; spec = importlib.util.spec_from_file_location('m', 'demo-simulate-sensor-chirpstack.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('import OK')"`
Expected: `import OK`

- [ ] **Step 4: Run the full test suite once more**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: PASS (5 tests, unchanged — `publish_uplink` has no direct unit test by design)

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor-chirpstack.py scripts/requirements.txt
git commit -m "feat(scripts): add publish_uplink MQTT wrapper for ChirpStack demo script"
```

---

## Task 5: Wire `main()` to publish, with error handling

**Files:**
- Modify: `scripts/tests/test_demo_simulate_sensor_chirpstack.py`
- Modify: `scripts/demo-simulate-sensor-chirpstack.py`

- [ ] **Step 1: Write the failing tests**

Add to `test_demo_simulate_sensor_chirpstack.py`:

```python
class TestMainSuccess(unittest.TestCase):
    def test_success_publishes_and_returns_0(self):
        stdout = io.StringIO()
        with patch.object(demo, "publish_uplink") as mock_publish, patch("sys.stdout", stdout):
            code = demo.main([
                "--device", "lht65-frigo-positif",
                "--value", "12.0",
                "--application-id", "haccp-restaurant-poc",
                "--mqtt-host", "127.0.0.1",
                "--mqtt-port", "1883",
            ])
        self.assertEqual(code, 0)
        mock_publish.assert_called_once_with(
            "127.0.0.1",
            1883,
            "application/haccp-restaurant-poc/device/lht65-frigo-positif/event/up",
            {"deviceInfo": {"deviceName": "lht65-frigo-positif"}, "object": {"temperature_1": 12.0}},
        )
        self.assertIn("OK", stdout.getvalue())

    def test_humidity_field_builds_correct_payload(self):
        with patch.object(demo, "publish_uplink") as mock_publish:
            demo.main([
                "--device", "lht65-stockage-sec",
                "--value", "90.0",
                "--field", "humidity",
            ])
        called_payload = mock_publish.call_args[0][3]
        self.assertEqual(
            called_payload,
            {"deviceInfo": {"deviceName": "lht65-stockage-sec"}, "object": {"humidity": 90.0}},
        )


class TestMainMqttError(unittest.TestCase):
    def test_mqtt_error_prints_message_and_returns_1(self):
        stderr = io.StringIO()
        with patch.object(demo, "publish_uplink", side_effect=ConnectionRefusedError("refused")), \
             patch("sys.stderr", stderr):
            code = demo.main(["--device", "lht65-frigo-positif", "--value", "12.0"])
        self.assertEqual(code, 1)
        self.assertIn("ERREUR MQTT", stderr.getvalue())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: FAIL — `test_success_publishes_and_returns_0` and `test_humidity_field_builds_correct_payload` fail because `mock_publish` is never called (current `main()` returns `0`/`1` without calling `publish_uplink`); `test_mqtt_error_prints_message_and_returns_1` fails because no `OSError` handling exists yet and/or the mocked side effect is never triggered.

- [ ] **Step 3: Write minimal implementation**

Replace the `return 0` at the end of `main()` (added in Task 3) with:

```python
    topic = build_topic(args.application_id, args.device)
    payload = build_uplink_payload(args.device, args.field, args.value)

    print(f"Publication d'un uplink simule — device={args.device} {args.field}={args.value}")
    print(f"MQTT {args.mqtt_host}:{args.mqtt_port} -> {topic}")

    try:
        publish_uplink(args.mqtt_host, args.mqtt_port, topic, payload)
    except OSError as e:
        print(f"ERREUR MQTT : {e}", file=sys.stderr)
        return 1

    print("OK — uplink simule publie")
    print("Observe maintenant en direct :")
    print("  - Odoo (quality.check / quality.alert) sur http://192.168.1.182:8029")
    print("  - Le telephone configure pour les SMS d'alerte")
    return 0
```

Also add, right at the bottom of the file, replacing `if __name__ == "__main__": pass`:

```python
if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/tests && python3 -m unittest test_demo_simulate_sensor_chirpstack -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/demo-simulate-sensor-chirpstack.py scripts/tests/test_demo_simulate_sensor_chirpstack.py
git commit -m "feat(scripts): wire main() to publish_uplink with OSError handling"
```

---

## Not covered by this plan (runbook, to execute together later — not autonomous)

See `docs/operations/chirpstack-deploiement-ops121s.md` for:
- Populating ChirpStack's actual `.toml` config files from the official quickstart.
- Deploying the updated `docker-compose.yml` to the real OPS121S (`docker compose up -d postgres redis chirpstack chirpstack-gateway-bridge`).
- Configuring ChirpStack via its web UI: tenant, application, device profile with a JS codec (reusing the LHT65 decode logic already documented in `docs/operations/architecture-ops121s-vnode.md` §3.1), provisioning the 3 devices.
- Deploying `haccp-edge-agent` itself to the OPS121S (`edge-agent.env` with `CHIRPSTACK_APPLICATION_ID`, `systemctl enable --now haccp-edge-agent`).
- Running `scripts/demo-simulate-sensor-chirpstack.py` against the real broker and confirming the full chain in Odoo + SMS.
- Running ChirpStack + `haccp-edge-agent` in parallel with vNode for cross-validation, then decommissioning vNode and updating `docs/operations/architecture-ops121s-vnode.md` to reflect the new reality.

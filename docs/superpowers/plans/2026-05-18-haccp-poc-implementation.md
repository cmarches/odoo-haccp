# HACCP IoT POC — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déployer un POC fonctionnel de surveillance HACCP IoT couvrant la chaîne complète : capteurs LHT65 → LoRaWAN → TTN → vNode Edge → Odoo Qualité → alertes multi-niveaux (push ntfy + SMS + appel vocal Twilio).

**Architecture:** Stack en 4 couches (Capteurs → Réseau → Edge OPS121S → Cloud VPS). vNode Automation sur OPS121S orchestre l'ingestion MQTT depuis TTN, l'évaluation des seuils HACCP et la synchronisation avec Odoo Community 19 via XML-RPC. La résilience réseau est assurée par le Dream Machine SE dual WAN (Fibre + 4G/LTE 1NCE).

**Tech Stack:** Ubuntu 20.04 LTS · Docker Compose v2 · vNode Automation (Vester, mode démo) · Mosquitto MQTT · InfluxDB 2.7 · Portainer CE · Odoo 19 Community Edition · PostgreSQL 15 · ntfy.sh · Flask + Twilio SDK (webhook) · Restic (backup) · The Things Network EU868

---

## Fichiers créés par ce plan

### OPS121S (`infra/ops121s/`)
- `docker-compose.yml` — Stack Mosquitto + InfluxDB + Portainer + vNode
- `.env.example` — Variables d'environnement (template sans secrets)
- `mosquitto/mosquitto.conf` — Configuration broker MQTT local
- `vnode/config/rules-example.json` — Structure de référence des règles HACCP vNode
- `backup/restic-init.sh` — Initialisation one-shot repo Restic
- `backup/haccp-backup.cron` — Tâches cron Restic (InfluxDB + SQLite + config)

### VPS (`infra/vps/`)
- `docker-compose.yml` — Stack Odoo 19 CE + PostgreSQL 15 + ntfy.sh + webhook Twilio
- `.env.example` — Variables d'environnement (template)
- `ntfy/server.yml` — Configuration ntfy.sh (auth, cache, base-url)
- `odoo/odoo.conf` — Configuration Odoo (addons, workers, log)
- `webhook/app.py` — Flask TwiML + endpoint ACK Twilio
- `webhook/Dockerfile` — Image Docker webhook
- `webhook/requirements.txt` — Dépendances Python

### Scripts (`scripts/`)
- `test-odoo-api.py` — Test XML-RPC création quality.check + quality.alert
- `test-mqtt-subscribe.sh` — Test abonnement MQTT TTN (réception payloads LHT65)

### Documentation opérationnelle (`docs/operations/`)
- `dream-machine-se-config.md` — Procédure VLANs + dual WAN
- `rak7268-setup.md` — Procédure configuration gateway LoRaWAN
- `ttn-setup.md` — Procédure TTN + enregistrement LHT65
- `ops121s-setup.md` — Installation Ubuntu 20.04 + Docker Engine
- `vps-odoo-setup.md` — Déploiement VPS Hetzner + Odoo
- `odoo-qualite-qcp.md` — Configuration QCPs Odoo Qualité
- `vnode-config.md` — Configuration vNode MQTT + règles HACCP
- `alertes-twilio-sms.md` — Configuration alertes Twilio Voice + SMS

---

## Task 1: Initialisation du dépôt git + structure infra

**Files:**
- Create: `.gitignore`
- Create: répertoires `infra/`, `scripts/`, `docs/operations/`

- [ ] **Step 1: Initialiser le dépôt git**

```bash
cd /home/christian/projets/aifluencedigital/odoo-haccp
git init
git config user.email "aifluencedigital@gmail.com"
git config user.name "AIFluence Digital"
```

Expected: `Initialized empty Git repository in .../odoo-haccp/.git/`

- [ ] **Step 2: Créer la structure des répertoires**

```bash
mkdir -p infra/ops121s/mosquitto
mkdir -p infra/ops121s/vnode/config
mkdir -p infra/ops121s/vnode/data
mkdir -p infra/ops121s/backup
mkdir -p infra/vps/ntfy
mkdir -p infra/vps/odoo
mkdir -p infra/vps/webhook
mkdir -p scripts
mkdir -p docs/operations
touch infra/ops121s/vnode/config/.gitkeep
touch infra/ops121s/vnode/data/.gitkeep
```

- [ ] **Step 3: Créer le .gitignore**

Créer `.gitignore` :

```
# Secrets — ne jamais committer
infra/ops121s/.env
infra/vps/.env
*.env
/etc/haccp-backup.env

# Python
__pycache__/
*.pyc
*.pyo
.venv/

# OS
.DS_Store
Thumbs.db

# Données runtime
infra/ops121s/vnode/data/*
!infra/ops121s/vnode/data/.gitkeep
```

- [ ] **Step 4: Stager les fichiers existants**

```bash
git add docs/ .gitignore
```

- [ ] **Step 5: Commit initial**

```bash
git commit -m "chore: init repo HACCP IoT POC — spec + structure infra"
```

Expected: commit créé, 1+ fichiers.

---

## Task 2: Stack Docker OPS121S

**Files:**
- Create: `infra/ops121s/docker-compose.yml`
- Create: `infra/ops121s/.env.example`
- Create: `infra/ops121s/mosquitto/mosquitto.conf`

- [ ] **Step 1: Créer docker-compose.yml OPS121S**

Créer `infra/ops121s/docker-compose.yml` :

```yaml
version: "3.8"

services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: haccp-mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log
    networks:
      - haccp-net

  influxdb:
    image: influxdb:2.7
    container_name: haccp-influxdb
    restart: unless-stopped
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=${INFLUXDB_USER}
      - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD}
      - DOCKER_INFLUXDB_INIT_ORG=aifluence
      - DOCKER_INFLUXDB_INIT_BUCKET=haccp
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN}
    volumes:
      - influxdb_data:/var/lib/influxdb2
    networks:
      - haccp-net

  portainer:
    image: portainer/portainer-ce:latest
    container_name: haccp-portainer
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    networks:
      - haccp-net

  # L'image vNode est fournie par Vester lors de l'activation.
  # Remplacer "vester/vnode-automation:latest" par l'image réelle.
  # Le MAC address fixe (02:42:ac:11:00:02) stabilise l'empreinte machine pour la licence.
  vnode:
    image: vester/vnode-automation:latest
    container_name: haccp-vnode
    restart: unless-stopped
    mac_address: "02:42:ac:11:00:02"
    environment:
      - TZ=Europe/Paris
    volumes:
      - ./vnode/config:/app/config
      - ./vnode/data:/app/data
    depends_on:
      - mosquitto
      - influxdb
    networks:
      - haccp-net

networks:
  haccp-net:
    driver: bridge

volumes:
  mosquitto_data:
  mosquitto_log:
  influxdb_data:
  portainer_data:
```

- [ ] **Step 2: Créer .env.example OPS121S**

Créer `infra/ops121s/.env.example` :

```bash
# Copier vers .env et remplir les valeurs réelles (ne pas committer .env)
INFLUXDB_USER=haccp_admin
INFLUXDB_PASSWORD=changeme_influx_password_min16chars

# Token InfluxDB — générer avec : openssl rand -hex 32
INFLUXDB_TOKEN=changeme_influx_token_64chars_minimum
```

- [ ] **Step 3: Créer mosquitto/mosquitto.conf**

Créer `infra/ops121s/mosquitto/mosquitto.conf` :

```
# Listener local non-TLS — vNode communique en intra-réseau Docker
listener 1883
allow_anonymous true

# Logs
log_type error
log_type warning
log_type notice
log_dest file /mosquitto/log/mosquitto.log
persistence true
persistence_location /mosquitto/data/
```

- [ ] **Step 4: Vérifier la syntaxe YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('infra/ops121s/docker-compose.yml'))" && echo "OK — YAML valide"
```

Expected: `OK — YAML valide`

- [ ] **Step 5: Commit**

```bash
git add infra/ops121s/
git commit -m "feat: docker-compose OPS121S — Mosquitto + InfluxDB + Portainer + vNode"
```

---

## Task 3: Stack Docker VPS (Odoo 19 CE + PostgreSQL 15 + ntfy.sh + webhook)

**Files:**
- Create: `infra/vps/docker-compose.yml`
- Create: `infra/vps/.env.example`
- Create: `infra/vps/ntfy/server.yml`
- Create: `infra/vps/odoo/odoo.conf`

- [ ] **Step 1: Créer docker-compose.yml VPS**

Créer `infra/vps/docker-compose.yml` :

```yaml
version: "3.8"

services:
  db:
    image: postgres:15
    container_name: odoo-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=odoo
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - odoo-net
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "odoo"]
      interval: 10s
      timeout: 5s
      retries: 5

  odoo:
    image: odoo:19.0
    container_name: odoo-app
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - odoo_data:/var/lib/odoo
      - ./odoo/odoo.conf:/etc/odoo/odoo.conf
      - ./odoo/addons:/mnt/extra-addons
    networks:
      - odoo-net

  ntfy:
    image: binwiederhier/ntfy:latest
    container_name: odoo-ntfy
    restart: unless-stopped
    command: serve
    ports:
      - "8080:80"
    volumes:
      - ./ntfy/server.yml:/etc/ntfy/server.yml
      - ntfy_data:/var/lib/ntfy
      - ntfy_cache:/var/cache/ntfy
    networks:
      - odoo-net

  webhook:
    build: ./webhook
    container_name: odoo-webhook
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - ODOO_URL=http://odoo:8069
      - ODOO_DB=odoo
      - ODOO_USER=admin
      - ODOO_API_KEY=${ODOO_API_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
    depends_on:
      - odoo
    networks:
      - odoo-net

networks:
  odoo-net:
    driver: bridge

volumes:
  postgres_data:
  odoo_data:
  ntfy_data:
  ntfy_cache:
```

- [ ] **Step 2: Créer .env.example VPS**

Créer `infra/vps/.env.example` :

```bash
# Copier vers .env et remplir les valeurs réelles (ne pas committer .env)

# PostgreSQL
POSTGRES_PASSWORD=changeme_postgres_password_min16chars

# Odoo — clé API générée dans Odoo Settings > Technical > API Keys
ODOO_API_KEY=changeme_odoo_api_key

# Twilio — Dashboard twilio.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=changeme_twilio_auth_token
TWILIO_FROM_NUMBER=+33XXXXXXXXX
```

- [ ] **Step 3: Créer ntfy/server.yml**

Créer `infra/vps/ntfy/server.yml` :

```yaml
# Remplacer base-url par le domaine ou IP réelle du VPS
base-url: http://VOTRE_IP_VPS:8080

cache-file: /var/lib/ntfy/cache.db
auth-file: /var/lib/ntfy/auth.db
auth-default-access: deny-all

attachment-cache-dir: /var/cache/ntfy
attachment-total-size-limit: 1G
attachment-expiry-duration: 3h
visitor-attachment-total-size-limit: 50m

log-level: info
```

- [ ] **Step 4: Créer odoo/odoo.conf**

Créer `infra/vps/odoo/odoo.conf` :

```ini
[options]
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
db_host = db
db_port = 5432
db_user = odoo
db_password = False
admin_passwd = False
workers = 2
max_cron_threads = 1
log_level = info
```

- [ ] **Step 5: Créer le répertoire addons Odoo**

```bash
mkdir -p infra/vps/odoo/addons
touch infra/vps/odoo/addons/.gitkeep
```

- [ ] **Step 6: Vérifier la syntaxe YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('infra/vps/docker-compose.yml'))" && echo "OK — YAML valide"
python3 -c "import yaml; yaml.safe_load(open('infra/vps/ntfy/server.yml'))" && echo "OK — YAML valide"
```

Expected (2 lignes): `OK — YAML valide`

- [ ] **Step 7: Commit**

```bash
git add infra/vps/
git commit -m "feat: docker-compose VPS — Odoo 19 CE + PostgreSQL 15 + ntfy.sh + webhook"
```

---

## Task 4: Webhook Twilio Voice — Application Flask

**Files:**
- Create: `infra/vps/webhook/requirements.txt`
- Create: `infra/vps/webhook/Dockerfile`
- Create: `infra/vps/webhook/app.py`

- [ ] **Step 1: Créer requirements.txt**

Créer `infra/vps/webhook/requirements.txt` :

```
flask==3.0.3
twilio==9.3.3
requests==2.32.3
```

- [ ] **Step 2: Créer le Dockerfile**

Créer `infra/vps/webhook/Dockerfile` :

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
```

- [ ] **Step 3: Créer app.py**

Créer `infra/vps/webhook/app.py` :

```python
import os
import xmlrpc.client
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Say

app = Flask(__name__)

ODOO_URL = os.environ["ODOO_URL"]
ODOO_DB = os.environ["ODOO_DB"]
ODOO_USER = os.environ["ODOO_USER"]
ODOO_API_KEY = os.environ["ODOO_API_KEY"]


def _odoo_client():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models


@app.route("/haccp/twiml", methods=["POST"])
def twiml_alert():
    device = request.args.get("device", "équipement")
    duration = request.args.get("duration", "20")
    alert_id = request.args.get("alert_id", "")

    response = VoiceResponse()
    response.say(
        f"Alerte H A C C P urgente. {device} dépasse le seuil depuis {duration} minutes. "
        "Appuyez sur 1 pour confirmer votre prise en charge.",
        language="fr-FR",
        voice="Polly.Lea",
    )
    gather = Gather(
        num_digits=1,
        action=f"/haccp/ack-call?alert_id={alert_id}",
        timeout=10,
    )
    gather.say(
        "Appuyez sur 1, ou restez en ligne pour déclencher l'escalade.",
        language="fr-FR",
        voice="Polly.Lea",
    )
    response.append(gather)
    response.say(
        "Pas de réponse. Le responsable suivant va être contacté.",
        language="fr-FR",
        voice="Polly.Lea",
    )
    return Response(str(response), mimetype="text/xml")


@app.route("/haccp/ack-call", methods=["POST"])
def ack_call():
    digit = request.form.get("Digits", "")
    alert_id = request.args.get("alert_id", "")

    response = VoiceResponse()
    if digit == "1" and alert_id:
        _acknowledge_alert(alert_id)
        response.say(
            "Prise en charge confirmée. Merci.",
            language="fr-FR",
            voice="Polly.Lea",
        )
    else:
        response.say(
            "Action non reconnue. Escalade maintenue.",
            language="fr-FR",
            voice="Polly.Lea",
        )
    return Response(str(response), mimetype="text/xml")


def _acknowledge_alert(alert_id: str):
    try:
        uid, models = _odoo_client()
        models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            "quality.alert", "write",
            [[int(alert_id)], {"user_id": uid}],
        )
    except Exception as exc:
        app.logger.error("Odoo ACK failed alert_id=%s: %s", alert_id, exc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

- [ ] **Step 4: Vérifier la syntaxe Python**

```bash
python3 -m py_compile infra/vps/webhook/app.py && echo "OK — syntaxe valide"
```

Expected: `OK — syntaxe valide`

- [ ] **Step 5: Commit**

```bash
git add infra/vps/webhook/
git commit -m "feat: webhook Twilio Voice — TwiML HACCP fr-FR Polly.Lea + ACK endpoint"
```

---

## Task 5: Script de test API Odoo + test MQTT

**Files:**
- Create: `scripts/test-odoo-api.py`
- Create: `scripts/test-mqtt-subscribe.sh`

- [ ] **Step 1: Créer scripts/test-odoo-api.py**

Créer `scripts/test-odoo-api.py` :

```python
#!/usr/bin/env python3
"""
Test API Odoo Qualité via XML-RPC.
Usage: python3 test-odoo-api.py --url http://<vps>:8069 --db odoo --key <api_key>
"""
import argparse
import sys
import xmlrpc.client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    print(f"[1] Connexion {args.url} — DB: {args.db}")
    common = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/common")
    uid = common.authenticate(args.db, args.user, args.key, {})
    if not uid:
        print("ERREUR : authentification échouée — vérifier URL, DB, user, api_key")
        sys.exit(1)
    print(f"    OK — UID: {uid}")

    models = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/object")

    print("[2] Lecture des QCPs disponibles")
    qcps = models.execute_kw(
        args.db, uid, args.key,
        "quality.point", "search_read",
        [[]], {"fields": ["id", "name"], "limit": 10},
    )
    if not qcps:
        print("    AVERTISSEMENT : aucun QCP — créer les QCPs dans Odoo d'abord (Task 11)")
        sys.exit(0)
    for q in qcps:
        print(f"    QCP #{q['id']}: {q['name']}")
    qcp_id = qcps[0]["id"]

    print(f"[3] Création quality.check test (5.8°C, QCP #{qcp_id})")
    check_id = models.execute_kw(
        args.db, uid, args.key,
        "quality.check", "create",
        [{"point_id": qcp_id, "measure": 5.8}],
    )
    print(f"    OK — quality.check ID: {check_id}")

    print("[4] Création quality.alert test")
    alert_id = models.execute_kw(
        args.db, uid, args.key,
        "quality.alert", "create",
        [{"name": "[TEST POC] Frigo 1 — 5.8°C > seuil 4°C"}],
    )
    print(f"    OK — quality.alert ID: {alert_id}")

    print("[5] Vérification quality.check")
    check = models.execute_kw(
        args.db, uid, args.key,
        "quality.check", "read",
        [[check_id]], {"fields": ["measure", "quality_state"]},
    )
    print(f"    measure={check[0]['measure']} state={check[0]['quality_state']}")

    print("\nOK — API Odoo Qualité fonctionnelle")
    print(f"  Supprimer les enregistrements de test : check={check_id}, alert={alert_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Créer scripts/test-mqtt-subscribe.sh**

Créer `scripts/test-mqtt-subscribe.sh` :

```bash
#!/bin/bash
# Test abonnement MQTT TTN — vérification réception payloads LHT65.
# Usage: ./test-mqtt-subscribe.sh <ttn_app_id> <ttn_api_key>
# Prérequis: apt install mosquitto-clients

TTN_APP_ID="${1:?Usage: $0 <ttn_app_id> <ttn_api_key>}"
TTN_API_KEY="${2:?Usage: $0 <ttn_app_id> <ttn_api_key>}"

echo "Abonnement MQTT TTN — app: ${TTN_APP_ID}"
echo "Topic: v3/${TTN_APP_ID}@ttn/devices/+/up"
echo "Ctrl+C pour arrêter"
echo "---"

mosquitto_sub \
    --host "eu1.cloud.thethings.network" \
    --port 8883 \
    --capath /etc/ssl/certs \
    --username "${TTN_APP_ID}@ttn" \
    --pw "${TTN_API_KEY}" \
    --topic "v3/${TTN_APP_ID}@ttn/devices/+/up" \
    --verbose
```

- [ ] **Step 3: Rendre exécutable + vérifier syntaxe**

```bash
chmod +x scripts/test-mqtt-subscribe.sh
python3 -m py_compile scripts/test-odoo-api.py && echo "OK — syntaxe valide"
```

Expected: `OK — syntaxe valide`

- [ ] **Step 4: Commit**

```bash
git add scripts/
git commit -m "feat: scripts test API Odoo Qualité (XML-RPC) + abonnement MQTT TTN"
```

---

## Task 6: Scripts backup Restic

**Files:**
- Create: `infra/ops121s/backup/restic-init.sh`
- Create: `infra/ops121s/backup/haccp-backup.cron`

- [ ] **Step 1: Créer restic-init.sh**

Créer `infra/ops121s/backup/restic-init.sh` :

```bash
#!/bin/bash
# Initialisation du repo Restic sur le VPS — à lancer une seule fois.
# Usage: RESTIC_PASSWORD=xxx VPS_HOST=backup@<ip> ./restic-init.sh
set -euo pipefail

VPS_HOST="${VPS_HOST:?Définir VPS_HOST=user@ip_vps}"
RESTIC_REPO="sftp:${VPS_HOST}:/backups/ops121s"

echo "Initialisation repo Restic : ${RESTIC_REPO}"
restic -r "${RESTIC_REPO}" init

echo ""
echo "OK — Repo Restic initialisé."
echo "  Vérifier avec : restic -r ${RESTIC_REPO} snapshots"
```

- [ ] **Step 2: Créer haccp-backup.cron**

Créer `infra/ops121s/backup/haccp-backup.cron` :

```cron
# Backup HACCP OPS121S → VPS
# Installer dans /etc/cron.d/haccp-backup (chmod 644)
#
# /etc/haccp-backup.env (chmod 600) doit contenir :
#   RESTIC_PASSWORD=votre_password_restic
#   VPS_HOST=backup@ip_vps
#   INFLUXDB_TOKEN=votre_token_influxdb

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# InfluxDB — backup quotidien à 2h00
0 2 * * * root source /etc/haccp-backup.env && \
  docker exec haccp-influxdb influx backup /tmp/influx-backup -t ${INFLUXDB_TOKEN} && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s backup /tmp/influx-backup --tag influxdb && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s forget --keep-daily 30 --keep-weekly 52 --keep-monthly 36 --prune && \
  docker exec haccp-influxdb rm -rf /tmp/influx-backup \
  >> /var/log/haccp-backup.log 2>&1

# SQLite vNode (buffer offline) — toutes les 15 minutes
*/15 * * * * root source /etc/haccp-backup.env && \
  sqlite3 /opt/vnode/data/buffer.db ".backup /tmp/vnode-buffer.db" && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s backup /tmp/vnode-buffer.db --tag sqlite-buffer && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s forget --keep-hourly 24 --prune && \
  rm -f /tmp/vnode-buffer.db \
  >> /var/log/haccp-backup.log 2>&1

# Config vNode + Docker Compose — hebdomadaire dimanche 3h00
0 3 * * 0 root source /etc/haccp-backup.env && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s backup \
    /opt/vnode/config /opt/docker/haccp --tag config && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s forget --keep-weekly 52 --prune \
  >> /var/log/haccp-backup.log 2>&1
```

- [ ] **Step 3: Rendre exécutable**

```bash
chmod +x infra/ops121s/backup/restic-init.sh
```

- [ ] **Step 4: Commit**

```bash
git add infra/ops121s/backup/
git commit -m "feat: scripts backup Restic — InfluxDB quotidien + SQLite 15min + config hebdo"
```

---

## Task 7: Documentation Dream Machine SE — VLANs + dual WAN

**Files:**
- Create: `docs/operations/dream-machine-se-config.md`

- [ ] **Step 1: Créer dream-machine-se-config.md**

Créer `docs/operations/dream-machine-se-config.md` :

```markdown
# Dream Machine SE — Configuration réseau HACCP

## Accès UniFi OS
- URL : https://192.168.1.1 (IP par défaut — changer immédiatement)
- Login initial : ubnt / ubnt

## 1. Dual WAN — Failover 4G/LTE (1NCE SIM)

Settings → Internet → WAN1 :
- Protocol : DHCP (ou PPPoE selon ISP)

Settings → Internet → WAN2 (SIM 1NCE) :
- Type : USB 4G LTE ou module SIM selon version UDM SE
- Mode : **Failover** (pas Load Balance)
- APN : `iot.1nce.net` (confirmer dans le portail 1NCE)
- Ping target : 8.8.8.8 (détection coupure)
- Failover delay : 30s

La nano-SIM 1NCE s'insère dans le slot SIM du Dream Machine SE.

## 2. VLANs

### VLAN 10 — IoT HACCP
Settings → Networks → Add Network :
- Name : IoT_HACCP
- VLAN ID : 10
- Subnet : 10.10.10.0/24
- DHCP : Enabled — Range 10.10.10.100–10.10.10.200
- DNS : 10.10.10.1
- Inter-VLAN routing : **Disabled** (isolation IoT)

### VLAN 20 — Wi-Fi Restaurant
- Name : WiFi_Restaurant
- VLAN ID : 20
- Subnet : 10.10.20.0/24
- DHCP : Enabled — Range 10.10.20.100–10.10.20.250

### VLAN 30 — Management
- Name : Management
- VLAN ID : 30
- Subnet : 10.10.30.0/24
- DHCP : Disabled (IPs fixes)

## 3. Affectation des ports PoE

| Port | Équipement | VLAN natif | PoE |
|------|-----------|-----------|-----|
| Port 1 | RAK7268 Gateway | 10 (IoT) | Activé (802.3af) |
| Port 2 | OPS121S | 10 (IoT) | Désactivé (alim. propre) |
| Port 8 | Switch management | 30 | Désactivé |

Settings → Switch Ports → Port 1 → Native VLAN : 10, PoE : Enabled.

## 4. Règle firewall — Isolation IoT ↔ Wi-Fi

Settings → Firewall → Rules → Create :
- Name : Block_IoT_to_WiFi
- Source : Network IoT_HACCP (10.10.10.0/24)
- Destination : Network WiFi_Restaurant (10.10.20.0/24)
- Action : Drop

## 5. IP fixes (DHCP reservations)

Settings → Networks → IoT_HACCP → DHCP Reservations :
- MAC RAK7268 → IP fixe 10.10.10.11
- MAC OPS121S → IP fixe 10.10.10.10

## 6. Vérification

Depuis OPS121S (10.10.10.10) :
```bash
# Accès Internet via Fibre (WAN1)
ping -c 4 8.8.8.8

# Test failover : débrancher câble WAN1, attendre 35s, vérifier continuité
ping -c 30 -i 2 8.8.8.8
# Les paquets doivent reprendre après ~30s (bascule sur 4G/LTE)

# Vérifier isolation VLAN : depuis IoT, la gateway Wi-Fi ne doit pas répondre
ping -c 2 10.10.20.1
# Expected: 100% packet loss (règle firewall)
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/dream-machine-se-config.md
git commit -m "docs: procédure Dream Machine SE VLANs + dual WAN failover 4G/LTE 1NCE"
```

---

## Task 8: Documentation RAK7268 + TTN

**Files:**
- Create: `docs/operations/rak7268-setup.md`
- Create: `docs/operations/ttn-setup.md`

- [ ] **Step 1: Créer rak7268-setup.md**

Créer `docs/operations/rak7268-setup.md` :

```markdown
# RAK7268 — Configuration gateway LoRaWAN EU868

## Connexion
- Brancher Port 1 du Dream Machine SE (PoE 802.3af) → RAK7268
- IP assignée par DHCP IoT VLAN → vérifier dans UniFi : Clients → 10.10.10.11
- WebUI : http://10.10.10.11 — Login : root / root (changer immédiatement)

## 1. Fréquence
LoRa Network → LoRaWAN Network Settings :
- Region : **EU868**
- Channel plan : EU868 (8 canaux standard TTN)

## 2. Connexion TTN (Basics Station — recommandé)
LoRa Network → Network Settings → Packet Forwarder → Basic Station :
- LNS URI : `wss://eu1.cloud.thethings.network:8887`
- CUPS URI : `https://eu1.cloud.thethings.network:443`
- Trust Certificate : laisser vide (certificat Let's Encrypt public)
- Gateway key : récupérée dans TTN Console (voir ttn-setup.md section 3)

Alternative (UDP Packet Forwarder si Basic Station non disponible) :
- Server Address : `eu1.cloud.thethings.network`
- Server Port : 1700

## 3. Vérification
Dashboard RAK7268 → LoRa Packet Logger :
- Après activation des LHT65, des paquets `uplink` doivent apparaître
- RSSI typique restaurant : -80 à -100 dBm
- SNR > 5 dB = signal acceptable

## 4. Conseil position
Placer la gateway en hauteur (2m+), proche du centre du restaurant.
Le LoRaWAN EU868 passe sans problème les cloisons et les portes de frigo.
```

- [ ] **Step 2: Créer ttn-setup.md**

Créer `docs/operations/ttn-setup.md` :

```markdown
# TTN — Application + Enregistrement LHT65

## 1. Compte TTN
URL : https://eu1.cloud.thethings.network
Région : **Europe 1** (eu1.cloud.thethings.network)

## 2. Créer l'Application
Applications → Add Application :
- Application ID : `haccp-restaurant-poc`
- Name : HACCP Restaurant POC — AIFluence Digital

## 3. Enregistrer la Gateway RAK7268
Gateways → Register Gateway :
- Gateway EUI : sur l'étiquette RAK7268 (ex: AA555A0000000101)
- Gateway ID : `rak7268-haccp-restaurant`
- Frequency Plan : **Europe 863-870 MHz (SF9 for RX2)**
- Récupérer la Gateway key pour la configuration Basic Station (section rak7268-setup.md)

## 4. Enregistrer les 3 capteurs LHT65

Applications → haccp-restaurant-poc → End Devices → Add End Device :

### Via Device Repository (recommandé)
- Brand : **Dragino**
- Model : **LHT65**
- Hardware Ver : 1.x, Firmware Ver : 1.x
- Frequency Plan : Europe 863-870 MHz (SF9 for RX2)
- Activation : **OTAA**

Les Device EUI et App EUI sont sur l'étiquette de chaque LHT65.
AppKey : cliquer "Generate" → **conserver précieusement** (saisie dans le capteur).

### Device IDs
| Capteur | Device ID TTN | Affectation physique |
|---------|-------------|---------------------|
| LHT65 #1 | `lht65-frigo-positif` | Frigo positif (sonde externe plongeante) |
| LHT65 #2 | `lht65-congelateur` | Congélateur (sonde externe plongeante) |
| LHT65 #3 | `lht65-stockage-sec` | Stockage sec (capteur interne T° + HR) |

## 5. Payload Formatter
Applications → haccp-restaurant-poc → Payload Formatters → Uplink :
- Type : **Use Device Repository Formatters**

Le codec Dragino LHT65 est inclus dans le TTN Device Repository.
Payload décodé attendu : `{"temperature_1": 3.5, "humidity": 62.1, "battery_voltage": 3.1}`

## 6. Intégration MQTT TTN
Applications → haccp-restaurant-poc → Integrations → MQTT :
- Générer une API Key (scope : `Read application traffic (uplink)`)
- **Conserver** : utilisée dans la configuration vNode

Paramètres MQTT TTN :
- Host : `eu1.cloud.thethings.network`
- Port : 8883 (TLS)
- Username : `haccp-restaurant-poc@ttn`
- Password : `<api_key générée>`
- Topic uplink : `v3/haccp-restaurant-poc@ttn/devices/+/up`

## 7. Activation physique des LHT65
Pour chaque capteur :
1. Insérer les 2 piles AA lithium
2. Appuyer 3× rapidement sur le bouton ACT → LED clignote (Join Request)
3. TTN Console → End Devices → `lht65-xxx` → Live Data → vérifier "Join Accept"
4. Attendre 10 min → vérifier un uplink avec payload décodé

## 8. Test abonnement MQTT (depuis OPS121S ou laptop)
```bash
# Prérequis : apt install mosquitto-clients
./scripts/test-mqtt-subscribe.sh haccp-restaurant-poc <api_key_ttn>
```
Expected : payloads JSON des LHT65 s'affichent toutes les ~10 minutes.
```

- [ ] **Step 3: Commit**

```bash
git add docs/operations/rak7268-setup.md docs/operations/ttn-setup.md
git commit -m "docs: procédures RAK7268 gateway + TTN application + LHT65 enregistrement OTAA"
```

---

## Task 9: Documentation OPS121S — Installation Ubuntu + Docker

**Files:**
- Create: `docs/operations/ops121s-setup.md`

- [ ] **Step 1: Créer docs/operations/ops121s-setup.md**

Créer `docs/operations/ops121s-setup.md` :

```markdown
# OPS121S — Installation Ubuntu 20.04 LTS + Docker Engine + Stack HACCP

## 1. Installation Ubuntu 20.04 LTS Server
- ISO : ubuntu-20.04.6-live-server-amd64.iso
- Partitionnement : LVM auto (tout le SSD 256 GB)
- Packages à l'installation : OpenSSH Server uniquement
- Hostname : ops121s-haccp
- User principal : haccp

Note production : Ubuntu 20.04 est hors support standard depuis avril 2025.
Migrer vers 22.04 LTS avant tout déploiement client réel.

## 2. Post-installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git sqlite3 restic mosquitto-clients
```

## 3. Docker Engine sur Ubuntu 20.04
```bash
# Supprimer anciens packages
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Dépendances
sudo apt install -y ca-certificates gnupg lsb-release

# Clé GPG Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Repo Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Vérification
docker --version
docker compose version
```

Expected :
```
Docker version 26.x.x, build ...
Docker Compose version v2.x.x
```

## 4. Permissions Docker
```bash
sudo usermod -aG docker haccp
newgrp docker
docker run --rm hello-world
```
Expected: `Hello from Docker!`

## 5. Déployer la stack HACCP

```bash
# Copier les fichiers depuis le dépôt git
sudo mkdir -p /opt/docker/haccp
sudo chown haccp:haccp /opt/docker/haccp

# Depuis la machine de développement :
scp -r infra/ops121s/* haccp@10.10.10.10:/opt/docker/haccp/

# Sur l'OPS121S :
cd /opt/docker/haccp
cp .env.example .env
nano .env   # Remplir INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_TOKEN

# Démarrer Mosquitto + InfluxDB + Portainer (sans vNode dans un premier temps)
docker compose up -d mosquitto influxdb portainer
docker compose ps
```

Expected :
```
NAME                STATUS
haccp-mosquitto     running
haccp-influxdb      running
haccp-portainer     running
```

## 6. Vérification Mosquitto
```bash
# Pub/sub local (deux terminaux)
mosquitto_sub -h localhost -p 1883 -t "test/#" &
mosquitto_pub -h localhost -p 1883 -t "test/haccp" -m '{"temp":3.5}'
```
Expected: `{"temp":3.5}` s'affiche dans le subscriber. Ctrl+C pour arrêter.

## 7. Vérification InfluxDB
```bash
# Depuis le VLAN Management : http://10.10.10.10:8086
# Login : INFLUXDB_USER / INFLUXDB_PASSWORD
# Vérifier que le bucket "haccp" est présent
```

## 8. Portainer
```bash
# http://10.10.10.10:9000 — créer le compte admin au premier accès
# Vérifier les 3 containers Running
```

## 9. Ajouter vNode à la stack
```bash
# Une fois l'image vNode obtenue auprès de Vester :
# 1. Charger l'image : docker load -i vnode-automation.tar
# 2. Mettre à jour l'image dans docker-compose.yml
docker compose up -d vnode
docker compose logs vnode   # Vérifier démarrage (mode démo : redémarre toutes les 2h)
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/ops121s-setup.md
git commit -m "docs: procédure installation OPS121S Ubuntu 20.04 + Docker Engine + stack HACCP"
```

---

## Task 10: Documentation VPS Hetzner — Odoo 19 CE

**Files:**
- Create: `docs/operations/vps-odoo-setup.md`

- [ ] **Step 1: Créer docs/operations/vps-odoo-setup.md**

Créer `docs/operations/vps-odoo-setup.md` :

```markdown
# VPS Hetzner — Déploiement Odoo 19 CE + ntfy.sh + Webhook Twilio

## 1. Créer le VPS Hetzner
- Console : https://console.hetzner.cloud
- Type : **CX21** (2 vCPU, 4 GB RAM, 40 GB SSD) — ~5€/mois
- OS : Ubuntu 22.04 LTS
- SSH Key : ajouter votre clé publique

## 2. Docker Engine sur Ubuntu 22.04
```bash
ssh root@<ip_vps>

apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
docker --version
```

## 3. Déployer la stack VPS

```bash
mkdir -p /opt/docker/odoo
# Depuis la machine de développement :
scp -r infra/vps/* root@<ip_vps>:/opt/docker/odoo/

# Sur le VPS :
cd /opt/docker/odoo
cp .env.example .env
nano .env   # Remplir POSTGRES_PASSWORD, ODOO_API_KEY, TWILIO_*

# Démarrer PostgreSQL + Odoo + ntfy en premier
docker compose up -d db odoo ntfy
docker compose logs -f odoo
# Attendre : "odoo.service.server: HTTP service (werkzeug) running on ..."
```

## 4. Initialiser la base de données Odoo
```
Ouvrir http://<ip_vps>:8069/web/database/manager
→ Create Database
  - Database Name : odoo
  - Email : admin@aifluencedigital.fr
  - Password : <choisir un password admin sécurisé>
  - Language : French (fr)
  - Country : France
  - Demo data : Non (décoché)
```

## 5. Installer le module Quality Control
```
Apps → Rechercher "Quality Control" → Installer
```
Vérifier : le menu "Quality" apparaît dans la barre de navigation principale.

## 6. Générer une API Key Odoo
```
Settings → Technical → API Keys → New
- Name : vNode HACCP
- Expiration : (vide = permanente)
→ Copier la clé → mettre dans /opt/docker/odoo/.env (ODOO_API_KEY)
```

## 7. Démarrer le webhook Twilio
```bash
docker compose up -d webhook
docker compose logs webhook
```
Expected: `Running on http://0.0.0.0:5000`

## 8. Configurer ntfy.sh

### Mettre à jour server.yml avec l'IP réelle
```bash
# Éditer /opt/docker/odoo/ntfy/server.yml
# Remplacer VOTRE_IP_VPS par l'IP Hetzner réelle
docker compose restart ntfy
```

### Créer l'utilisateur ntfy
```bash
docker exec odoo-ntfy ntfy user add --role=admin haccp-admin
# Saisir un mot de passe sécurisé

docker exec odoo-ntfy ntfy access haccp-admin haccp-alerts rw
```

### Test notification push
```bash
curl -u haccp-admin:<password> \
  -d "Test HACCP ntfy — POC AIFluence Digital" \
  http://<ip_vps>:8080/haccp-alerts
```
Expected : notification reçue dans l'app ntfy sur smartphone.

## 9. Ouvrir les ports firewall VPS
```bash
# Hetzner Firewall (console cloud) → ajouter règles Inbound :
# TCP 8069  — Odoo
# TCP 8080  — ntfy.sh
# TCP 5000  — webhook Twilio
# TCP 22    — SSH
```

## 10. Vérification finale VPS
```bash
docker compose ps
```
Expected :
```
NAME            STATUS
odoo-db         running
odoo-app        running
odoo-ntfy       running
odoo-webhook    running
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/vps-odoo-setup.md
git commit -m "docs: procédure déploiement VPS Hetzner — Odoo 19 CE + ntfy.sh + webhook"
```

---

## Task 11: Documentation Odoo Qualité — Configuration QCPs

**Files:**
- Create: `docs/operations/odoo-qualite-qcp.md`

- [ ] **Step 1: Créer docs/operations/odoo-qualite-qcp.md**

Créer `docs/operations/odoo-qualite-qcp.md` :

```markdown
# Odoo Qualité — Configuration QCPs HACCP + Test API

## 1. Activer le mode développeur
Settings → Activate developer mode (lien en bas de la page Settings)

## 2. Créer les 3 Quality Control Points (QCPs)

Quality → Configuration → Control Points → New

### QCP Frigo Positif
- Name : **Frigo Positif — Surveillance HACCP**
- Control Type : **Measure**
- Norm : 2 (température cible en °C)
- Tolerance Min : -30
- Tolerance Max : 4 (seuil critique HACCP)
- Unit of Measure : °C

### QCP Congélateur
- Name : **Congélateur — Surveillance HACCP**
- Control Type : **Measure**
- Norm : -18
- Tolerance Min : -40
- Tolerance Max : -15
- Unit of Measure : °C

### QCP Stockage Sec Humidité
- Name : **Stockage Sec — Humidité HACCP**
- Control Type : **Measure**
- Norm : 55
- Tolerance Min : 0
- Tolerance Max : 75
- Unit of Measure : %

## 3. Récupérer les IDs des QCPs

En mode développeur, l'ID est visible dans l'URL quand vous ouvrez un QCP :
`/web#id=X&model=quality.point`

| QCP | ID Odoo | À noter pour vNode |
|-----|---------|-------------------|
| Frigo Positif | ... | QCP_ID_FRIGO_POSITIF |
| Congélateur | ... | QCP_ID_CONGELATEUR |
| Stockage Sec | ... | QCP_ID_STOCKAGE_SEC |

Ces IDs sont utilisés dans la configuration vNode (Task 12).

## 4. Tester la création manuelle
Quality → Quality Checks → New :
- Control Point : Frigo Positif — Surveillance HACCP
- Measure : 3.5 → Status : **Pass** (3.5 ≤ 4°C) ✓

Créer un second check :
- Measure : 6.2 → Status : **Fail** (6.2 > 4°C) ✓
Une quality.alert peut se créer automatiquement (selon config QCP).

## 5. Exécuter le script de test API

```bash
python3 scripts/test-odoo-api.py \
  --url http://<ip_vps>:8069 \
  --db odoo \
  --user admin \
  --key <odoo_api_key>
```

Expected :
```
[1] Connexion http://<ip_vps>:8069 — DB: odoo
    OK — UID: 2
[2] Lecture des QCPs disponibles
    QCP #1: Frigo Positif — Surveillance HACCP
    QCP #2: Congélateur — Surveillance HACCP
    QCP #3: Stockage Sec — Humidité HACCP
[3] Création quality.check test (5.8°C, QCP #1)
    OK — quality.check ID: 3
[4] Création quality.alert test
    OK — quality.alert ID: 1
[5] Vérification quality.check
    measure=5.8 state=fail
OK — API Odoo Qualité fonctionnelle
```

## 6. Créer l'utilisateur responsable restaurant
Settings → Users → New :
- Name : Responsable Cuisine
- Email : responsable@restaurant.fr
- Application accesses : Quality → Administrateur
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/odoo-qualite-qcp.md
git commit -m "docs: procédure configuration QCPs Odoo Qualité HACCP + test API XML-RPC"
```

---

## Task 12: Documentation vNode — Configuration complète

**Files:**
- Create: `docs/operations/vnode-config.md`
- Create: `infra/ops121s/vnode/config/rules-example.json`

- [ ] **Step 1: Créer docs/operations/vnode-config.md**

Créer `docs/operations/vnode-config.md` :

```markdown
# vNode Automation — Configuration MQTT + REST API + Règles HACCP

## Prérequis
- Stack Docker OPS121S opérationnelle (Mosquitto, InfluxDB, Portainer)
- TTN Application configurée + MQTT API Key (ttn-setup.md)
- Odoo 19 CE opérationnel + QCPs créés + API Key Odoo (odoo-qualite-qcp.md)
- IDs des 3 QCPs notés

## 1. Lancer vNode en mode démo POC

```bash
cd /opt/docker/haccp
docker compose up -d vnode
docker compose logs -f vnode
```

En mode démo, vNode redémarre automatiquement toutes les 2h (comportement normal).

## 2. Accéder à l'interface vNode

Se référer à la documentation Vester pour le port et les identifiants de l'UI vNode.
URL type : http://10.10.10.10:<PORT_VNODE>

## 3. Module MQTT Client — Connexion TTN

Modules → MQTT Client → Add Connection :
| Paramètre | Valeur |
|-----------|--------|
| Name | TTN_HACCP |
| Host | eu1.cloud.thethings.network |
| Port | 8883 |
| SSL/TLS | Enabled |
| Username | haccp-restaurant-poc@ttn |
| Password | `<api_key TTN>` |
| Client ID | vnode-haccp-ops121s |
| Topic Subscribe | v3/haccp-restaurant-poc@ttn/devices/+/up |
| QoS | 1 |

Tester → Expected : "Connected"

## 4. Module MQTT Client — Connexion Mosquitto local

Add Connection (second) :
| Paramètre | Valeur |
|-----------|--------|
| Name | Mosquitto_Local |
| Host | mosquitto (service Docker) |
| Port | 1883 |
| SSL/TLS | Disabled |
| QoS | 0 |

## 5. Mapping payload TTN → champs normalisés

Pour chaque device TTN (`lht65-frigo-positif`, `lht65-congelateur`, `lht65-stockage-sec`) :

```json
{
  "device_id": "$.end_device_ids.device_id",
  "timestamp": "$.received_at",
  "temperature": "$.uplink_message.decoded_payload.temperature_1",
  "humidity": "$.uplink_message.decoded_payload.humidity",
  "battery_v": "$.uplink_message.decoded_payload.battery_voltage"
}
```

## 6. Module REST API Client — Connexion Odoo

Modules → REST API Client → Add Target :
| Paramètre | Valeur |
|-----------|--------|
| Name | Odoo_HACCP |
| Base URL | http://`<ip_vps>`:8069/xmlrpc/2/object |
| Auth | Basic — user: admin, password: `<odoo_api_key>` |
| Content-Type | application/xml |
| Timeout | 10s |
| Retry on failure | 3 |

## 7. Règle HACCP — Frigo Positif

Rules → Add Rule :

**Trigger :** device `lht65-frigo-positif`, field `temperature` > 4.0

**Actions :**
1. Créer quality.check dans Odoo :
   - Method : execute_kw
   - Model : quality.check, method : create
   - Payload : `{"point_id": <QCP_ID_FRIGO_POSITIF>, "measure": {{temperature}}}`

2. Créer quality.alert dans Odoo :
   - Model : quality.alert, method : create
   - Payload : `{"name": "Dépassement frigo positif — {{temperature}}°C"}`

3. Push ntfy :
   - HTTP POST `http://<ip_vps>:8080/haccp-alerts`
   - Auth : Basic haccp-admin:<password>
   - Body : `HACCP Alerte : Frigo positif {{temperature}}°C > 4°C`

**Cooldown :** 10 min (éviter les alertes répétitives sur chaque uplink)

## 8. Règle HACCP — Congélateur

**Trigger :** device `lht65-congelateur`, field `temperature` > -15.0

**Actions identiques à Frigo Positif** (QCP_ID_CONGELATEUR, message adapté)

## 9. Règle HACCP — Stockage Sec Humidité

**Trigger :** device `lht65-stockage-sec`, field `humidity` > 75.0

**Actions :**
1. quality.check (QCP_ID_STOCKAGE_SEC, measure : {{humidity}})
2. quality.alert (nom : "Humidité stockage sec — {{humidity}}%")
3. Push ntfy adapté

**Cooldown :** 30 min

## 10. Persistance InfluxDB

Outputs → InfluxDB :
| Paramètre | Valeur |
|-----------|--------|
| URL | http://influxdb:8086 |
| Token | `<INFLUXDB_TOKEN>` |
| Org | aifluence |
| Bucket | haccp |
| Measurement | temperature_sensor |
| Tags | device_id, zone |
| Fields | temperature, humidity, battery_v |

## 11. Vérifier l'ingestion en temps réel

```bash
# Logs vNode
docker compose logs -f vnode

# Vérifier InfluxDB — 5 dernières mesures
source /opt/docker/haccp/.env
curl -s "http://localhost:8086/api/v2/query?org=aifluence" \
  -H "Authorization: Token ${INFLUXDB_TOKEN}" \
  -H "Content-Type: application/vnd.flux" \
  --data-raw '
from(bucket: "haccp")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "temperature_sensor")
  |> last()
'
```

Expected : JSON avec les dernières mesures des capteurs actifs.
```

- [ ] **Step 2: Créer rules-example.json**

Créer `infra/ops121s/vnode/config/rules-example.json` :

```json
{
  "_doc": "Structure de référence des règles HACCP vNode — adapter aux écrans UI vNode réels",
  "rules": [
    {
      "name": "HACCP_Frigo_Positif_Alerte",
      "trigger": {
        "device_id": "lht65-frigo-positif",
        "field": "temperature",
        "operator": ">",
        "threshold": 4.0
      },
      "cooldown_minutes": 10,
      "actions": [
        {
          "type": "odoo_xmlrpc",
          "model": "quality.check",
          "method": "create",
          "values": {
            "point_id": "QCP_ID_FRIGO_POSITIF",
            "measure": "{{temperature}}"
          }
        },
        {
          "type": "odoo_xmlrpc",
          "model": "quality.alert",
          "method": "create",
          "values": {
            "name": "Dépassement frigo positif — {{temperature}}°C > 4°C"
          }
        },
        {
          "type": "http_post",
          "url": "http://IP_VPS:8080/haccp-alerts",
          "auth_basic": "haccp-admin:PASSWORD",
          "body": "HACCP Alerte : Frigo positif {{temperature}}°C > 4°C"
        }
      ]
    },
    {
      "name": "HACCP_Congelateur_Alerte",
      "trigger": {
        "device_id": "lht65-congelateur",
        "field": "temperature",
        "operator": ">",
        "threshold": -15.0
      },
      "cooldown_minutes": 10,
      "actions": [
        {
          "type": "odoo_xmlrpc",
          "model": "quality.check",
          "method": "create",
          "values": {
            "point_id": "QCP_ID_CONGELATEUR",
            "measure": "{{temperature}}"
          }
        },
        {
          "type": "odoo_xmlrpc",
          "model": "quality.alert",
          "method": "create",
          "values": {
            "name": "Dépassement congélateur — {{temperature}}°C > -15°C"
          }
        },
        {
          "type": "http_post",
          "url": "http://IP_VPS:8080/haccp-alerts",
          "auth_basic": "haccp-admin:PASSWORD",
          "body": "HACCP Alerte : Congélateur {{temperature}}°C > -15°C"
        }
      ]
    },
    {
      "name": "HACCP_Stockage_Humidite_Alerte",
      "trigger": {
        "device_id": "lht65-stockage-sec",
        "field": "humidity",
        "operator": ">",
        "threshold": 75.0
      },
      "cooldown_minutes": 30,
      "actions": [
        {
          "type": "odoo_xmlrpc",
          "model": "quality.check",
          "method": "create",
          "values": {
            "point_id": "QCP_ID_STOCKAGE_SEC",
            "measure": "{{humidity}}"
          }
        },
        {
          "type": "odoo_xmlrpc",
          "model": "quality.alert",
          "method": "create",
          "values": {
            "name": "Humidité stockage sec — {{humidity}}% > 75%"
          }
        }
      ]
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add docs/operations/vnode-config.md infra/ops121s/vnode/config/rules-example.json
git commit -m "docs: procédure configuration vNode MQTT Client + REST API Odoo + règles HACCP"
```

---

## Task 13: Documentation alertes Twilio Voice + SMS

**Files:**
- Create: `docs/operations/alertes-twilio-sms.md`

- [ ] **Step 1: Créer docs/operations/alertes-twilio-sms.md**

Créer `docs/operations/alertes-twilio-sms.md` :

```markdown
# Alertes — Twilio Voice + SMS

## 1. Compte Twilio (POC)
URL : https://console.twilio.com
Le compte essai gratuit inclut ~15€ de crédit — suffisant pour valider le POC.

### Acheter un numéro France
Phone Numbers → Buy a Number → Country: France → Voice + SMS → ~1€/mois

### Variables à récupérer
- **TWILIO_ACCOUNT_SID** : dans le Dashboard (format ACxx...)
- **TWILIO_AUTH_TOKEN** : Dashboard Twilio
- **TWILIO_FROM_NUMBER** : numéro acheté (format +33XXXXXXXXX)

Ajouter dans `/opt/docker/odoo/.env` :
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+33XXXXXXXXX
```

## 2. Configurer l'escalade vocale dans vNode

Dans vNode → Rules → HACCP_Frigo_Positif_Alerte → Escalation (t+20 min sans ACK) :

Ajouter une action HTTP POST vers l'API Twilio Calls :
- URL : `https://api.twilio.com/2010-04-01/Accounts/<ACCOUNT_SID>/Calls.json`
- Method : POST
- Auth : Basic (`<ACCOUNT_SID>:<AUTH_TOKEN>`)
- Body (form-encoded) :
  ```
  To=+33XXXXXXXXX_RESPONSABLE
  From=+33XXXXXXXXX_TWILIO
  Url=http://<ip_vps>:5000/haccp/twiml?device=Frigo+positif&duration=20&alert_id={{alert_id}}
  ```

Répéter pour les règles Congélateur et Stockage Sec.

## 3. Tester le webhook TwiML (sans appel réel)
```bash
curl "http://<ip_vps>:5000/haccp/twiml?device=Frigo+positif&duration=20&alert_id=1"
```

Expected :
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="fr-FR" voice="Polly.Lea">Alerte H A C C P urgente. Frigo positif
    dépasse le seuil depuis 20 minutes. Appuyez sur 1 pour confirmer votre prise en charge.</Say>
  <Gather numDigits="1" action="/haccp/ack-call?alert_id=1" timeout="10">
    <Say language="fr-FR" voice="Polly.Lea">Appuyez sur 1, ou restez en ligne
      pour déclencher l'escalade.</Say>
  </Gather>
  <Say language="fr-FR" voice="Polly.Lea">Pas de réponse.
    Le responsable suivant va être contacté.</Say>
</Response>
```

## 4. Déclencher un appel de test Twilio
```bash
curl -X POST \
  "https://api.twilio.com/2010-04-01/Accounts/<ACCOUNT_SID>/Calls.json" \
  -u "<ACCOUNT_SID>:<AUTH_TOKEN>" \
  --data-urlencode "To=+33XXXXXXXXX" \
  --data-urlencode "From=+33XXXXXXXXX_TWILIO" \
  --data-urlencode "Url=http://<ip_vps>:5000/haccp/twiml?device=Frigo+positif&duration=20&alert_id=1"
```

Expected : appel reçu, voix Polly.Lea en français, pression sur 1 → confirmation.

## 5. SMS — API Free Mobile (optionnel, si abonné Free)
Espace client Free Mobile → Mon Compte → Mes options → Activer "Notifications par SMS"
- Identifiant : (dans l'espace client)
- Clé API : (dans l'espace client)

Dans vNode → Rules → Action HTTP GET :
```
https://smsapi.free-mobile.fr/sendmsg?user=<ID>&pass=<KEY>&msg=HACCP+{{device_id}}+{{temperature}}%C2%B0C
```

## 6. SMS — OVH SMS (clients RGPD strict, données 100% France)
- Console OVH : https://www.ovhcloud.com/fr/sms/
- Créer un compte SMS OVH, acheter des crédits SMS
- API endpoint : `https://www.ovh.com/cgi-bin/sms/http2sms.cgi`
- Paramètres : account, login, password, from, to, message

Dans vNode → Rules → Action HTTP POST vers l'API OVH SMS.
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/alertes-twilio-sms.md
git commit -m "docs: procédure alertes Twilio Voice fr-FR Polly.Lea + SMS Free Mobile + OVH SMS"
```

---

## Task 14: Déploiement backup Restic sur OPS121S

Cette tâche s'exécute sur l'OPS121S après les Tasks 9 et 10.

- [ ] **Step 1: Préparer l'utilisateur backup sur le VPS**

Sur le VPS Hetzner (SSH root) :
```bash
useradd -m -s /bin/bash backup
mkdir -p /backups/ops121s
chown backup:backup /backups/ops121s
```

- [ ] **Step 2: Générer une clé SSH dédiée backup (sur OPS121S)**

```bash
ssh-keygen -t ed25519 -f ~/.ssh/haccp_backup -N "" -C "haccp-backup@ops121s"
ssh-copy-id -i ~/.ssh/haccp_backup.pub backup@<ip_vps>

# Vérifier la connexion sans passphrase
ssh -i ~/.ssh/haccp_backup backup@<ip_vps> "echo SSH OK"
```

Expected: `SSH OK`

- [ ] **Step 3: Ajouter la config SSH dans ~/.ssh/config**

Sur l'OPS121S :
```bash
cat >> ~/.ssh/config << 'EOF'
Host haccp-vps-backup
    HostName <ip_vps>
    User backup
    IdentityFile ~/.ssh/haccp_backup
EOF
```

- [ ] **Step 4: Initialiser le repo Restic**

```bash
cd /opt/docker/haccp
export RESTIC_PASSWORD="votre_password_restic_securise_min12chars"
export VPS_HOST="haccp-vps-backup"

chmod +x backup/restic-init.sh
VPS_HOST=${VPS_HOST} RESTIC_PASSWORD=${RESTIC_PASSWORD} ./backup/restic-init.sh
```

Expected:
```
Initialisation repo Restic : sftp:haccp-vps-backup:/backups/ops121s
created restic repository xxxxxxxx at sftp:haccp-vps-backup:/backups/ops121s
OK — Repo Restic initialisé.
```

- [ ] **Step 5: Créer le fichier d'environnement cron**

```bash
sudo tee /etc/haccp-backup.env > /dev/null << 'EOF'
RESTIC_PASSWORD=votre_password_restic_securise_min12chars
VPS_HOST=haccp-vps-backup
INFLUXDB_TOKEN=votre_influxdb_token_depuis_.env
EOF
sudo chmod 600 /etc/haccp-backup.env
```

- [ ] **Step 6: Installer et tester le cron**

```bash
sudo cp /opt/docker/haccp/backup/haccp-backup.cron /etc/cron.d/haccp-backup
sudo chmod 644 /etc/cron.d/haccp-backup
sudo systemctl restart cron

# Test manuel backup InfluxDB
source /etc/haccp-backup.env
docker exec haccp-influxdb influx backup /tmp/influx-backup -t ${INFLUXDB_TOKEN} && \
  restic -r sftp:${VPS_HOST}:/backups/ops121s backup /tmp/influx-backup --tag influxdb && \
  echo "OK — Backup test réussi"
```

Expected: `OK — Backup test réussi`

- [ ] **Step 7: Vérifier les snapshots**

```bash
source /etc/haccp-backup.env
restic -r sftp:${VPS_HOST}:/backups/ops121s snapshots
```

Expected: au moins 1 snapshot listé avec tag `influxdb`.

---

## Task 15: Tests bout en bout

Valide la chaîne complète : LHT65 → TTN → vNode → Odoo Qualité → Alertes.

- [ ] **Step 1: Vérifier les 3 LHT65 actifs sur TTN**

TTN Console → haccp-restaurant-poc → End Devices :
- Chaque device doit afficher "Last seen: < 15 minutes"
- Live Data → vérifier payload décodé : `temperature_1`, `humidity`, `battery_voltage`

- [ ] **Step 2: Vérifier les uplinks dans Mosquitto (OPS121S)**

```bash
mosquitto_sub -h localhost -p 1883 \
  -t "v3/haccp-restaurant-poc@ttn/devices/+/up" -v
```

Expected : payloads JSON TTN apparaissent toutes les ~10 minutes.

- [ ] **Step 3: Vérifier la persistance InfluxDB**

```bash
source /opt/docker/haccp/.env
curl -s "http://localhost:8086/api/v2/query?org=aifluence" \
  -H "Authorization: Token ${INFLUXDB_TOKEN}" \
  -H "Content-Type: application/vnd.flux" \
  --data-raw '
from(bucket: "haccp")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "temperature_sensor")
  |> last()
'
```

Expected : JSON avec les dernières mesures des 3 capteurs.

- [ ] **Step 4: Vérifier les quality.check dans Odoo**

```bash
python3 scripts/test-odoo-api.py \
  --url http://<ip_vps>:8069 \
  --db odoo \
  --user admin \
  --key <odoo_api_key>
```

Dans l'UI Odoo : Quality → Quality Checks → vérifier les enregistrements créés par vNode.

- [ ] **Step 5: Simuler un dépassement de seuil via TTN**

TTN Console → End Devices → lht65-frigo-positif → Simulate Uplink :
```json
{
  "temperature_1": 7.5,
  "humidity": 62.0,
  "battery_voltage": 3.1
}
```

Dans les 30 secondes, vérifier :
- ✓ Notification push ntfy reçue sur smartphone
- ✓ SMS reçu (si Free Mobile API configurée)
- ✓ Odoo : Quality → Quality Alerts → nouvelle alerte "Dépassement frigo positif 7.5°C"

- [ ] **Step 6: Tester l'appel vocal Twilio**

```bash
curl -X POST \
  "https://api.twilio.com/2010-04-01/Accounts/<ACCOUNT_SID>/Calls.json" \
  -u "<ACCOUNT_SID>:<AUTH_TOKEN>" \
  --data-urlencode "To=+33XXXXXXXXX" \
  --data-urlencode "From=+33XXXXXXXXX_TWILIO" \
  --data-urlencode "Url=http://<ip_vps>:5000/haccp/twiml?device=Frigo+positif&duration=20&alert_id=1"
```

Expected :
- ✓ Appel reçu
- ✓ Voix Polly.Lea en français lit le script d'alerte
- ✓ Appui sur 1 → "Prise en charge confirmée"
- ✓ Odoo : quality.alert #1 mise à jour

- [ ] **Step 7: Tester le fallback vNode (Odoo indisponible)**

```bash
# Arrêter Odoo temporairement
cd /opt/docker/odoo && docker compose stop odoo

# Sur OPS121S — surveiller les logs vNode (~30s)
docker compose logs -f vnode
# Expected : timeout API Odoo → envoi direct ntfy + buffer SQLite

# Relancer Odoo
docker compose start odoo

# Vérifier la synchronisation rétroactive des mesures bufferisées
# Expected dans les 60s : les quality.check du buffer apparaissent dans Odoo
```

- [ ] **Step 8: Exporter un rapport PDF HACCP**

Dans Odoo : Quality → Quality Checks → sélectionner les checks de la journée → Print → vérifier le PDF généré (horodatage, valeurs, statut Pass/Fail).

- [ ] **Step 9: Vérifier le dernier snapshot Restic**

```bash
source /etc/haccp-backup.env
restic -r sftp:${VPS_HOST}:/backups/ops121s snapshots
restic -r sftp:${VPS_HOST}:/backups/ops121s restore latest \
  --target /tmp/restic-restore --tag sqlite-buffer
ls -la /tmp/restic-restore/
```

Expected: `vnode-buffer.db` présent dans le répertoire de restauration.

- [ ] **Step 10: Commit final**

```bash
git status
git add .
git commit -m "chore: documentation opérationnelle complète POC HACCP IoT v1"
```

---

## Checklist finale POC

| Composant | Statut |
|-----------|--------|
| Dépôt git initialisé + tous les fichiers infra | ☐ |
| Dream Machine SE — VLANs IoT/WiFi/Mgmt + dual WAN 4G 1NCE | ☐ |
| RAK7268 — Connecté TTN EU868, paquets gateway reçus | ☐ |
| LHT65 #1 Frigo positif — OTAA OK, uplinks TTN actifs | ☐ |
| LHT65 #2 Congélateur — OTAA OK, uplinks TTN actifs | ☐ |
| LHT65 #3 Stockage sec — OTAA OK, uplinks TTN actifs | ☐ |
| OPS121S — Docker stack (Mosquitto + InfluxDB + Portainer + vNode) | ☐ |
| vNode — MQTT TTN connecté, règles HACCP actives, InfluxDB alimenté | ☐ |
| VPS Hetzner — Odoo 19 CE + ntfy.sh + webhook Twilio opérationnels | ☐ |
| Odoo — 3 QCPs configurés, quality.check créés automatiquement | ☐ |
| Alertes push ntfy — reçues sur smartphone en < 30s | ☐ |
| SMS — Free Mobile ou OVH SMS fonctionnel | ☐ |
| Appel vocal Twilio — Polly.Lea fr-FR, ACK par touche 1 | ☐ |
| Fallback vNode — testé et validé | ☐ |
| Backup Restic — premier snapshot vérifié, cron actif | ☐ |
| Rapport PDF HACCP — exporté depuis Odoo | ☐ |

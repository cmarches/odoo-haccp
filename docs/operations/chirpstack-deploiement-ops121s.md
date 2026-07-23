# Runbook — Déploiement ChirpStack + haccp-edge-agent sur OPS121S

> À exécuter **ensemble, en session live**, pas en autonome — touche la vraie machine de démo (192.168.1.101) et l'interface web ChirpStack. Prérequis : `infra/ops121s/docker-compose.yml` (skeleton ChirpStack) et `infra/ops121s/edge-agent/` (service) déjà en place sur `master` — voir `docs/superpowers/plans/2026-07-23-chirpstack-demo-integration.md` et `docs/superpowers/plans/2026-07-23-haccp-edge-agent.md`.

## 0. Ce que ce runbook ne couvre pas encore

Les fichiers `.toml` de config ChirpStack (`infra/ops121s/chirpstack/config/`, `infra/ops121s/chirpstack/gateway-bridge-config/`) sont volontairement vides à ce stade — leur contenu exact dépend de la version de ChirpStack réellement déployée. Première étape de ce runbook : les compléter depuis le quickstart officiel.

## 1. Compléter la config ChirpStack

1. Suivre le quickstart docker officiel ChirpStack v4 : https://www.chirpstack.io/docs/chirpstack/getting-started/docker.html
2. Adapter les `.toml` obtenus pour pointer vers les services déjà en place dans `infra/ops121s/docker-compose.yml` :
   - Postgres : host `postgres`, db `chirpstack`, user `chirpstack`, password = valeur de `CHIRPSTACK_POSTGRES_PASSWORD` (`infra/ops121s/.env`, générée via `openssl rand -hex 24`).
   - Redis : host `redis`.
   - Intégration MQTT : host `mosquitto` (broker déjà existant, ne pas en créer un second).
   - Plan de fréquence : EU868.
3. Copier ces fichiers dans `infra/ops121s/chirpstack/config/` et `infra/ops121s/chirpstack/gateway-bridge-config/` sur l'OPS121S (pas besoin de les committer dans ce repo — config locale à la machine, comme `bridge.env`).

## 2. Démarrer la stack ChirpStack sur l'OPS121S

```bash
ssh christian@192.168.1.101
cd /opt/docker/haccp   # ou le chemin réel du docker-compose sur l'OPS121S
docker compose up -d postgres redis chirpstack chirpstack-gateway-bridge
docker compose ps
docker compose logs chirpstack --tail 50
```

Vérifier `http://192.168.1.101:8080` accessible (login initial ChirpStack par défaut — à changer immédiatement).

## 3. Configurer ChirpStack (interface web)

1. Créer un tenant et une application (ex: `haccp-restaurant-poc`, cohérent avec `CHIRPSTACK_APPLICATION_ID`).
2. Créer un device profile EU868 avec un **codec JS custom** — réutiliser la logique déjà validée pour TTN (`docs/operations/architecture-ops121s-vnode.md` §3.1 : décodage 6 bytes `frm_payload`, battery masqué 14 bits, température signée /100, humidité /10). Le codec doit produire un objet `{temperature_1, humidity, battery_voltage}` — c'est le contenu du champ `object` que `haccp-edge-agent` lit (`parse_uplink()`).
3. Provisionner les 3 devices (`lht65-frigo-positif` a minima, `lht65-congelateur`/`lht65-stockage-sec` si les capteurs physiques sont disponibles) avec ce device profile.
4. Activer l'intégration MQTT de l'application (si pas automatique) pour confirmer le topic publié : `application/<id>/device/<dev_eui>/event/up`.
5. **Validation du codec** (distinct de la démo scriptée) : utiliser le testeur de codec intégré à ChirpStack (si disponible dans la version déployée) avec les mêmes bytes de test déjà validés côté TTN, pour confirmer que le device profile produit bien `{temperature_1, humidity, battery_voltage}` — c'est le point explicitement **non couvert** par `scripts/demo-simulate-sensor-chirpstack.py`, qui contourne cette couche.

## 4. Déployer haccp-edge-agent sur l'OPS121S

```bash
ssh christian@192.168.1.101 "mkdir -p /home/christian/haccp/edge-agent"
rsync -av infra/ops121s/edge-agent/ christian@192.168.1.101:/home/christian/haccp/edge-agent/
ssh christian@192.168.1.101
cd /home/christian/haccp/edge-agent
pip3 install -r requirements.txt   # ou venv, selon convention déjà en place pour odoo-bridge
```

Créer `/home/christian/haccp/edge-agent/edge-agent.env` (non committé, `*.env` gitignore) :
```
CHIRPSTACK_APPLICATION_ID=<id de l'application créée à l'étape 3>
```

```bash
sudo cp haccp-edge-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now haccp-edge-agent
sudo systemctl status haccp-edge-agent
journalctl -u haccp-edge-agent -f
```

## 5. Valider bout en bout

Depuis la machine de dev :
```bash
export CHIRPSTACK_APPLICATION_ID=<meme id qu'a l'etape 4>
export MQTT_HOST=192.168.1.101   # ou tunnel SSH si Mosquitto n'est pas exposé publiquement
python3 scripts/demo-simulate-sensor-chirpstack.py --device lht65-frigo-positif --value 12.0
```

Vérifier :
- `journalctl -u haccp-edge-agent -f` sur l'OPS121S — la mesure est reçue et forwardée.
- Odoo (`http://192.168.1.182:8029`) — nouveau `quality.check` (et `quality.alert` si hors tolérance).
- SMS reçu si hors tolérance.

## 6. Faire tourner en parallèle de vNode, puis décommissionner

- Laisser `haccp-edge-agent` tourner en parallèle de vNode quelques jours/démos, sans désinstaller vNode tout de suite.
- Une fois confiant : `sudo systemctl stop vnode && sudo systemctl disable vnode` (vNode reste installé, juste arrêté, au cas où).
- Mettre à jour `docs/operations/architecture-ops121s-vnode.md` pour refléter la nouvelle réalité (ChirpStack + `haccp-edge-agent` au lieu de vNode) — ce document décrit l'état réel du POC, il doit changer une fois la bascule faite, pas avant.

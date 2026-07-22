# Architecture actuelle — Serveur OPS121S (vNode)

> Ce document décrit l'état **réellement déployé** du serveur OPS121S pour le POC démo HACCP, tel que configuré à ce jour. Les autres fichiers de `docs/operations/` (`ops121s-setup.md`, `dream-machine-se-config.md`, `rak7268-setup.md`) décrivent l'**architecture cible de production** (VLANs Dream Machine SE, gateway LoRaWAN physique RAK7268, Chirpstack auto-hébergé) qui n'est pas encore déployée — voir [Écarts avec la cible production](#écarts-avec-larchitecture-cible-production) en fin de document.

## 1. Vue d'ensemble

OPS121S est le nœud "edge" du POC : il reçoit les données capteurs (via TTN pour l'instant, LoRaWAN direct plus tard), les transforme en points de contrôle qualité, et les pousse vers Odoo. C'est aussi le point d'accès MCP qui permet à Claude Code de lire les tags en direct pendant le développement.

```
TTN (cloud, eu1.cloud.thethings.network)
      │ MQTT uplink JSON (TLS 8883)
      ▼
┌─────────────────────────── OPS121S — 192.168.1.101 ───────────────────────────┐
│                                                                                 │
│  vNode Automation 1.22.3 (natif, systemd — PAS dockerisé)                      │
│   ├─ module MqttClient   : TTN → tags /HACCP/*  (parser custom JS)             │
│   ├─ module RestApiClient: tag change → POST http://127.0.0.1:5001/quality-check│
│   └─ module McpServer    : API MCP (port 4003) pour Claude Code                │
│                                                                                 │
│  haccp-odoo-bridge.service (Python, systemd, port 5001)                       │
│   └─ reçoit les POST vNode → XML-RPC → Odoo 19 EE (192.168.1.182:8029)        │
│       + alertes SMS (Twilio / Free Mobile) si mesure hors tolérance            │
│                                                                                 │
│  Stack Docker (docker compose, /opt/docker/haccp ou équivalent)               │
│   ├─ Mosquitto   (127.0.0.1:1883)  — broker MQTT local, usage secondaire      │
│   ├─ InfluxDB    (:8086)           — historisation séries temporelles         │
│   └─ Portainer   (:9443)           — administration Docker                    │
│                                                                                 │
│  Sauvegarde : restic → repo SFTP (config vNode + odoo-bridge)                 │
└─────────────────────────────────────────────────────────────────────────────┘
      │ XML-RPC (HTTPS interne LAN)
      ▼
Odoo 19 EE — 192.168.1.182:8029 (base odoo19e_dev)
   quality.check / quality.alert
```

## 2. Hôte

| Paramètre | Valeur |
|---|---|
| IP | **192.168.1.101** (LAN existant, pas encore sur le VLAN IoT dédié) |
| OS | Ubuntu 20.04 LTS Server |
| Hostname | ops121s-haccp |
| Accès | SSH, user `christian` |
| WebUI vNode | `http://192.168.1.101:8003` (login `admin`) |

Procédure d'installation OS + Docker de base : voir `docs/operations/ops121s-setup.md` (valide pour la partie Docker/Mosquitto/InfluxDB/Portainer — la section 9 "Ajouter vNode à la stack" est **obsolète**, vNode n'est pas dockerisé).

## 3. vNode Automation — installation native

Installé depuis le tarball fournisseur (Vester), **jamais dockerisé** : la licence est liée à l'adresse MAC de l'interface réseau physique de l'hôte.

```bash
sudo systemctl status vnode
sudo systemctl restart vnode   # nécessaire ~toutes les 2h en mode démo (licence)
```

Fichiers de config : `/home/christian/haccp/vnode/config/<Module>/config.n3c`
Logs : `/home/christian/haccp/vnode/log/<Module>/centralserver.<Module>.<date>.log`

### 3.1 Module MqttClient — ingestion TTN → tags

Détaillé intégralement dans `docs/operations/vnode-config.md`. Résumé :
- Connexion TLS à `eu1.cloud.thethings.network:8883`, souscription `v3/.../devices/+/up`.
- **Parser custom JS obligatoire** (le parser `mqttJson` ne fonctionne que pour du vNode-à-vNode) : script qui lit `decoded_payload` et pousse vers `$.output` un tag par mesure.
- 6 tags produits sous `/HACCP/` : `Frigo_Temperature`, `Frigo_Humidity`, `Congelateur_Temperature`, `Congelateur_Humidity`, `Stockage_Temperature`, `Stockage_Humidity`.
- Un seul device TTN réellement provisionné aujourd'hui : `lht65-frigo-positif` (les deux autres sont des placeholders, voir §6).

### 3.2 Module RestApiClient — tags → bridge Odoo

Config source : `infra/ops121s/vnode/config/RestApiClient-config.n3c`.

- Se déclenche **sur changement de valeur** d'un tag (`tagChangeTriggers`), pas en polling — donc renvoyer deux fois la même valeur ne génère aucun nouvel événement côté Odoo (piège connu, redémarrer `vnode.service` réinitialise l'état si besoin en démo).
- Un point de configuration par QCP (`Frigo_Temperature_QCP`, `Congelateur_Temperature_QCP`, `Stockage_Humidity_QCP`), chacun :
  - `POST http://127.0.0.1:5001/quality-check`
  - body JSON construit par un script custom : `{qcp_id, value, tag, quality}` — le `qcp_id` fait le lien avec le point de contrôle qualité Odoo correspondant (1=Frigo, 2=Congélateur, 3=Stockage).

### 3.3 Module McpServer — accès Claude Code

- Port HTTP 4003 sur `0.0.0.0`.
- Config créée **manuellement** (le module ne génère pas ses fichiers seul) : `config.n3c`, `access.n3c` (token), `tools.n3c`/`prompts.n3c`/`resources.n3c` (vides mais doivent exister au démarrage).
- Côté Claude Code : serveur MCP `vnode-haccp` déclaré en HTTP avec token Bearer.
- Sert uniquement au développement/debug (lecture de tags en direct) — ne fait pas partie du pipeline de données métier.

## 4. Bridge Odoo (`haccp-odoo-bridge.service`)

Service Python natif (pas docker), `infra/ops121s/odoo-bridge/bridge.py`, écoute en HTTP sur `127.0.0.1:5001` (donc uniquement accessible depuis vNode sur le même hôte).

Rôle :
1. Reçoit `POST /quality-check` de vNode RestApiClient.
2. Ignore les mesures de mauvaise qualité OPC (`quality < 64` = capteur déconnecté).
3. Authentifie en XML-RPC sur Odoo (`ODOO_URL`, `ODOO_DB`, `ODOO_LOGIN`, `ODOO_KEY` — variables d'env dans `bridge.env`, jamais commitées ni transmises en clair dans une conversation).
4. Crée un `quality.check` lié au `point_id` (= `qcp_id`), écrit `quality_state` explicitement (pass/fail — pas calculé automatiquement par ce champ).
5. Si hors tolérance, déclenche l'alerte SMS (Twilio ou Free Mobile selon variables d'env configurées).

Déployé via systemd, unit file : `infra/ops121s/odoo-bridge/haccp-odoo-bridge.service` (`WorkingDirectory=/home/christian/haccp/odoo-bridge`).

## 5. Stack Docker

`infra/ops121s/docker-compose.yml` — seuls 3 services dockerisés :

| Service | Port | Rôle |
|---|---|---|
| `haccp-mosquitto` | 127.0.0.1:1883 | Broker MQTT local (usage secondaire, pas sur le chemin critique TTN→Odoo actuel) |
| `haccp-influxdb` | 8086 | Bucket `haccp`, org `aifluence` — historisation séries temporelles |
| `haccp-portainer` | 9443 | Admin Docker |

vNode est explicitement exclu de ce compose (commentaire dans le fichier) — voir §3.

## 6. Génération de données de démo (sans capteur physique)

Aucun gateway LoRaWAN physique n'est déployé à ce jour (RAK7268 pas encore installé). Les démos utilisent `scripts/demo-simulate-sensor.py` qui appelle l'API TTN `/up/simulate` en encodant le vrai payload LHT65 (`frm_payload`, 6 bytes) plutôt que le `decoded_payload` — cela exerce le pipeline complet y compris le formatter uplink TTN, contrairement au bouton "Simulate uplink" de la console qui avait été utilisé avec un formatter TTN hardcodé (corrigé, voir mémoire `project-demo-simulate-sensor`).

Pipeline exercé de bout en bout :
```
demo-simulate-sensor.py → TTN /up/simulate → formatter uplink TTN → MQTT → vNode MqttClient
  → tag /HACCP/* → vNode RestApiClient → bridge.py → Odoo quality.check/alert → SMS
```

Seul `lht65-frigo-positif` est un device TTN réellement provisionné ; `lht65-congelateur` et `lht65-stockage-sec` sont des identifiants placeholders dans le script, pas encore enregistrés côté TTN.

## 7. Sauvegarde

Script réellement utilisé : `infra/ops121s/haccp-backup.sh` (restic, repo SFTP `192.168.1.174:/home/restic-repos/ops121s-haccp`), sauvegarde `~/haccp/vnode/config` et `~/haccp/odoo-bridge`, rétention 7 quotidiens / 4 hebdo / 3 mensuels.

> `infra/ops121s/backup/haccp-backup.cron` + `restic-init.sh` décrivent un schéma de sauvegarde plus élaboré (InfluxDB, buffer SQLite vNode, cron granulaire, cible VPS) qui fait partie de l'architecture cible production, pas encore en place tel quel.

## Écarts avec l'architecture cible production

| Aspect | Cible production (docs existants) | État réel POC actuel |
|---|---|---|
| Réseau | VLAN IoT dédié `10.10.10.x` derrière Dream Machine SE | LAN plat existant, OPS121S en `192.168.1.101` |
| Gateway LoRaWAN | RAK7268 physique, indoor | Aucun — simulation via API TTN (`demo-simulate-sensor.py`) |
| LNS | TTN (POC) → Chirpstack auto-hébergé (prod) | TTN uniquement |
| Sauvegarde | Cron granulaire multi-cible vers VPS | Script restic simple, cible `192.168.1.174` |
| vNode dans docker-compose | Section prévue (`ops121s-setup.md` §9) | Installation native systemd — la section docker-compose est obsolète |

Les fichiers `ops121s-setup.md`, `dream-machine-se-config.md` et `rak7268-setup.md` restent la référence à suivre **au moment du déploiement client réel** ; ce document-ci reflète ce qui tourne effectivement pendant les démos.

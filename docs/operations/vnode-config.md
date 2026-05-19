# vNode Automation — Configuration MQTT + Parser Custom HACCP

## Prérequis
- Stack Docker OPS121S opérationnelle (Mosquitto, InfluxDB, Portainer)
- TTN Application configurée + MQTT API Key (ttn-setup.md)
- Odoo 19 CE opérationnel + QCPs créés + API Key Odoo (odoo-qualite-qcp.md)
- IDs des 3 QCPs notés

## Architecture

vNode 1.22.3 est installé **en natif** sur OPS121S (tarball Vester), géré par systemd.  
Ne pas dockeriser — la licence est liée au MAC de l'interface physique.

```
TTN (eu1.cloud.thethings.network:8883 TLS)
  ↓ MQTT uplink JSON
vNode MqttClient (module v1.14.0)
  ↓ Parser custom JS → $.output.push()
vNode Tags (/HACCP/Frigo_Temperature, etc.)
  ↓ sourceModule: MqttClient
Bootstrap tag model
```

## 1. Accéder à l'interface vNode

```
URL WebUI : http://192.168.1.101:8003
Login : admin / (mot de passe défini à l'installation)
```

## 2. Vérifier l'état de vNode

```bash
sudo systemctl status vnode
tail -f /home/christian/haccp/vnode/log/MqttClient/centralserver.MqttClient.$(date +%Y-%m-%d).log
```

En mode démo, vNode s'arrête automatiquement toutes les 2h — `sudo systemctl restart vnode` pour relancer.

## 3. Module MqttClient — Connexion TTN

Fichier de config : `/home/christian/haccp/vnode/config/MqttClient/config.n3c`  
Backup de référence : `infra/ops121s/vnode/config/MqttClient-config.n3c` (dans ce repo)

### Connexion TTN_HACCP

| Paramètre | Valeur |
|-----------|--------|
| Name | TTN_HACCP |
| Protocol | mqtts (TLS) |
| Host | eu1.cloud.thethings.network |
| Port | 8883 |
| Username | haccp-restaurant-poc@ttn |
| Password | `<api_key TTN>` (stockée chiffrée dans config.n3c) |
| Client ID | vnode-haccp-ops121s |
| Protocol Version | MQTT 3.X (4) |

### Subscriber TTN_Uplink

| Paramètre | Valeur |
|-----------|--------|
| Topic | v3/haccp-restaurant-poc@ttn/devices/+/up |
| QoS | 1 |
| Encoding | binary |
| Serializer | json |
| **Parser** | **custom** (script JavaScript) |

## 4. Parser Custom — Point critique

Le parser `mqttJson` est réservé à la communication vNode-à-vNode.  
Pour du JSON TTN arbitraire, il faut obligatoirement le parser `custom`.

Script JavaScript du subscriber TTN_Uplink :

```javascript
var msg = $.input;
var deviceId = msg.end_device_ids && msg.end_device_ids.device_id;
var dp = msg.uplink_message && msg.uplink_message.decoded_payload;
if (!dp) { $.logger.warn('No decoded_payload for device %s', deviceId || 'unknown'); return; }
var ts = msg.received_at ? new Date(msg.received_at).getTime() : Date.now();
var q = 192; // Good quality

if (deviceId === 'lht65-frigo-positif') {
  if (dp.temperature_1 !== undefined) $.output.push({tag:'lht65_frigo_temperature', value:dp.temperature_1, quality:q, ts:ts});
  if (dp.humidity !== undefined) $.output.push({tag:'lht65_frigo_humidity', value:dp.humidity, quality:q, ts:ts});
} else if (deviceId === 'lht65-congelateur') {
  if (dp.temperature_1 !== undefined) $.output.push({tag:'lht65_congelateur_temperature', value:dp.temperature_1, quality:q, ts:ts});
  if (dp.humidity !== undefined) $.output.push({tag:'lht65_congelateur_humidity', value:dp.humidity, quality:q, ts:ts});
} else if (deviceId === 'lht65-stockage-sec') {
  if (dp.temperature_1 !== undefined) $.output.push({tag:'lht65_stockage_temperature', value:dp.temperature_1, quality:q, ts:ts});
  if (dp.humidity !== undefined) $.output.push({tag:'lht65_stockage_humidity', value:dp.humidity, quality:q, ts:ts});
}
```

**Variables disponibles dans le script :**
- `$.input` : payload JSON désérialisé reçu du broker MQTT
- `$.output` : tableau de sortie — `{tag: TAG_ADDRESS, value, quality, ts}`
- `$.topic` : topic MQTT de réception
- `$.logger` : logger vNode (`$.logger.info()`, `$.logger.warn()`, etc.)
- `quality` : 0–63 = Bad, 64–127 = Uncertain, 192–255 = Good

**TAG_ADDRESS** = valeur du champ `tagAddress` dans la config source du tag (ex: `lht65_frigo_temperature`), ou le chemin complet du tag si `tagAddress` est vide.

## 5. Tags HACCP — Configuration source

Fichier : `/home/christian/haccp/vnode/config/bootstrap/tags.n3c`

Les 6 tags sont dans le groupe `/HACCP` du modèle `result` :

| Tag path | tagAddress | Device TTN |
|----------|------------|------------|
| /HACCP/Frigo_Temperature | lht65_frigo_temperature | lht65-frigo-positif |
| /HACCP/Frigo_Humidity | lht65_frigo_humidity | lht65-frigo-positif |
| /HACCP/Congelateur_Temperature | lht65_congelateur_temperature | lht65-congelateur |
| /HACCP/Congelateur_Humidity | lht65_congelateur_humidity | lht65-congelateur |
| /HACCP/Stockage_Temperature | lht65_stockage_temperature | lht65-stockage-sec |
| /HACCP/Stockage_Humidity | lht65_stockage_humidity | lht65-stockage-sec |

Config source de chaque tag (dans `extensions.source`) :
```json
{
  "enabled": true,
  "type": "MqttClient",
  "module": "MqttClient",
  "config": {
    "subscriber": "TTN_HACCP/TTN_Uplink",
    "tagAddress": "lht65_frigo_temperature"
  }
}
```

## 6. Payload Formatter TTN — Point critique

Le codec Dragino LHT65 du Device Repository crashe sur les octets du capteur externe (`7FFFFFFF01`).  
Utiliser un formatter custom au niveau **device** (pas application) :

```javascript
function decodeUplink(input) {
  return {
    data: {
      temperature_1: 3.5,
      humidity: 62.1,
      battery_voltage: 3.1
    }
  };
}
```

⚠️ Ce formatter est **hardcodé** pour le POC (valeurs fixes). Remplacer par le décodeur LHT65 réel quand les capteurs physiques arrivent (voir `infra/ops121s/vnode/` pour le décodeur complet).

## 7. Vérifier l'ingestion en temps réel

```bash
# Tags vNode via MCP (depuis la machine de dev)
curl -s -X POST "http://192.168.1.101:4003/mcp" \
  -H "Authorization: Bearer <MCP_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}'
# Récupérer mcp-session-id puis appeler tag_describe

# TTN Simulate Uplink (pour tester sans capteur physique)
# TTN Console → End Devices → lht65-frigo-positif → Messaging → Simulate Uplink
# Format payload : FineOffset, laisser les bytes par défaut

# Mosquitto — écouter les uplinks bruts
mosquitto_sub -h eu1.cloud.thethings.network -p 8883 --cafile /etc/ssl/certs/ca-certificates.crt \
  -u "haccp-restaurant-poc@ttn" -P "<api_key>" \
  -t "v3/haccp-restaurant-poc@ttn/devices/+/up" -v
```

## 8. Note — Message "No Handlers for tags configured for this module"

Ce message apparaît dans le log MqttClient à chaque démarrage. Il est **sans conséquence** — il indique qu'aucun tag n'est configuré pour **publier** vers MQTT (direction tag → MQTT). La direction inverse (MQTT → tags) fonctionne normalement via le parser custom.

## 9. Persistance InfluxDB (à configurer)

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

## 10. Déploiement initial — Si reconfiguration nécessaire

```bash
# Restaurer la config MqttClient depuis le repo
sudo cp infra/ops121s/vnode/config/MqttClient-config.n3c \
  /home/christian/haccp/vnode/config/MqttClient/config.n3c
sudo systemctl restart vnode

# Vérifier
sudo systemctl status vnode
tail /home/christian/haccp/vnode/log/MqttClient/centralserver.MqttClient.$(date +%Y-%m-%d).log
```

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

En mode démo, vNode redémarre automatiquement toutes les 2h (comportement normal pour le POC).

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
2. quality.alert (nom : "Humidité stockage sec — {{humidity}}% > 75%")
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

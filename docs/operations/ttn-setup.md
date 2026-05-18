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

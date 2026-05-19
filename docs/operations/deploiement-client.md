# Runbook — Déploiement HACCP Client

Procédure standard pour déployer l'architecture HACCP IoT → Odoo chez un nouveau client restaurant.

**Architecture cible :**
- Edge : OPS121S (standardisé)
- LoRaWAN : compte TTN dédié par client
- Cloud : Odoo 19 EE mutualisé AIFluence (1 base par client)
- Alertes : SMS Free Mobile ou Twilio

**Durée estimée :** 4h (hors livraison hardware)

---

## 0. Prérequis

### Hardware à commander

| Composant | Référence | Qté | Usage |
|-----------|-----------|-----|-------|
| Edge device | OPS121S | 1 | vNode + bridge |
| Gateway LoRaWAN | RAK7268 | 1 | Indoor, couvre 1 bâtiment |
| Capteur température | Dragino LHT65 | 1/zone | Frigo, congélateur, stockage |
| SIM data | SIM 4G (optionnel) | 1 | Si pas de Wi-Fi fiable sur site |

> **Minimum viable** : 1 OPS121S + 1 RAK7268 + 2 LHT65 (frigo + congélateur)

### Informations à collecter auprès du client

- [ ] Nombre de zones à surveiller (frigo positif, congélateur, stockage sec…)
- [ ] Seuils réglementaires par zone (ex: frigo ≤ 4°C, congélateur ≤ -18°C)
- [ ] Numéro de téléphone du responsable HACCP (destinataire SMS)
- [ ] Réseau Wi-Fi sur site : SSID + mot de passe (pour OPS121S et RAK7268)
- [ ] Nom commercial du client (pour nommer TTN app, Odoo DB, etc.)

---

## 1. TTN — Nouveau compte client

### 1.1 Créer le compte TTN

1. Aller sur [console.cloud.thethings.network](https://console.cloud.thethings.network)
2. **Sign up** → email client ou email AIFluence dédié (`haccp-<client>@aifluencedigital.com`)
3. Cluster : **eu1** (Europe)
4. Confirmer l'email

### 1.2 Créer l'application TTN

```
Applications → + Create application
  Application ID : haccp-<nom-client>        (ex: haccp-restaurant-dupont)
  Name           : HACCP <Nom Client>
  Cluster        : eu1
```

### 1.3 Enregistrer la gateway RAK7268

```
Gateways → + Register gateway
  Gateway EUI    : (sur l'étiquette RAK7268, format 60C5A8FFFE...)
  Gateway ID     : gw-haccp-<nom-client>
  Frequency plan : Europe 863-870 MHz (SF9 for RX2)
  Location       : (adresse du restaurant)
```

**Config RAK7268 :**
```
http://<ip-rak>  → admin/admin
Network → LoRa Network
  Server Address : eu1.cloud.thethings.network
  Server Port Up : 1700
  Server Port Down: 1700
```

Vérifier : gateway apparaît "Connected" dans TTN Console dans les 2 minutes.

### 1.4 Enregistrer les capteurs LHT65

Pour chaque capteur (répéter) :

```
End Devices → + Register end device → Enter end device specifics manually
  Frequency plan    : Europe 863-870 MHz
  LoRaWAN version   : LoRaWAN Specification 1.0.3
  Regional parameters: RP001 Regional Parameters 1.0.3 revision A

  JoinEUI  : A84041000XXXXXXX   (sur l'étiquette LHT65)
  DevEUI   : A84041XXXXXXXXXX   (sur l'étiquette LHT65)
  AppKey   : XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX  (sur l'étiquette LHT65)
  End device ID : lht65-<zone>  (ex: lht65-frigo-positif)
```

### 1.5 Configurer le Payload Formatter

Dans TTN → Applications → haccp-\<client\> → **Payload formatters** → Uplink → Custom Javascript :

```javascript
function decodeUplink(input) {
  var bytes = input.bytes;
  var temp_SHT = ((bytes[2] << 8) | bytes[3]);
  if (temp_SHT > 32767) temp_SHT -= 65536;
  temp_SHT = temp_SHT / 100;

  var humi_SHT = ((bytes[4] << 8) | bytes[5]) / 10;

  var ext_sensor = bytes[6] & 0xFF;
  var ext_value = null;
  if (ext_sensor === 0x01) {
    var ds18b20 = ((bytes[7] << 8) | bytes[8]);
    if (ds18b20 > 32767) ds18b20 -= 65536;
    ext_value = ds18b20 / 100;
  }

  return {
    data: {
      TempC_SHT: temp_SHT,
      Hum_SHT: humi_SHT,
      TempC_DS18B20: ext_value
    }
  };
}
```

> Le LHT65 peut avoir une sonde externe DS18B20 (pour frigos) ou utiliser la sonde interne SHT20. Vérifier avec le client quelle sonde est branchée.

### 1.6 Récupérer les credentials TTN pour vNode

```
Applications → haccp-<client> → Integrations → MQTT
  Username  : haccp-<client>@ttn
  Password  : (générer une API Key "MQTT")
```

---

## 2. OPS121S — Installation sur site

### 2.1 Configuration réseau

Brancher l'OPS121S sur le réseau local client (ETH ou Wi-Fi).

Se connecter via SSH (IP assignée par DHCP ou fixe) :

```bash
ssh root@<ip-ops121s>
# mot de passe par défaut : admin
```

Changer le mot de passe root :
```bash
passwd root
```

Optionnel — IP fixe (recommandé en production) :
```
WebUI OPS121S : http://<ip-ops121s>
  Network → LAN → Static IP : 192.168.X.Y / 255.255.255.0
```

### 2.2 Installer vNode

```bash
# Vérifier si vNode est déjà installé
vnode --version

# Si absent :
VER=$(curl -s https://api.github.com/repos/scadaback/vNode/releases/latest | grep tag_name | cut -d'"' -f4)
curl -LO "https://github.com/scadaback/vNode/releases/download/${VER}/vNode-linux-arm64.tar.gz"
tar -xzf vNode-linux-arm64.tar.gz -C /usr/local/bin/
chmod +x /usr/local/bin/vnode
```

Créer les répertoires :
```bash
mkdir -p /home/christian/haccp/vnode/config
mkdir -p /home/christian/haccp/odoo-bridge
```

### 2.3 Installer Python 3 + bridge.py

```bash
# Python3 est inclus dans OPS121S
python3 --version

# Copier bridge.py depuis le repo
scp bridge.py root@<ip-ops121s>:/home/christian/haccp/odoo-bridge/
```

Ou cloner le repo :
```bash
opkg install git  # si nécessaire
git clone https://github.com/cmarches/odoo-haccp.git /tmp/odoo-haccp
cp /tmp/odoo-haccp/infra/ops121s/odoo-bridge/bridge.py /home/christian/haccp/odoo-bridge/
```

---

## 3. OPS121S — Configuration vNode

### 3.1 MqttClient (TTN → tags locaux)

Créer `/home/christian/haccp/vnode/config/MqttClient-config.n3c` :

```json
{
  "version": {"main": 1, "editor": 3},
  "result": ["Object", {
    "TTN_HACCP": ["Object", {
      "enabled": ["Boolean", true],
      "connection": ["Object", {
        "url": ["String", "mqtts://eu1.cloud.thethings.network:8883"],
        "clientId": ["String", "vnode-haccp-<nom-client>"],
        "username": ["String", "haccp-<nom-client>@ttn"],
        "password": ["String", "<API_KEY_TTN_MQTT>"]
      }],
      "subscriptions": ["Object", {
        "uplink": ["Object", {
          "topic": ["String", "v3/haccp-<nom-client>@ttn/devices/+/up"],
          "qos": ["Number", 0]
        }]
      }],
      "parser": ["Object", {
        "type": ["String", "custom"],
        "script": ["String", "var p=JSON.parse($.payload); var dev=p.end_device_ids.device_id; var d=p.uplink_message.decoded_payload; if(d.TempC_DS18B20!==null){$.setTag('/HACCP/'+dev+'/temperature',d.TempC_DS18B20);}else{$.setTag('/HACCP/'+dev+'/temperature',d.TempC_SHT);} $.setTag('/HACCP/'+dev+'/humidity',d.Hum_SHT);"]
      }]
    }, null, 0]
  }],
  "editor": {}
}
```

> Adapter le script parser selon les noms de tags souhaités.

### 3.2 RestApiClient (tags → Odoo bridge)

Pour chaque capteur, créer une request dans `/home/christian/haccp/vnode/config/RestApiClient-config.n3c`.

**Template par zone** (remplacer `<ZONE>`, `<TAG_PATH>`, `<QCP_ID>`) :

```json
"<ZONE>_QCP": ["Object", {
  "enabled": ["Boolean", true],
  "tagChangeTriggers": ["Object", {
    "trigger": ["Object", {
      "tag": ["String", "/HACCP/<TAG_PATH>"],
      "property": ["String", "value"],
      "initial": ["Boolean", false]
    }, null, <INDEX_TRIGGER>]
  }],
  "parameters": ["Object", {
    "temperature": ["Object", {
      "type": ["String", "single"],
      "tag": ["String", "/HACCP/<TAG_PATH>"]
    }, null, <INDEX_PARAM>]
  }],
  "method": ["String", "POST"],
  "type": "read",
  "path": ["Object", {"type": ["String", "plain"], "text": ["String", "/quality-check"]}],
  "headers": ["Object", {
    "fixedHeaders": ["Object", {"accept-encoding": ["String", "gzip"], "authorization": ["Object", {"type": ["String", "none"]}]}],
    "customHeaders": ["Object", {}]
  }],
  "body": ["Object", {
    "serialization": ["Object", {"serializer": ["String", "json"], "encoding": ["String", "utf8"]}],
    "parsing": ["Object", {
      "type": ["String", "custom"],
      "options": ["Object", {"script": ["String", "$.output = {qcp_id: <QCP_ID>, value: $.parameter.temperature.value, tag: '<ZONE>', quality: $.parameter.temperature.quality};"]}]
    }]
  }],
  "serialization": ["Object", {"encoding": ["String", "utf8"], "serializer": ["String", "json"]}],
  "parsing": ["Object", {
    "type": ["String", "custom"],
    "options": ["Object", {"script": ["String", "$.output = [];"]}]
  }]
}, null, <INDEX_OBJECT>]
```

**Correspondance indices** (chaque objet doit avoir des indices uniques et séquentiels) :

| Zone | INDEX_TRIGGER | INDEX_PARAM | INDEX_OBJECT |
|------|--------------|-------------|--------------|
| Zone 1 | 0 | 1 | 2 |
| Zone 2 | 3 | 4 | 5 |
| Zone 3 | 6 | 7 | 8 |

---

## 4. OPS121S — Configuration bridge.py

### 4.1 Créer bridge.env

```bash
cat > /home/christian/haccp/odoo-bridge/bridge.env <<'EOF'
# Odoo — instance mutualisée AIFluence
ODOO_URL=https://odoo.aifluencedigital.com
ODOO_DB=haccp_<nom_client>
ODOO_LOGIN=haccp-<nom_client>@aifluencedigital.com
ODOO_KEY=<API_KEY_ODOO>
BRIDGE_PORT=5001

# SMS Free Mobile (recommandé, sans coût)
FREE_MOBILE_USER=<ID_FREE_MOBILE>
FREE_MOBILE_KEY=<CLE_API_FREE>

# SMS Twilio (fallback si client n'a pas Free Mobile)
# TWILIO_ACCOUNT_SID=ACxxxxxxx
# TWILIO_AUTH_TOKEN=xxxxxxx
# TWILIO_FROM_NUMBER=+33XXXXXXXXX
# TWILIO_ALERT_NUMBER=+33XXXXXXXXX
EOF

chmod 600 /home/christian/haccp/odoo-bridge/bridge.env
```

### 4.2 Créer les services systemd

**vNode :**

```bash
cat > /etc/systemd/system/vnode.service <<'EOF'
[Unit]
Description=vNode HACCP — MqttClient TTN + RestApiClient Odoo bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/christian/haccp/vnode
ExecStart=/usr/local/bin/vnode run --config /home/christian/haccp/vnode/config
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Bridge :**

```bash
cat > /etc/systemd/system/haccp-odoo-bridge.service <<'EOF'
[Unit]
Description=HACCP Odoo Bridge — vNode RestApiClient → Odoo quality.check
After=network-online.target vnode.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/christian/haccp/odoo-bridge
EnvironmentFile=/home/christian/haccp/odoo-bridge/bridge.env
ExecStart=/usr/bin/python3 /home/christian/haccp/odoo-bridge/bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Activer et démarrer :**

```bash
systemctl daemon-reload
systemctl enable vnode haccp-odoo-bridge
systemctl start vnode haccp-odoo-bridge
systemctl status vnode haccp-odoo-bridge
```

---

## 5. Odoo — Nouvelle base client

### 5.1 Créer la base de données

Sur le serveur Odoo mutualisé AIFluence :

```bash
# Depuis le serveur Odoo
docker exec -it odoo19ee bash
createdb -U odoo haccp_<nom_client>
```

Ou via l'interface Odoo Manager : `https://odoo.aifluencedigital.com/web/database/manager`

```
Database Name : haccp_<nom_client>
Email         : haccp-<nom_client>@aifluencedigital.com
Password      : (générer un mdp fort)
Language      : Français
Country       : France
```

### 5.2 Installer le module Qualité

```
Odoo → Apps → Quality → Installer
```

### 5.3 Créer l'utilisateur HACCP bridge

```
Paramètres → Utilisateurs → Nouveau
  Nom    : HACCP Bridge <Client>
  Email  : haccp-<nom_client>@aifluencedigital.com
  Rôle   : Technicien qualité (minimum requis pour quality.check)
```

Générer une clé API :
```
Profil utilisateur → Onglet Sécurité → Clés API → Nouvelle clé
  Nom : haccp-bridge-<nom_client>
```

Copier la clé → `ODOO_KEY` dans `bridge.env`.

### 5.4 Créer les Control Points (QCPs)

```
Qualité → Configuration → Points de contrôle → Nouveau
```

Créer un QCP par zone :

| Zone | Opération | Type | Tolérance min | Tolérance max | Fréquence |
|------|-----------|------|--------------|--------------|-----------|
| Frigo positif | HACCP Température | Mesure | -30 | 4 | En continu |
| Congélateur | HACCP Température | Mesure | -40 | -15 | En continu |
| Stockage sec | HACCP Humidité | Mesure | 0 | 75 | En continu |

> **Seuils réglementaires France (référence)** :
> - Denrées réfrigérées : ≤ +4°C (viandes : ≤ +7°C)
> - Produits surgelés : ≤ -18°C
> - Légumes frais : ≤ +8°C

Noter les **ID des QCPs** créés (visibles dans l'URL) → renseigner dans `bridge.env` → `qcp_id` des RestApiClient requests.

---

## 6. Backup Restic

### 6.1 Installer Restic sur OPS121S

```bash
VER=$(curl -s https://api.github.com/repos/restic/restic/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d 'v')
curl -LO "https://github.com/restic/restic/releases/download/v${VER}/restic_${VER}_linux_arm64.bz2"
bunzip2 restic_${VER}_linux_arm64.bz2
mv restic_${VER}_linux_arm64 /usr/local/bin/restic
chmod +x /usr/local/bin/restic
```

### 6.2 Configurer le dépôt (NAS Synology client ou NAS AIFluence)

```bash
# Initialiser le dépôt Restic (première fois)
RESTIC_REPOSITORY="sftp:<user>@<ip-nas>:/home/restic-repos/haccp-<nom-client>"
RESTIC_PASSWORD="<mot-de-passe-fort>"

restic -r "$RESTIC_REPOSITORY" init
```

### 6.3 Script de backup

```bash
cp /tmp/odoo-haccp/infra/ops121s/haccp-backup.sh /home/christian/haccp/
# Éditer RESTIC_REPOSITORY et RESTIC_PASSWORD
chmod 700 /home/christian/haccp/haccp-backup.sh
```

### 6.4 Timer systemd quotidien

```bash
cat > /etc/systemd/system/haccp-backup.service <<'EOF'
[Unit]
Description=HACCP Restic Backup

[Service]
Type=oneshot
ExecStart=/home/christian/haccp/haccp-backup.sh
EOF

cat > /etc/systemd/system/haccp-backup.timer <<'EOF'
[Unit]
Description=HACCP Restic Backup quotidien 03h00

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now haccp-backup.timer
```

---

## 7. Tests de validation

### 7.1 Test pipeline complet (Simulate Uplink TTN)

```
TTN Console → Applications → haccp-<client> → End devices → lht65-<zone>
  → Messaging → Simulate uplink
  Payload (hex) : 0A 00 07 42 03 82 01 FF FF (≈ 18.58°C, 89.8% hum)
```

Vérifier dans les logs OPS121S :
```bash
journalctl -u haccp-odoo-bridge -f
# Attendu : INFO OK — lht65-frigo-positif=18.58 → check #N PASS
```

### 7.2 Test alerte FAIL

Simuler une température hors seuil :
```bash
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 6.0, "tag": "Frigo_Temperature", "quality": 192}'
```

Vérifier :
- [ ] `quality.check` FAIL créé dans Odoo
- [ ] `quality.alert` créée dans Odoo
- [ ] SMS reçu sur le téléphone du responsable

### 7.3 Test backup Restic

```bash
/home/christian/haccp/haccp-backup.sh
restic -r sftp:<user>@<ip-nas>:/home/restic-repos/haccp-<client> snapshots
```

---

## 8. Checklist de mise en production

### Hardware
- [ ] OPS121S branché et accessible SSH
- [ ] RAK7268 connectée et visible dans TTN
- [ ] Tous les LHT65 enregistrés et émettant (LED verte)
- [ ] LHT65 positionnés dans les zones (frigo, congélateur, stockage)

### TTN
- [ ] Application TTN créée
- [ ] Gateway enregistrée et "Connected"
- [ ] Tous les end devices enregistrés
- [ ] Payload formatter configuré
- [ ] Données remontant dans TTN Live data

### OPS121S
- [ ] vNode actif (`systemctl status vnode`)
- [ ] Bridge actif (`systemctl status haccp-odoo-bridge`)
- [ ] Tags locaux mis à jour à chaque uplink (vNode WebUI → Tags)
- [ ] `bridge.env` en chmod 600

### Odoo
- [ ] Base de données créée
- [ ] Module Qualité installé
- [ ] Utilisateur bridge créé avec API key
- [ ] QCPs créés avec bons seuils
- [ ] Test PASS validé dans Odoo
- [ ] Test FAIL + quality.alert validé

### Alertes
- [ ] SMS FAIL reçu par le responsable
- [ ] Numéro de téléphone correct

### Backup
- [ ] Restic initialisé
- [ ] Premier snapshot vérifié
- [ ] Timer quotidien actif

---

## 9. Informations à remettre au client

Créer un document "Accès HACCP" (à transmettre de façon sécurisée) :

```
HACCP — Accès et informations <Nom Client>
Date installation : YYYY-MM-DD
Technicien        : AIFluence Digital

OPS121S
  IP locale     : 192.168.X.Y
  SSH           : root / <mot de passe>

TTN
  Console       : https://console.cloud.thethings.network
  Compte        : <email> / <mot de passe>
  Application   : haccp-<nom-client>

Odoo
  URL           : https://odoo.aifluencedigital.com
  Base          : haccp_<nom_client>
  Login         : haccp-<nom_client>@aifluencedigital.com
  Mot de passe  : <mot de passe>

Support AIFluence Digital
  Email         : support@aifluencedigital.com
  Téléphone     : +33 X XX XX XX XX
```

---

## Annexe — Temps estimé par étape

| Étape | Durée |
|-------|-------|
| TTN (compte + app + devices) | 30 min |
| OPS121S installation + config | 45 min |
| Odoo DB + QCPs | 30 min |
| Tests bout en bout | 30 min |
| Backup Restic | 15 min |
| Remise document client | 15 min |
| **Total** | **~3h** |

> Prévoir 1h supplémentaire si c'est la première installation ou si le réseau Wi-Fi du client pose des problèmes.

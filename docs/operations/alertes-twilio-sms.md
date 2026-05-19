# Alertes HACCP — SMS Twilio + Voice

## Architecture des alertes

```
quality.check FAIL (bridge.py)
  ├── Odoo : quality.alert créée (XML-RPC)
  ├── SMS Twilio : notification immédiate responsable
  └── Voice Twilio : escalade si pas d'ACK (via webhook Flask VPS)
```

Le bridge Python (`bridge.py`) gère les alertes SMS directement — pas de dépendance externe, stdlib pure.

## 1. Compte Twilio

URL : https://console.twilio.com  
Le compte essai gratuit inclut ~15€ de crédit — suffisant pour valider le POC.

### Acheter un numéro France
Phone Numbers → Buy a Number → Country: France → Voice + SMS → ~1€/mois

### Récupérer les credentials
- **TWILIO_ACCOUNT_SID** : Dashboard (format `ACxx...`)
- **TWILIO_AUTH_TOKEN** : Dashboard Twilio
- **TWILIO_FROM_NUMBER** : numéro acheté (format `+33XXXXXXXXX`)

## 2. Configurer le bridge pour les SMS

Ajouter dans `/home/christian/haccp/odoo-bridge/bridge.env` :

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+33XXXXXXXXX_TWILIO
TWILIO_ALERT_NUMBER=+33XXXXXXXXX_RESPONSABLE
```

Redémarrer le bridge :
```bash
sudo systemctl restart haccp-odoo-bridge
sudo journalctl -u haccp-odoo-bridge -f
```

Si les variables ne sont pas définies, le SMS est silencieusement ignoré (pas d'erreur).

## 3. Tester le SMS

Simuler un FAIL depuis TTN Console (température > 4°C) ou directement :

```bash
curl -s -X POST http://127.0.0.1:5001/quality-check \
  -H "Content-Type: application/json" \
  -d '{"qcp_id": 1, "value": 6.0, "tag": "Frigo_Temperature", "quality": 192}'
```

Log attendu dans le bridge :
```
2026-05-19 18:23:33 WARNING ALERTE — Frigo_Temperature=6.0 hors seuil [-30.0–4.0] → check #N FAIL
2026-05-19 18:23:34 INFO    SMS envoyé → +33XXXXXXXXX (HTTP 201)
```

SMS reçu :
```
[HACCP ALERTE] Frigo_Temperature = 6.0 hors seuil [-30.0–4.0]
```

## 4. Escalade vocale Twilio (si pas d'ACK sous 20 min)

Le webhook Flask tourne sur le VPS (Task 4). Il génère le TwiML pour l'appel vocal.

Appel de test manuel :
```bash
curl -X POST \
  "https://api.twilio.com/2010-04-01/Accounts/<ACCOUNT_SID>/Calls.json" \
  -u "<ACCOUNT_SID>:<AUTH_TOKEN>" \
  --data-urlencode "To=+33XXXXXXXXX_RESPONSABLE" \
  --data-urlencode "From=+33XXXXXXXXX_TWILIO" \
  --data-urlencode "Url=http://<ip_vps>:5000/haccp/twiml?device=Frigo+positif&duration=20&alert_id=1"
```

Réponse vocale (Polly.Lea, fr-FR) :
```
"Alerte HACCP urgente. Frigo positif dépasse le seuil depuis 20 minutes.
Appuyez sur 1 pour confirmer votre prise en charge."
```

## 5. SMS Free Mobile (option sans coût, abonnés Free)

Espace client Free Mobile → Mon Compte → Mes options → Notifications par SMS → Activer

Test direct :
```bash
curl "https://smsapi.free-mobile.fr/sendmsg?user=<ID>&pass=<KEY>&msg=HACCP+Test+Frigo+5.5%C2%B0C"
```

Cette option ne nécessite pas de modifier `bridge.py` — utile pour des tests rapides.

## 6. SMS OVH (données 100% France, RGPD strict)

Console OVH : https://www.ovhcloud.com/fr/sms/ → créer un compte SMS, acheter des crédits.

```bash
curl -X POST "https://www.ovh.com/cgi-bin/sms/http2sms.cgi" \
  --data-urlencode "account=<COMPTE_SMS>" \
  --data-urlencode "login=<LOGIN>" \
  --data-urlencode "password=<PASSWORD>" \
  --data-urlencode "from=HACCP" \
  --data-urlencode "to=+33XXXXXXXXX" \
  --data-urlencode "message=[HACCP ALERTE] Frigo 5.5°C > seuil 4°C"
```

À intégrer dans `bridge.py` à la place de (ou en complément de) Twilio si exigence RGPD.

## 7. Variables d'environnement bridge.env complètes

```bash
# Odoo
ODOO_URL=http://192.168.1.182:8029
ODOO_DB=odoo19e_dev
ODOO_LOGIN=cmarchesseau@aifluencedigital.com
ODOO_KEY=<api_key_odoo>
BRIDGE_PORT=5001

# Twilio SMS (optionnel — désactivé si vide)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+33XXXXXXXXX
TWILIO_ALERT_NUMBER=+33XXXXXXXXX_RESPONSABLE
```

Le fichier est en `chmod 600` sur OPS121S — ne jamais committer.

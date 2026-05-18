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

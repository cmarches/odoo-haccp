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

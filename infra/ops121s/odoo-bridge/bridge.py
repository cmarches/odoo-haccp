#!/usr/bin/env python3
"""
HACCP Odoo Bridge — reçoit les tag changes de vNode RestApiClient
et crée les quality.check / quality.alert dans Odoo 19 EE via XML-RPC.

Endpoint : POST http://127.0.0.1:5001/quality-check
Body JSON : {"qcp_id": 1, "value": 3.5, "tag": "Frigo_Temperature", "quality": 192}

OPC quality codes : 0-63=Bad, 64-127=Uncertain, 192-255=Good
On ignore les mesures Bad (quality < 64) — capteur déconnecté.
"""
import json
import logging
import os
import xmlrpc.client
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("haccp-bridge")

ODOO_URL   = os.environ.get("ODOO_URL",   "http://192.168.1.182:8029")
ODOO_DB    = os.environ.get("ODOO_DB",    "odoo19e_dev")
ODOO_LOGIN = os.environ.get("ODOO_LOGIN", "cmarchesseau@aifluencedigital.com")
ODOO_KEY   = os.environ.get("ODOO_KEY",   "")
LISTEN_PORT = int(os.environ.get("BRIDGE_PORT", "5001"))

_odoo_uid = None
_odoo_models = None


def odoo_connect():
    global _odoo_uid, _odoo_models
    if _odoo_uid:
        return _odoo_uid, _odoo_models
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_LOGIN, ODOO_KEY, {})
    if not uid:
        raise RuntimeError("Odoo auth failed — check ODOO_LOGIN / ODOO_KEY")
    _odoo_models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    _odoo_uid = uid
    log.info("Odoo connected — UID %s", uid)
    return uid, _odoo_models


def create_quality_check(qcp_id: int, value: float, tag: str):
    uid, models = odoo_connect()

    check_id = models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "quality.check", "create",
        [{"point_id": qcp_id, "measure": value}],
    )
    check = models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "quality.check", "read",
        [[check_id]], {"fields": ["measure_success"]},
    )
    result = check[0]["measure_success"]

    models.execute_kw(
        ODOO_DB, uid, ODOO_KEY,
        "quality.check", "write",
        [[check_id], {"quality_state": result}],
    )

    if result == "fail":
        check_data = models.execute_kw(
            ODOO_DB, uid, ODOO_KEY,
            "quality.check", "read",
            [[check_id]], {"fields": ["tolerance_max", "tolerance_min"]},
        )
        tol_max = check_data[0]["tolerance_max"]
        tol_min = check_data[0]["tolerance_min"]
        models.execute_kw(
            ODOO_DB, uid, ODOO_KEY,
            "quality.alert", "create",
            [{"name": f"[HACCP ALERTE] {tag} hors seuil: {value} (tol [{tol_min}–{tol_max}])"}],
        )
        log.warning("ALERTE — %s=%s hors seuil [%s–%s] → check #%s FAIL",
                    tag, value, tol_min, tol_max, check_id)
    else:
        log.info("OK — %s=%s → check #%s PASS", tag, value, check_id)

    return check_id, result


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # désactiver le log HTTP brut, on utilise logging

    def do_POST(self):
        if self.path != "/quality-check":
            self._respond(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception as e:
            self._respond(400, {"error": f"invalid JSON: {e}"})
            return

        qcp_id  = body.get("qcp_id")
        value   = body.get("value")
        tag     = body.get("tag", "unknown")
        quality = body.get("quality", 192)

        if qcp_id is None or value is None:
            self._respond(400, {"error": "qcp_id and value are required"})
            return

        if quality < 64:
            log.warning("Ignoring bad-quality measurement — tag=%s quality=%s", tag, quality)
            self._respond(200, {"status": "skipped", "reason": "bad quality"})
            return

        try:
            check_id, result = create_quality_check(int(qcp_id), float(value), tag)
            self._respond(200, {"status": "ok", "check_id": check_id, "result": result})
        except Exception as e:
            log.error("Odoo error: %s", e)
            # reset connection so next call re-authenticates
            global _odoo_uid, _odoo_models
            _odoo_uid = None
            _odoo_models = None
            self._respond(500, {"error": str(e)})

    def _respond(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if not ODOO_KEY:
        raise SystemExit("ODOO_KEY environment variable is required")
    log.info("HACCP Odoo Bridge starting on 127.0.0.1:%s", LISTEN_PORT)
    server = HTTPServer(("127.0.0.1", LISTEN_PORT), BridgeHandler)
    server.serve_forever()

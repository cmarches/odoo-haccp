#!/usr/bin/env python3
"""
Test API Odoo Qualité via XML-RPC.
Usage: python3 test-odoo-api.py --url http://<vps>:8069 --db odoo --key <api_key>
"""
import argparse
import sys
import xmlrpc.client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    print(f"[1] Connexion {args.url} — DB: {args.db}")
    common = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/common")
    uid = common.authenticate(args.db, args.user, args.key, {})
    if not uid:
        print("ERREUR : authentification échouée — vérifier URL, DB, user, api_key")
        sys.exit(1)
    print(f"    OK — UID: {uid}")

    models = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/object")

    print("[2] Lecture des QCPs disponibles")
    qcps = models.execute_kw(
        args.db, uid, args.key,
        "quality.point", "search_read",
        [[]], {"fields": ["id", "name"], "limit": 10},
    )
    if not qcps:
        print("    AVERTISSEMENT : aucun QCP — créer les QCPs dans Odoo d'abord (Task 11)")
        sys.exit(0)
    for q in qcps:
        print(f"    QCP #{q['id']}: {q['name']}")
    qcp_id = qcps[0]["id"]

    print(f"[3] Création quality.check test (5.8°C, QCP #{qcp_id})")
    check_id = models.execute_kw(
        args.db, uid, args.key,
        "quality.check", "create",
        [{"point_id": qcp_id, "measure": 5.8}],
    )
    print(f"    OK — quality.check ID: {check_id}")

    print("[4] Création quality.alert test")
    alert_id = models.execute_kw(
        args.db, uid, args.key,
        "quality.alert", "create",
        [{"name": "[TEST POC] Frigo 1 — 5.8°C > seuil 4°C"}],
    )
    print(f"    OK — quality.alert ID: {alert_id}")

    print("[5] Vérification quality.check")
    check = models.execute_kw(
        args.db, uid, args.key,
        "quality.check", "read",
        [[check_id]], {"fields": ["measure", "quality_state"]},
    )
    print(f"    measure={check[0]['measure']} state={check[0]['quality_state']}")

    print("\nOK — API Odoo Qualité fonctionnelle")
    print(f"  Supprimer les enregistrements de test : check={check_id}, alert={alert_id}")


if __name__ == "__main__":
    main()

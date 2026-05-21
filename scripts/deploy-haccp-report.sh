#!/bin/bash
# scripts/deploy-haccp-report.sh
# Usage: ./scripts/deploy-haccp-report.sh [--install|--update|--test]

set -euo pipefail
cd "$(dirname "$0")/.."

SERVER="christian@192.168.1.182"
REMOTE_ADDONS="/home/christian/odoo-multiversion/v19e/addons"
LOCAL_MODULE="odoo-addons/haccp_report"
CONTAINER="odoo19e_app"
DB="odoo19e_dev"
ADDONS_PATH="/mnt/enterprise-addons,/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"
DB_HOST="db19e"
DB_USER="odoo"
DB_PASS="odoo19e_dev"
# Odoo 19 : --no-http ne fonctionne pas en dehors du sous-commande "server"
# On utilise un port alternatif (8099) pour éviter le conflit avec le serveur principal
HTTP_OPTS="--http-port=8099"

echo "==> Sync module vers serveur..."
rsync -av --delete "$LOCAL_MODULE/" "$SERVER:$REMOTE_ADDONS/haccp_report/"

MODE="${1:---update}"

if [ "$MODE" = "--install" ]; then
    echo "==> Installation du module (première fois)..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB --db_host=$DB_HOST --db_user=$DB_USER --db_password=$DB_PASS -i haccp_report --stop-after-init --addons-path='$ADDONS_PATH' $HTTP_OPTS"
elif [ "$MODE" = "--update" ]; then
    echo "==> Mise à jour du module..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB --db_host=$DB_HOST --db_user=$DB_USER --db_password=$DB_PASS -u haccp_report --stop-after-init --addons-path='$ADDONS_PATH' $HTTP_OPTS"
elif [ "$MODE" = "--test" ]; then
    echo "==> Lancement des tests..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB --db_host=$DB_HOST --db_user=$DB_USER --db_password=$DB_PASS --test-enable -u haccp_report --stop-after-init --addons-path='$ADDONS_PATH' $HTTP_OPTS"
else
    echo "ERROR: unknown mode '$MODE'. Use --install, --update, or --test." >&2
    exit 1
fi

echo "==> Done."

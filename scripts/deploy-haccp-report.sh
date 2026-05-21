#!/bin/bash
# scripts/deploy-haccp-report.sh
# Usage: ./scripts/deploy-haccp-report.sh [--install|--update|--test]

set -e

SERVER="christian@192.168.1.182"
REMOTE_ADDONS="/home/christian/odoo-multiversion/v19e/addons"
LOCAL_MODULE="odoo-addons/haccp_report"
CONTAINER="odoo19e_app"
DB="odoo19e_dev"
ADDONS_PATH="/mnt/enterprise-addons,/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"

echo "==> Sync module vers serveur..."
rsync -av --delete "$LOCAL_MODULE/" "$SERVER:$REMOTE_ADDONS/haccp_report/"

MODE="${1:---update}"

if [ "$MODE" = "--install" ]; then
    echo "==> Installation du module (première fois)..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB -i haccp_report --stop-after-init --addons-path='$ADDONS_PATH' --no-http"
elif [ "$MODE" = "--update" ]; then
    echo "==> Mise à jour du module..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB -u haccp_report --stop-after-init --addons-path='$ADDONS_PATH' --no-http"
elif [ "$MODE" = "--test" ]; then
    echo "==> Lancement des tests..."
    ssh "$SERVER" "docker exec $CONTAINER odoo -d $DB --test-enable -i haccp_report --stop-after-init --addons-path='$ADDONS_PATH' --no-http"
fi

echo "==> Done."

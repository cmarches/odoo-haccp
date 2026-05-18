#!/bin/bash
# Initialisation du repo Restic sur le VPS — à lancer une seule fois.
# Usage: RESTIC_PASSWORD=xxx VPS_HOST=backup@<ip> ./restic-init.sh
set -euo pipefail

VPS_HOST="${VPS_HOST:?Définir VPS_HOST=user@ip_vps}"
export RESTIC_PASSWORD="${RESTIC_PASSWORD:?Définir RESTIC_PASSWORD=votre_password_restic}"
RESTIC_REPO="sftp:${VPS_HOST}:/backups/ops121s"

echo "Initialisation repo Restic : ${RESTIC_REPO}"
restic -r "${RESTIC_REPO}" init

echo ""
echo "OK — Repo Restic initialisé."
echo "  Vérifier avec : restic -r ${RESTIC_REPO} snapshots"

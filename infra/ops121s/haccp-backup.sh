#!/bin/bash
set -euo pipefail

export RESTIC_REPOSITORY="sftp:christian@192.168.1.174:/home/restic-repos/ops121s-haccp"
export RESTIC_PASSWORD="haccp-backup-2026"

restic backup \
  /home/christian/haccp/vnode/config \
  /home/christian/haccp/odoo-bridge \
  --exclude "*.log" \
  --tag ops121s,haccp

# Garder 7 derniers snapshots journaliers, 4 hebdomadaires, 3 mensuels
restic forget --prune \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3

restic check --read-data-subset=5%

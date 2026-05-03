#!/usr/bin/env bash
set -euo pipefail

: "${B2_ACCOUNT_ID:?B2_ACCOUNT_ID is required}"
: "${B2_ACCOUNT_KEY:?B2_ACCOUNT_KEY is required}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD is required}"
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}"

export B2_ACCOUNT_ID
export B2_ACCOUNT_KEY
export RESTIC_PASSWORD
export RESTIC_REPOSITORY

shopt -s nullglob
BACKUP_PATHS=(
  /var/lib/docker/volumes/hermes_*
  "/etc/hermes"
)

if ! restic snapshots >/dev/null 2>&1; then
  restic init
fi

restic backup "${BACKUP_PATHS[@]}" \
  --one-file-system \
  --tag hermes3d-vps \
  --verbose

restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 12 \
  --prune

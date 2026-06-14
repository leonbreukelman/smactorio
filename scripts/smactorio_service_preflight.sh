#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/home/leonb/.config/smactorio/env"
STATE_DIR="/home/leonb/.local/state/smactorio"

if [[ ! -r "$ENV_FILE" ]]; then
  echo "SmactorIO env file is missing or unreadable: $ENV_FILE" >&2
  exit 1
fi

if ! command -v bwrap >/dev/null 2>&1; then
  echo "bubblewrap (bwrap) is required for SmactorIO worker isolation" >&2
  exit 1
fi

mkdir -p "$STATE_DIR"

if systemctl is-active --quiet maei-orchestrator.service; then
  echo "maei-orchestrator.service is still active; refusing to run SmactorIO runtime until migration cuts over" >&2
  exit 1
fi

exit 0

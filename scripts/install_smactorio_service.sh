#!/usr/bin/env bash
set -euo pipefail

SMACTORIO_HOME="${SMACTORIO_HOME:-/home/leonb/projects/smactorio}"
ENV_DIR="/home/leonb/.config/smactorio"
STATE_DIR="/home/leonb/.local/state/smactorio"
SHARE_DIR="/home/leonb/.local/share/smactorio"
HERMES_HOME="$ENV_DIR/hermes-home"
GH_CONFIG_DIR="$ENV_DIR/gh"
ENV_FILE="$ENV_DIR/env"
UNIT_SRC="$SMACTORIO_HOME/infra/systemd/system/smactorio.service"
TIMER_SRC="$SMACTORIO_HOME/infra/systemd/system/smactorio.timer"

if [[ ! -f "$UNIT_SRC" || ! -f "$TIMER_SRC" ]]; then
  echo "missing SmactorIO unit files under $SMACTORIO_HOME/infra/systemd/system" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required" >&2
  exit 1
fi

if ! command -v bwrap >/dev/null 2>&1; then
  echo "bubblewrap (bwrap) is required for worker isolation" >&2
  exit 1
fi

umask 077
mkdir -p "$ENV_DIR" "$STATE_DIR" "$SHARE_DIR" "$HERMES_HOME" "$GH_CONFIG_DIR"

if [[ ! -s "$ENV_FILE" ]]; then
  token="$(gh auth token)"
  if [[ -z "$token" ]]; then
    echo "gh auth token returned empty output" >&2
    exit 1
  fi
  {
    printf 'GITHUB_TOKEN=%q\n' "$token"
    printf 'GH_TOKEN=%q\n' "$token"
    printf 'GH_CONFIG_DIR=%q\n' "$GH_CONFIG_DIR"
    printf 'HERMES_HOME=%q\n' "$HERMES_HOME"
    printf 'SMACTORIO_WORKER_HERMES_HOME=%q\n' "$HERMES_HOME"
    printf 'SMACTORIO_SHARE_DIR=%q\n' "$SHARE_DIR"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

if ! grep -q '^GH_CONFIG_DIR=' "$ENV_FILE" 2>/dev/null; then
  printf 'GH_CONFIG_DIR=%q\n' "$GH_CONFIG_DIR" >> "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"

if [[ -f /home/leonb/.hermes/config.yaml && ! -f "$HERMES_HOME/config.yaml" ]]; then
  install -m 600 /home/leonb/.hermes/config.yaml "$HERMES_HOME/config.yaml"
fi

if [[ -f /home/leonb/.hermes/.env ]]; then
  python3 - "$HERMES_HOME/.env" <<'PY'
from pathlib import Path
import os
import re
import sys
source = Path('/home/leonb/.hermes/.env')
target = Path(sys.argv[1])
blocked = re.compile(r'^(GH_|GITHUB_|GIT_|SSH_|AWS_|CLOUDFLARE_|CF_|NPM_|HOMEBREW_|DOCKER_)')
lines = []
for line in source.read_text(encoding='utf-8').splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith('#') or '=' not in stripped:
        continue
    key = stripped.split('=', 1)[0].strip()
    if blocked.match(key.upper()):
        continue
    lines.append(line)
target.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
os.chmod(target, 0o600)
PY
fi

sudo install -m 0644 "$UNIT_SRC" /etc/systemd/system/smactorio.service
sudo install -m 0644 "$TIMER_SRC" /etc/systemd/system/smactorio.timer
sudo systemctl daemon-reload
sudo systemctl enable smactorio.timer

echo "SmactorIO units installed and timer enabled. Environment file: $ENV_FILE"
echo "Run 'sudo systemctl start smactorio.service' for a one-shot verification run, then 'sudo systemctl start smactorio.timer'."

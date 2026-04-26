#!/bin/bash
set -e

APP_ROOT="/home/site/wwwroot"
PACKAGES_PATH="$APP_ROOT/.python_packages/lib/site-packages"
LOG_FILE="/home/LogFiles/echofy-startup.log"

cd "$APP_ROOT"

mkdir -p /home/LogFiles
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] starting gunicorn on PORT=${PORT:-unset}" >> "$LOG_FILE"

exec env \
  PYTHONPATH="$APP_ROOT:$PACKAGES_PATH" \
  python3 -m gunicorn \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 600 \
  --chdir "$APP_ROOT" \
  app.main:app \
  >> "$LOG_FILE" 2>&1

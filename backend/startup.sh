#!/bin/bash
set -e

# Install ODBC Driver 18 for SQL Server on Azure App Service (Debian/Ubuntu).
# Skip if already installed to avoid 30-60s delay on every app restart.
if ! dpkg -s msodbcsql18 >/dev/null 2>&1; then
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list
    apt-get update
    ACCEPT_EULA=Y apt-get install -y msodbcsql18
fi

APP_ROOT="/home/site/wwwroot"
PACKAGES_PATH="$APP_ROOT/.python_packages/lib/site-packages"
LOG_FILE="/home/LogFiles/echofy-startup.log"

mkdir -p /home/LogFiles
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] starting gunicorn on PORT=${PORT:-unset}" >> "$LOG_FILE"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] wwwroot: $(ls $APP_ROOT 2>&1)" >> "$LOG_FILE"

export PYTHONPATH="$APP_ROOT:$PACKAGES_PATH"
cd "$APP_ROOT"

exec python3 -m gunicorn \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 600 \
  app.main:app \
  >> "$LOG_FILE" 2>&1

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

# Azure App Service sets PORT; default for local/smoke runs.
PORT="${PORT:-8000}"
# Start gunicorn
exec gunicorn --bind="0.0.0.0:${PORT}" --timeout 600 app.main:app

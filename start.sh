#!/bin/sh
# Käynnistää Discord-botin ja web-dashboardin (Linux)
# Käyttö: ./start.sh  tai  sh start.sh

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Virhe: python3 ei löydy. Asenna Python 3.8+."
    exit 1
fi

exec python3 run.py

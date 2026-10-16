#!/bin/sh
# Run as greenhouse from the deployed checkout. No sudo is required.
set -eu
cd "$(dirname "$0")/.."
/usr/bin/python3 -m pip install --user --no-cache-dir -r frontend/requirements.txt
/usr/bin/python3 -c 'import streamlit, tornado'
mkdir -p "$HOME/.config/systemd/user"
unit="$HOME/.config/systemd/user/greenhouse-frontend.service"
if [ -f "$unit" ] && [ ! -f "$unit.before-http-bridge" ]; then
    cp "$unit" "$unit.before-http-bridge"
fi
cp deploy/systemd/greenhouse-frontend.service "$unit"
systemctl --user daemon-reload
systemctl --user restart greenhouse-frontend
attempt=0
until curl -fsS http://127.0.0.1:8501/_stcore/health; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 20 ]; then
        journalctl --user -u greenhouse-frontend -n 50 --no-pager
        exit 1
    fi
    sleep 1
done
curl -fsS http://127.0.0.1:8501/ | /usr/bin/python3 -c '
import sys
assert "/_greenhouse_transport/adapter.js" in sys.stdin.read(), "Bridge adapter missing"
print("\nHTTP bridge is serving Streamlit. Refresh https://greenhouse.kentcs.org")
'

#!/bin/bash
# Shared automatic server deployment; run as greenhouse, without sudo.
set -euo pipefail
cd "$(dirname "$0")/.."
exec 9>"$HOME/.greenhouse-deploy.lock"
flock -n 9 || { echo 'Another deployment is running'; exit 1; }
[ -f .env ] || { echo 'Missing ~/app/.env (database configuration)'; exit 1; }
# Use the same interpreter as systemd and never refill the download cache.
/usr/bin/python3 -m pip install --user --no-cache-dir -r backend/requirements.txt -r frontend/requirements.txt
mkdir -p "$HOME/.config/systemd/user" "$HOME/app/proxy/run"
# Validate before restarting the services.
/usr/sbin/nginx -t -c "$HOME/app/proxy/proxy.conf"
cp deploy/systemd/*.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable greenhouse-backend greenhouse-frontend greenhouse-proxy
systemctl --user restart greenhouse-backend greenhouse-frontend greenhouse-proxy
failed() {
    systemctl --user --no-pager --full status greenhouse-backend greenhouse-frontend greenhouse-proxy || true
    journalctl --user -u greenhouse-frontend -u greenhouse-backend -u greenhouse-proxy -n 60 --no-pager || true
}
trap failed ERR
for attempt in {1..30}; do
    if curl --max-time 3 -fsS http://127.0.0.1:15125/_stcore/health >/dev/null &&
       curl --max-time 3 -fsS http://127.0.0.1:15125/api/v1/health >/dev/null; then
        curl --max-time 5 -fsS http://127.0.0.1:15125/ | /usr/bin/python3 -c '
import sys
assert "/_greenhouse_transport/adapter.js" in sys.stdin.read(), "HTTP transport adapter missing"
'
        echo 'Backend and Streamlit HTTP bridge are healthy through the app proxy.'
        exit 0
    fi
    sleep 1
done
echo 'Deployment failed its health checks.'
failed
exit 1

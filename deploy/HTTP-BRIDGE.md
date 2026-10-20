# Streamlit through the university HTTP-only proxy

The public Nginx forwards HTTP to 127.0.0.1:15125 but does not forward
WebSocket upgrades. This bridge leaves that configuration unchanged:

Browser HTTP POST/poll → public Nginx → app Nginx :15125 → bridge :8501
→ local WebSocket → real Streamlit :8502.

The bridge starts and supervises Streamlit. It proxies its pages, assets,
media, uploads and downloads, injecting a script before the frontend bundle.
That script replaces only the same-host /_stcore/stream WebSocket with
short HTTP polls and ordered sends. Binary protobuf messages travel as base64.
Cookies, Origin and Streamlit's subprotocols (including XSRF/session tokens)
are forwarded to the local handshake; Streamlit's security checks stay enabled.
HTTP transport endpoints require a custom request header, reject foreign
origins and do not enable CORS. Each browser connection gets a random bearer
token, bounded receive buffers, and a 90-second idle expiry.

## Manual deployment through GitHub (normal workflow)

Commit all deployment, frontend, proxy and workflow files and merge
into `dev`. `.github/workflows/deploy.yml` runs only when manually triggered;
pushes and pull requests do not run it. To deploy, open GitHub Actions → Test and deploy
→ Run workflow, select `dev`, and click Run workflow. Only a manual run on
`dev` can deploy, after the checks pass.

Before deploying, CI tests the backend on Python
3.9, 3.10 and 3.12, and checks deployment script and browser adapter syntax.
The deployment script validates the server's Nginx configuration before
restarting services.
Deployment runs are serialized and are not cancelled midway by a newer push.

The workflow streams an archive of the exact tested commit over SSH into
`~/app`. It does not use `git pull`, which would conflict with files copied
during the initial manual installation. Existing `.env`, `.git`, and other
server-only files are preserved; the deployment directory's Git checkout
is not updated. Do not use `git pull` in that directory to deploy separately.
Removed repository files are not automatically removed from the server.

`deploy/deploy.sh` installs dependencies using the same Python interpreter
as the user services, with pip caching disabled, validates Nginx, installs
all three user services, enables and restarts them, and checks backend and
Streamlit health through port 15125. CI then uses a real browser to verify
that https://greenhouse.kentcs.org renders through the HTTP bridge. A failed
check makes the deployment fail; it does not automatically roll code back.
The backend user service runs Flask on 127.0.0.1:5000.
The app proxy skips access logging for transport requests to reduce log
volume and avoid writing session tokens to its access log. The university's
outer proxy remains outside this repository's control.

### One-time GitHub credentials

Configure these repository Actions secrets:

- `DEPLOY_HOST`: `cassini.cs.kent.edu`
- `DEPLOY_USER`: `greenhouse`
- `DEPLOY_SSH_KEY`: a dedicated, unencrypted SSH private key whose public key
  is installed in `/home/greenhouse/.ssh/authorized_keys` on the server.

The SSH key must allow noninteractive login; a password-only SSH login does
not work for Actions. A repository GitHub deploy key or `RELEASE_SYNC_SSH_KEY`
is not automatically a server login key. The server needs `/usr/bin/python3`
with pip, `/usr/sbin/nginx`, curl, flock and the existing user systemd manager.
Its `~/app/.env` must already contain the backend database configuration.
For services to survive logout/reboot, user lingering must be enabled by
server policy (`loginctl show-user greenhouse -p Linger`). The deployment
cannot enable system-wide lingering without the appropriate server access.

No sudo, manual archive upload, or public Nginx change is required for normal
future deployments. The server still needs free disk space: disabling pip
caching prevents these installs from filling the download cache again, but
cannot prevent other accounts on the shared server from filling the disk.
SSH host keys are discovered using ssh-keyscan, matching the existing workflow;
this does not independently authenticate a previously unknown server key.

## Manual recovery only

If GitHub Actions is unavailable, copy the files into `~/app` and run:

```sh
cd ~/app
bash deploy/deploy.sh
```

`sh deploy/install-http-bridge.sh` remains a frontend-only recovery helper.
It preserves the first backup of the original frontend service and disables
pip caching. It is not the normal deployment path.

## Roll back

```sh
cp ~/.config/systemd/user/greenhouse-frontend.service.before-http-bridge ~/.config/systemd/user/greenhouse-frontend.service
systemctl --user daemon-reload
systemctl --user restart greenhouse-frontend
```

## Validation and limits

To run the public-page check locally:

```sh
python -m pip install playwright
python -m playwright install chromium
python deploy/check-public-frontend.py https://greenhouse.kentcs.org
```

This check verifies that the deployed page renders through the HTTP bridge
without native browser WebSockets. It runs automatically after deployment.

This is a custom transport, not an upstream Streamlit feature. It adds HTTP
request overhead and base64 size overhead. WebSocket messages are limited to
16 MiB, each session has a 32 MiB receive budget, and incoming HTTP bodies are
limited to 24 MiB (the outer proxies may impose smaller upload limits).
There are at most 100 transport sessions per process. Closed tabs expire
automatically. Background-tab throttling or long network outages may require
reconnection. Third-party components that open their own WebSockets are not
adapted. Root-path hosting is supported; a Streamlit baseUrlPath is not.
Widget behavior, custom components and authentication flows are not covered
by the public-page check.

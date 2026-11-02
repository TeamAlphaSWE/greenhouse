# Greenhouse Gateway

MQTT subscriber that collects Shelly sensor readings from the Mosquitto broker on the greenhouse MacBook, normalizes them, and POSTs them to the backend API. It runs on the MacBook as a systemd service, so it starts on boot and restarts if it crashes.

The MacBook runs Linux, sits closed inside a cabinet in the greenhouse, and is configured to stay on with the lid closed and to boot unattended after a power loss. All work on it is done over SSH.

## Project Structure

```text
greenhouse_gateway/
├── tests/
│   ├── conftest.py
│   ├── mock_shelly_reading.json
│   └── test_subscriber.py
├── config.py
├── subscriber.py
├── greenhouse-gateway.service
├── requirements.txt
└── README.md
```

## Connecting to the Gateway

Your computer must be on the same Wi-Fi network as the MacBook (Kent State guest Wi-Fi). Then:

```bash
ssh greenhouse@<ip-address>
```

The IP address can change when the MacBook reconnects to Wi-Fi. If SSH stops connecting, open the cabinet and the lid, and run `hostname -I` on the MacBook. Use the address that is **not** `10.42.0.1` (that one is the sensor network on the ASUS router).

To edit code with an editor instead of in the terminal, use the VS Code **Remote - SSH** extension and connect to the same address.

## Setup

One-time setup on the MacBook, from the repository root (`~/greenhouse`):

```bash
python3 -m venv .venv
.venv/bin/pip install -r greenhouse_gateway/requirements.txt
```

The service uses `.venv/bin/python` directly, so you don't need to activate the venv for it. Activate it only to run tests or run the script by hand.

## Configuration

Settings are defined in `config.py` and read from environment variables. The service loads them from `greenhouse_gateway/.env`, which is not committed:

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:5000` | Backend API base URL |
| `MQTT_HOST` | `localhost` | Broker host |
| `MQTT_PORT` | `1883` | Broker port |

On the MacBook, only `BACKEND_URL` needs setting:

```bash
echo 'BACKEND_URL=https://greenhouse.kentcs.org' > greenhouse_gateway/.env
chmod 600 greenhouse_gateway/.env
```

## Running the Gateway (systemd service)

Install (one time, from the repository root):

```bash
sudo cp greenhouse_gateway/greenhouse-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now greenhouse-gateway
```

| Task | Command |
|---|---|
| Status | `systemctl status greenhouse-gateway` |
| Live logs | `journalctl -u greenhouse-gateway -f` |
| Restart after code changes | `sudo systemctl restart greenhouse-gateway` |
| Stop | `sudo systemctl stop greenhouse-gateway` |

Changes to `subscriber.py` or `config.py` take effect only after a restart. If you edit `greenhouse-gateway.service`, copy it to `/etc/systemd/system/` again and run `daemon-reload` before restarting.

> **Only one subscriber at a time.** Both copies use the same MQTT client ID, so the broker disconnects one whenever the other connects. They keep knocking each other off, and readings can be lost. Don't run `python subscriber.py` by hand while the service is running. Stop the service first and start it again when you're done.

## Updating the Code

```bash
cd ~/greenhouse
git pull
sudo systemctl restart greenhouse-gateway
journalctl -u greenhouse-gateway -f
```

## Reading Format

The gateway listens on `+/events/rpc` and processes only `NotifyFullStatus` messages. Sensors send these every 2 hours and when the device button is pressed.

Each message is normalized to:

```json
{
  "hardware_id": "shellyhtg3-e4b3233085e8",
  "temperature": 24.4,
  "humidity": 45.9,
  "battery": 66
}
```

| Field | Source in Shelly payload | Unit |
|---|---|---|
| `hardware_id` | `src` (derived from device MAC, unique per device) | — |
| `temperature` | `params["temperature:0"]["tC"]` | °C |
| `humidity` | `params["humidity:0"]["rh"]` | % RH |
| `battery` | `params["devicepower:0"]["battery"]["percent"]` | % |

Any value missing from the payload is `null`.

Readings are POSTed to `/api/v1/sensor_data` on `BACKEND_URL`. An unknown `hardware_id` is auto-created as a pending sensor. Network and API errors are logged and skipped, so the subscriber keeps running.

## Running Tests

Tests use the sample payload in `tests/mock_shelly_reading.json` and do not require broker access. From the repository root:

```bash
.venv/bin/python -m pytest greenhouse_gateway -v
```

## Optional: Remote Development over an SSH Tunnel

> **Not needed for normal work.** This was the original development setup, before the gateway ran as a service. It runs the subscriber on your own computer against the MacBook's broker. Use it only if you need to run gateway code locally.

The service on the MacBook uses the same MQTT client ID as your local copy, so running both causes connection conflicts and lost readings. Stop the service while you develop (`sudo systemctl stop greenhouse-gateway`) and start it again when you're done.

1. Connect to the same Wi-Fi network as the MacBook.
2. On your computer, open the tunnel:

```bash
   ssh -N -L 1884:localhost:1883 greenhouse@<ip-address>
```

3. In a separate terminal, run the gateway against the tunnel:

```bash
   MQTT_PORT=1884 python subscriber.py
```
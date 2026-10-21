# Greenhouse Gateway

MQTT subscriber that collects Shelly sensor readings from the Mosquitto broker on the greenhouse MacBook and normalizes them for the backend API.

## Project Structure

```text
greenhouse_gateway/
├── tests/
│   ├── conftest.py
│   ├── mock_shelly_reading.json
│   └── test_subscriber.py
├── config.py
├── subscriber.py
├── requirements.txt
└── README.md
```

## Setup

From the repository root, create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the gateway dependencies:

```bash
pip install -r greenhouse_gateway/requirements.txt
```

## Configuration

Settings are defined in `config.py` and read from environment variables:

| Variable | Default | Description |
|---|---|---|
| `MQTT_HOST` | `localhost` | Broker host |
| `MQTT_PORT` | `1883` | Broker port |

The defaults work when running on the greenhouse MacBook. For remote development over the SSH tunnel, set `MQTT_PORT=1884`.

## Running the Gateway

From the `greenhouse_gateway` directory, on the greenhouse MacBook:

```bash
python subscriber.py
```

### Remote Development

Open an SSH tunnel that forwards local port `1884` to the broker.

> **Note:** Your computer and the greenhouse MacBook must be on the same Wi-Fi network before you start. The IP address from `hostname -I` is a local network address, so the tunnel will not connect from a different network.

1. Connect your computer to the same Wi-Fi network as the greenhouse MacBook.
2. On the greenhouse MacBook (runs Linux), find its IP address:

   ```bash
   hostname -I
   ```

3. On your computer, open the tunnel using that IP address:

   ```bash
   ssh -L 1884:localhost:1883 greenhouse@<ip-address>
   ```

4. In a separate terminal, run the gateway against the tunnel:

   ```bash
   MQTT_PORT=1884 python subscriber.py
   ```

The IP address can change when the MacBook reconnects to Wi-Fi, so check it again if the tunnel stops connecting.

## Reading Format

The gateway listens on `+/events/rpc` and processes only `NotifyFullStatus` messages, which sensors send every 2 hours.

```json
{
  "sensor_id": "shellyhtg3-e4b3233085e8",
  "sensor_name": "greenhouse-ht1",
  "ts": "2026-10-09T11:00:00+00:00",
  "temp_c": 24.4,
  "humidity": 45.9,
  "battery": 66
}
```

`sensor_id` is the stable hardware ID. `sensor_name` is a display label set in the Shelly interface. `ts` is the time the gateway received the reading (UTC).

## Running Tests

Tests use the sample payload in `tests/mock_shelly_reading.json` and do not require broker access.

From the repository root:

```bash
python -m pytest greenhouse_gateway -v
```

Or from the `greenhouse_gateway` directory:

```bash
python -m pytest -v
```

## Development

Readings are currently printed.
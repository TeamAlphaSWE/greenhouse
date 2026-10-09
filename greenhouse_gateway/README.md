# Greenhouse Gateway

MQTT subscriber that collects Shelly sensor readings from the Mosquitto broker on the greenhouse MacBook and normalizes them for the backend API.

## Project Structure

```text
greenhouse_gateway/
├── tests/
│   └── test_subscriber.py
├── mock_shelly_reading.json
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

## Running the Gateway

From the `greenhouse_gateway` directory:

```bash
python subscriber.py
```

Requires access to the broker. Port `1883` is used when running on the greenhouse MacBook. For remote development, open an SSH tunnel that forwards local port `1884` to the broker.

1. Make sure your computer and the greenhouse MacBook are on the same Wi-Fi network.
2. On the greenhouse MacBook (runs Linux), find its IP address:

   ```bash
   hostname -I
   ```

3. On your computer, open the tunnel using that IP address:

   ```bash
   ssh -L 1884:localhost:1883 greenhouse@<ip-address>
   ```

The IP address can change when the MacBook reconnects to Wi-Fi, so check it again if the tunnel stops connecting.

Leave the tunnel open in a separate terminal while the gateway runs.

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

Tests use the sample payload in `mock_shelly_reading.json` and do not require broker access.

From the `greenhouse_gateway` directory:

```bash
python -m pytest -v
```

## Development

Readings are currently printed.
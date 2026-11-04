"""Helpers for reading sensors and their history from the backend API."""
import os

import pandas as pd
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "https://greenhouse.kentcs.org").rstrip("/")
TIMEOUT_SECONDS = 10


def _get(path):
    response = requests.get(f"{BACKEND_URL}{path}", timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def get_sensors():
    return _get("/api/v1/sensors").get("sensors", [])


def get_zones():
    return _get("/api/v1/zones").get("zones", [])


def get_sensor_data(sensor_id):
    return _get(f"/api/v1/sensor_data/{sensor_id}").get("sensor_data", [])


def readings_to_frame(readings):
    """Turn sensor_data records into one row per reading, one column per value type.

    [{"timestamp": "...", "values": [{"type": "temperature", "value": 23.4}, ...]}]
    -> DataFrame with columns Date, temperature, humidity, battery (sorted by Date)
    """
    rows = []
    for reading in readings:
        row = {"Date": reading.get("timestamp")}
        for value in reading.get("values", []):
            row[value["type"]] = value["value"]
        rows.append(row)

    frame = pd.DataFrame(rows, columns=["Date", "temperature", "humidity", "battery"])
    if frame.empty:
        return frame
    frame["Date"] = pd.to_datetime(frame["Date"], utc=True)
    return frame.sort_values("Date").reset_index(drop=True)
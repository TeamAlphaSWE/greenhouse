"""Sensor health: reporting / stale / no data, battery level and last seen."""
from datetime import datetime, timezone


def sensor_health(sensor, latest, config, now=None):
    now = now or datetime.now(timezone.utc)
    interval = sensor.get("report_interval_minutes") or config["SENSOR_REPORT_INTERVAL_MINUTES"]
    stale_after = interval * config["SENSOR_STALE_FACTOR"]

    last_seen = latest["timestamp"] if latest else None
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    if last_seen is None:
        state, minutes_ago = "no_data", None
    else:
        minutes_ago = int((now - last_seen).total_seconds() // 60)
        state = "stale" if minutes_ago > stale_after else "reporting"

    battery = None
    for value in (latest or {}).get("values", []):
        if value.get("type") == "battery":
            battery = value.get("value")

    return {
        "id": sensor["id"],
        "name": sensor.get("name") or sensor.get("hardware_id"),
        "hardware_id": sensor.get("hardware_id"),
        "zone_id": sensor.get("zone_id"),
        "state": state,
        "last_seen": last_seen,
        "minutes_since_last_seen": minutes_ago,
        "battery": battery,
        "low_battery": battery is not None and battery < config["LOW_BATTERY_PERCENT"],
    }


def summarize(health):
    return {
        "total": len(health),
        "reporting": sum(h["state"] == "reporting" for h in health),
        "stale": sum(h["state"] == "stale" for h in health),
        "no_data": sum(h["state"] == "no_data" for h in health),
        "low_battery": sum(h["low_battery"] for h in health),
    }
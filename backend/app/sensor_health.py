"""Sensor health: reporting / no data, battery level and last seen."""
from datetime import datetime, timezone


def minutes_since(last_seen, now=None):
    """Minutes between last_seen and now, or None if last_seen is None."""
    if last_seen is None:
        return None
    now = now or datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return int((now - last_seen).total_seconds() // 60)


def is_stale(minutes_ago, config):
    """Shared staleness threshold: shared with area_overview.py's area_status()
    so the map and the Sensors page agree on what counts as stale."""
    stale_after = config["SENSOR_REPORT_INTERVAL_MINUTES"] * config["SENSOR_STALE_FACTOR"]
    return minutes_ago is not None and minutes_ago > stale_after


def sensor_health(sensor, latest, config, now=None):
    now = now or datetime.now(timezone.utc)

    last_seen = latest["timestamp"] if latest else None
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    minutes_ago = minutes_since(last_seen, now)
    state = "no_data" if last_seen is None else "reporting"

    battery = None
    for value in (latest or {}).get("values", []):
        if value.get("type") == "battery":
            battery = value.get("value")

    stale = is_stale(minutes_ago, config)
    low_battery = battery is not None and battery < config["LOW_BATTERY_PERCENT"]

    if stale or low_battery:
        status = "warning"
    elif last_seen is None or battery is None:
        status = "unknown"
    else:
        status = "healthy"

    return {
        "id": sensor["id"],
        "name": sensor.get("name") or sensor.get("hardware_id"),
        "hardware_id": sensor.get("hardware_id"),
        "zone_id": sensor.get("zone_id"),
        "area_id": sensor.get("area_id"),
        "state": state,
        "last_seen": last_seen,
        "minutes_since_last_seen": minutes_ago,
        "battery": battery,
        "low_battery": low_battery,
        "stale": stale,
        "status": status,
    }


def summarize(health):
    return {
        "total": len(health),
        "reporting": sum(h["state"] == "reporting" for h in health),
        "no_data": sum(h["state"] == "no_data" for h in health),
        "low_battery": sum(h["low_battery"] for h in health),
        "stale": sum(h["stale"] for h in health),
        "healthy": sum(h["status"] == "healthy" for h in health),
        "warning": sum(h["status"] == "warning" for h in health),
        "unknown": sum(h["status"] == "unknown" for h in health),
    }
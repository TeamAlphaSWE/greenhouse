"""Greenhouse data retrieval for the Ask assistant, through existing
repositories/services - no LangChain or other AI-provider concerns here, so
this stays testable on its own. assistant_tools.py wraps each of these as a
tool the model can call on demand, instead of this data being pushed into
every prompt whether it's relevant or not.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.area_overview import build_overview
from app.repositories.sensor_data import sensor_data as sensor_data_repository
from app.repositories.sensors import sensors as sensor_repository
from app.repositories.zones import zones as zone_repository
from app.sensor_health import sensor_health

RECENT_HISTORY_HOURS = 24


def current_conditions(area_name=None):
    """Current temperature/humidity vs. target for every area, or one area by name."""
    zone_list = zone_repository.find(sort=[("name", 1)])
    sensor_list = sensor_repository.find()
    assigned = [s for s in sensor_list if s.get("area_id")]
    latest = sensor_data_repository.latest_by_sensor(
        [sensor_repository._to_object_id(s["id"]) for s in sensor_list]
    )
    latest_by_area = {s["area_id"]: latest.get(s["id"]) for s in assigned}

    areas = [
        {"zone": zone.get("name"), **area}
        for zone in build_overview(zone_list, latest_by_area)
        for area in zone["areas"]
    ]
    if area_name:
        areas = [a for a in areas if (a.get("name") or "").lower() == area_name.lower()]
    return areas


def sensor_status(sensor_name=None, config=None):
    """Reporting state, battery, and last-seen time for sensors, or one by name."""
    sensor_list = sensor_repository.find(sort=[("name", 1)])
    if sensor_name:
        sensor_list = [s for s in sensor_list
                        if (s.get("name") or "").lower() == sensor_name.lower()]
    latest = sensor_data_repository.latest_by_sensor(
        [sensor_repository._to_object_id(s["id"]) for s in sensor_list]
    )
    return [sensor_health(s, latest.get(s["id"]), config) for s in sensor_list]


def sensor_history(sensor_name, hours=RECENT_HISTORY_HOURS, now=None):
    """Min/max/avg per measurement for one named sensor over a recent window.

    Returns None if no sensor has that name, or {} if it has no readings in
    the window.
    """
    sensor = sensor_repository.find_one({"name": sensor_name})
    if sensor is None:
        return None

    since = (now or datetime.now(timezone.utc)) - timedelta(hours=hours)
    by_type: dict[str, list[float]] = {}
    for reading in sensor_data_repository.find_by_sensor_id(sensor["id"]):
        timestamp = reading["timestamp"]
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if timestamp < since:
            continue
        for value in reading.get("values", []):
            by_type.setdefault(value["type"], []).append(value["value"])

    return {
        measurement: {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / len(values), 2),
        }
        for measurement, values in by_type.items()
    }

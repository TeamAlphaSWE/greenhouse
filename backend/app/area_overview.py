"""Per-area environmental status: latest temperature/humidity vs. target_conditions.

This is a different question from sensor_health.py's "is the sensor reporting" —
an area can be perfectly in range while its sensor is offline (stale last
reading) or out of range while reporting fine. Status here is purely about the
latest temperature reading against the area's configured limits.
"""
from __future__ import annotations


def area_status(area, latest):
    """One area's status: {"normal", "out_of_range", "offline_unknown"}.

    latest is the sensor's latest sensor_data reading (or None if the area has
    no sensor assigned, or that sensor has never reported).
    """
    temperature = humidity = None
    if latest:
        for value in latest.get("values", []):
            if value.get("type") == "temperature":
                temperature = value.get("value")
            elif value.get("type") == "humidity":
                humidity = value.get("value")

    limits = area.get("target_conditions", {}).get("temperature", {})
    low, high = limits.get("min"), limits.get("max")

    if temperature is None or low is None or high is None:
        state = "offline_unknown"
    elif temperature < low or temperature > high:
        state = "out_of_range"
    else:
        state = "normal"

    return {
        "id": area["id"],
        "name": area.get("name"),
        "temperature": temperature,
        "humidity": humidity,
        "state": state,
        "temperature_min": low,
        "temperature_max": high,
    }


def build_overview(zones, latest_by_area):
    """zones: GET /api/v1/zones shape. latest_by_area: {area_id: latest reading}."""
    return [
        {
            "id": zone["id"],
            "name": zone.get("name"),
            "areas": [
                area_status(area, latest_by_area.get(area["id"]))
                for area in zone.get("areas", [])
            ],
        }
        for zone in zones
    ]


def summarize(overview):
    all_areas = [area for zone in overview for area in zone["areas"]]
    return {
        "total": len(all_areas),
        "normal": sum(a["state"] == "normal" for a in all_areas),
        "out_of_range": sum(a["state"] == "out_of_range" for a in all_areas),
        "offline_unknown": sum(a["state"] == "offline_unknown" for a in all_areas),
    }

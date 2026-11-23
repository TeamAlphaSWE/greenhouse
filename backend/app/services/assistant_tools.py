"""LangChain tool wrappers around assistant_context.py's pure data functions.

The only place this feature's retrieval logic meets LangChain: each tool's
docstring is what the model sees as the tool's description, so the model
decides on its own whether and when to call each one.
"""
import json

from flask import current_app
from langchain_core.tools import tool

from app.services import assistant_context as context


@tool
def get_current_conditions(area_name: str = "") -> str:
    """Get the current temperature, humidity, and status for greenhouse areas.

    Pass area_name to look up one area (e.g. "Tomatoes"), or leave it empty
    to get every area's current conditions.
    """
    areas = context.current_conditions(area_name or None)
    if not areas:
        return f"No area found matching '{area_name}'." if area_name else "No areas configured."
    return json.dumps(areas, default=str)


@tool
def get_sensor_status(sensor_name: str = "") -> str:
    """Get sensor reporting status, battery level, and last-seen time.

    Pass sensor_name to look up one sensor, or leave it empty for all sensors.
    """
    sensors = context.sensor_status(sensor_name or None, current_app.config)
    if not sensors:
        return f"No sensor found matching '{sensor_name}'." if sensor_name else "No sensors found."
    return json.dumps(sensors, default=str)


@tool
def get_sensor_history(sensor_name: str, hours: int = 24) -> str:
    """Get min/max/average temperature and humidity for one named sensor
    over a recent time window (default 24 hours).
    """
    stats = context.sensor_history(sensor_name, hours)
    if stats is None:
        return f"No sensor named '{sensor_name}' found."
    if not stats:
        return f"'{sensor_name}' has no readings in the last {hours} hours."
    return json.dumps(stats, default=str)


ASSISTANT_TOOLS = [get_current_conditions, get_sensor_status, get_sensor_history]

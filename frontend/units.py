"""Temperature and timestamp display helpers.

The backend always stores Celsius and UTC. These only convert values for
display, using the unit picked on the Settings page and the viewer's browser
timezone.
"""
from zoneinfo import ZoneInfo

import streamlit as st

CELSIUS = "°C"
FAHRENHEIT = "°F"


def c_to_f(celsius):
    return celsius * 9 / 5 + 32


def to_display(celsius, unit):
    """Convert a Celsius value (number or pandas Series) to the chosen unit. None stays None."""
    if celsius is None:
        return None
    return c_to_f(celsius) if unit == FAHRENHEIT else celsius


def temperature_unit():
    """The user's preferred unit for this session, Celsius by default."""
    return st.session_state.get("temperature_unit", CELSIUS)


def fmt(value, decimals=1):
    """Format a number to at most `decimals` places, dropping a trailing zero (20.0 -> "20")."""
    text = f"{value:.{decimals}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def viewer_timezone():
    """IANA zone name of the browser viewing this session, UTC if unavailable."""
    return st.context.timezone or "UTC"


def to_local(dt):
    """Convert a UTC-aware datetime (or pandas Timestamp) to the viewer's local timezone. None stays None."""
    return None if dt is None else dt.astimezone(ZoneInfo(viewer_timezone()))

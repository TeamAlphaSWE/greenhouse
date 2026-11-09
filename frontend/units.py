"""Temperature unit helpers.

The backend always stores Celsius. These only convert values for display,
using the unit picked on the Settings page.
"""
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

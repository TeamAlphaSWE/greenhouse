import pandas as pd
import requests
import streamlit as st

from sensor_api import get_sensor_data, get_sensors, get_zones, readings_to_frame

st.title("Dashboard")


def show(value, unit):
    return "—" if value is None or pd.isna(value) else f"{value:g}{unit}"


try:
    sensors = get_sensors()
    zone_names = {zone["id"]: zone["name"] for zone in get_zones()}
except requests.RequestException:
    st.error("Could not reach the backend. Try again in a moment.")
    st.stop()

if not sensors:
    st.info("No sensors available yet.")
    st.stop()

sensor_names = {s["id"]: s.get("name") or s["hardware_id"] for s in sensors}
sensor_id = st.selectbox(
    "Sensor",
    options=list(sensor_names),
    format_func=lambda sid: sensor_names[sid],
)
sensor = next(s for s in sensors if s["id"] == sensor_id)

try:
    data = readings_to_frame(get_sensor_data(sensor_id))
except requests.RequestException:
    st.error("Could not load this sensor's data.")
    st.stop()

# -------------------- Sensor details --------------------

st.subheader("Sensor details")
latest = data.iloc[-1] if not data.empty else None

col1, col2, col3 = st.columns(3)
col1.metric("Temperature", show(None if latest is None else latest["temperature"], " °C"))
col2.metric("Humidity", show(None if latest is None else latest["humidity"], " %"))
col3.metric("Battery", show(None if latest is None else latest["battery"], " %"))

last_seen = "never" if latest is None else latest["Date"].strftime("%Y-%m-%d %H:%M UTC")
st.write(f"**Zone:** {zone_names.get(sensor.get('zone_id'), 'Unassigned')}")
st.write(f"**Status:** {sensor.get('status', 'unknown')}")
st.write(f"**Hardware ID:** {sensor.get('hardware_id', '—')}")
st.write(f"**Last reading:** {last_seen}")

# -------------------- Charts --------------------

if data.empty:
    st.info("This sensor has not sent any readings yet.")
    st.stop()

first_day, last_day = data["Date"].min().date(), data["Date"].max().date()
date_range = st.date_input(
    "Date range",
    value=(first_day, last_day),
    min_value=first_day,
    max_value=last_day,
)
if len(date_range) == 2:
    start, end = date_range
    data = data[(data["Date"].dt.date >= start) & (data["Date"].dt.date <= end)]

st.subheader("Temperature (°C)")
st.line_chart(data, x="Date", y="temperature")

st.subheader("Humidity (%)")
st.line_chart(data, x="Date", y="humidity")

st.subheader("Battery (%)")
st.line_chart(data, x="Date", y="battery")
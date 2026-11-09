import pandas as pd
import requests
import streamlit as st
from charts import time_series_chart
from sensor_api import (
    activate_sensor,
    get_latest_sensor_data,
    get_sensor_data,
    get_sensors,
    get_zones,
    readings_to_frame,
)
from units import temperature_unit, to_display

st.title("Sensors")

unit = temperature_unit()


def show(value, unit):
    return "—" if value is None or pd.isna(value) else f"{value:g}{unit}"


def show_limit(celsius):
    return "—" if celsius is None else f"{to_display(celsius, unit):g}"


def show_activation_form(sensor_id, sensors):
    if st.button("← Back to sensors"):
        st.session_state.pop("activating_sensor_id", None)
        st.rerun()

    sensor = next((s for s in sensors if s["id"] == sensor_id), None)
    if sensor is None or sensor.get("status") != "pending":
        st.info("This sensor is no longer pending activation.")
        return

    st.write(f"**Hardware ID:** {sensor['hardware_id']}")
    discovered = pd.to_datetime(sensor.get("created_at"), errors="coerce")
    st.write(f"**Discovered:** {discovered:%Y-%m-%d %H:%M UTC}" if pd.notna(discovered) else "**Discovered:** unknown")

    try:
        latest = get_latest_sensor_data(sensor_id)
    except requests.RequestException:
        latest = None
        st.warning("Could not load this sensor's latest reading.")

    if latest:
        values = {v["type"]: v["value"] for v in latest.get("values", [])}
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", show(to_display(values.get("temperature"), unit), f" {unit}"))
        col2.metric("Humidity", f"{values['humidity']:g} %" if "humidity" in values else "—")
        col3.metric("Battery", f"{values['battery']:g} %" if "battery" in values else "—")
        reading_time = pd.to_datetime(latest.get("timestamp"), errors="coerce")
        if pd.notna(reading_time):
            st.caption(f"Reading from {reading_time:%Y-%m-%d %H:%M UTC}")
    else:
        st.caption("No readings from this sensor yet.")

    st.divider()

    try:
        zones = get_zones()
    except requests.RequestException:
        st.error("Could not load zones. Try again in a moment.")
        return

    if not zones:
        st.warning("No zones available. Create a zone before activating this sensor.")
        return

    name = st.text_input("Sensor name")

    zone_names = {zone["id"]: zone["name"] for zone in zones}
    zone_id = st.selectbox(
        "Zone", options=list(zone_names), index=None, placeholder="Select a zone",
        format_func=lambda zid: zone_names[zid],
    )
    if zone_id is None:
        return
    zone = next(z for z in zones if z["id"] == zone_id)

    areas = zone.get("areas", [])
    if not areas:
        st.warning("This zone has no areas. Choose a different zone.")
        return

    area_names = {area["id"]: area["name"] for area in areas}
    area_id = st.selectbox(
        "Area", options=list(area_names), index=None, placeholder="Select an area",
        format_func=lambda aid: area_names[aid],
    )
    if area_id is None:
        return
    area = next(a for a in areas if a["id"] == area_id)

    conditions = area.get("target_conditions", {})
    temp = conditions.get("temperature", {})
    humidity = conditions.get("humidity", {})
    st.caption(
        f"Target · Temperature: {show_limit(temp.get('min'))}–{show_limit(temp.get('max'))} {unit} · "
        f"Humidity: {humidity.get('min', '—')}–{humidity.get('max', '—')} %"
    )

    if st.button("Activate sensor", type="primary", disabled=not name.strip()):
        try:
            activate_sensor(sensor_id, name.strip(), area_id)
        except requests.RequestException:
            st.error("Could not activate this sensor. Try again.")
        else:
            st.session_state.pop("activating_sensor_id", None)
            st.rerun()


try:
    sensors = get_sensors()
except requests.RequestException:
    st.error("Could not reach the backend. Try again in a moment.")
    st.stop()

activating_sensor_id = st.session_state.get("activating_sensor_id")
if activating_sensor_id:
    st.subheader("Activate sensor")
    show_activation_form(activating_sensor_id, sensors)
    st.stop()

try:
    zone_names = {zone["id"]: zone["name"] for zone in get_zones()}
except requests.RequestException:
    st.error("Could not reach the backend. Try again in a moment.")
    st.stop()

if not sensors:
    st.info("No sensors available yet.")
    st.stop()

# -------------------- Sensors list --------------------

st.subheader("All sensors")
for s in sensors:
    row = st.columns([3, 2, 2])
    row[0].write(s.get("name") or s["hardware_id"])
    if s.get("status") == "pending":
        row[1].badge("Pending", color="orange")
        if row[2].button("Activate", key=f"activate-{s['id']}"):
            st.session_state["activating_sensor_id"] = s["id"]
            st.rerun()
    else:
        row[1].badge("Active", color="green")

st.divider()

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
col1.metric("Temperature", show(None if latest is None else to_display(latest["temperature"], unit), f" {unit}"))
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

data = data.assign(temperature=to_display(data["temperature"], unit))

st.subheader(f"Temperature ({unit})")
st.altair_chart(time_series_chart(data, ["temperature"]), use_container_width=True)
st.subheader("Humidity (%)")
st.altair_chart(time_series_chart(data, ["humidity"]), use_container_width=True)
st.subheader("Battery (%)")
st.line_chart(data, x="Date", y="battery")
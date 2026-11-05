import pandas as pd
import requests
import streamlit as st

from sensor_api import activate_sensor, get_latest_sensor_data, get_sensors, get_zones

st.title("Activate Sensor")

sensor_id = st.session_state.get("activating_sensor_id")
if not sensor_id:
    st.info("Select a sensor to activate from the Sensors list.")
    st.page_link("views/sensors.py", label="Go to Sensors")
    st.stop()

try:
    sensors = get_sensors()
except requests.RequestException:
    st.error("Could not reach the backend. Try again in a moment.")
    st.stop()

sensor = next((s for s in sensors if s["id"] == sensor_id), None)
if sensor is None or sensor.get("status") != "pending":
    st.info("This sensor is no longer pending activation.")
    st.page_link("views/sensors.py", label="Go to Sensors")
    st.stop()

# -------------------- Sensor identity --------------------

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
    col1.metric("Temperature", f"{values['temperature']:g} °C" if "temperature" in values else "—")
    col2.metric("Humidity", f"{values['humidity']:g} %" if "humidity" in values else "—")
    col3.metric("Battery", f"{values['battery']:g} %" if "battery" in values else "—")
    reading_time = pd.to_datetime(latest.get("timestamp"), errors="coerce")
    if pd.notna(reading_time):
        st.caption(f"Reading from {reading_time:%Y-%m-%d %H:%M UTC}")
else:
    st.caption("No readings from this sensor yet.")

st.divider()

# -------------------- Activation form --------------------

try:
    zones = get_zones()
except requests.RequestException:
    st.error("Could not load zones. Try again in a moment.")
    st.stop()

if not zones:
    st.warning("No zones available. Create a zone before activating this sensor.")
    st.stop()

name = st.text_input("Sensor name")

zone_names = {zone["id"]: zone["name"] for zone in zones}
zone_id = st.selectbox("Zone", options=list(zone_names), format_func=lambda zid: zone_names[zid])
zone = next(z for z in zones if z["id"] == zone_id)

areas = zone.get("areas", [])
if not areas:
    st.warning("This zone has no areas. Choose a different zone.")
    st.stop()

area_names = {area["id"]: area["name"] for area in areas}
area_id = st.selectbox("Area", options=list(area_names), format_func=lambda aid: area_names[aid])
area = next(a for a in areas if a["id"] == area_id)

conditions = area.get("target_conditions", {})
temp = conditions.get("temperature", {})
humidity = conditions.get("humidity", {})
st.caption(
    f"Target · Temperature: {temp.get('min', '—')}–{temp.get('max', '—')} °C · "
    f"Humidity: {humidity.get('min', '—')}–{humidity.get('max', '—')} %"
)

if st.button("Activate sensor", type="primary", disabled=not name.strip()):
    try:
        activate_sensor(sensor_id, name.strip(), area_id)
    except requests.RequestException:
        st.error("Could not activate this sensor. Try again.")
    else:
        st.session_state.pop("activating_sensor_id", None)
        st.switch_page("views/sensors.py")

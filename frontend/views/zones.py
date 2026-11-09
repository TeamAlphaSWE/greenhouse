import pandas as pd
import requests
import streamlit as st
from sensor_api import get_sensors, get_zones, get_sensor_data, readings_to_frame

# NOT FINISHED YET #
st.title("Zones")
st.write("------------------------------------------")
# will have all the zone information,the box in figma called as "monitoring positions"
BACKEND_URL = "https://greenhouse.kentcs.org"
@st.fragment(run_every = "10s") # refresh page once every 10 seconds
def update_dashboard():
    def show(value, unit):
        return "—" if value is None or pd.isna(value) else f"{value:g}{unit}"
    zones = get_zones()
    sensors = get_sensors()
    zone_sensor = "Unassigned" 
    if not zones:
        st.write("No zones available")
        return
    
    zone_options = {z["id"]: z.get("name") or z["status"] for z in zones}
    zone_id = st.segmented_control(
        "Choose a zone",
        options = list(zone_options),
        format_func = lambda name: zone_options[name],
        selection_mode = "single",
        default = next(iter(zone_options))
    )

    if zone_id is None:
        st.write("Please select a zone.")
        return
    zone = next(z for z in zones if z["id"] == zone_id)

    st.subheader("Zone Information")
    st.write(f"**Status:** {zone.get('status', 'Unknown')}")
    st.write(f"**Info:** {zone.get('description', 'N/A')}")
    # check to see if specific zone has assigned sensor
    for s in sensors:
        if s.get("zone_id") == zone.get("id"):
            zone_sensor = s.get("name")
            break
    st.write(f"**Assigned Sensor:** {zone_sensor}")
    # -------------------- LATEST INFO --------------------------
    st.subheader("Current Readings")
    latest = None
    # makes sure it reads proper sensor that matches assigned zone
    for s in sensors:
        if s.get("zone_id") == zone.get("id"): 
            data = readings_to_frame(get_sensor_data(s.get("id")))
            latest = data.iloc[-1] if not data.empty else None
    if latest is None:
        st.write("Data for zone unavailable.")
        return
    else:
        # create columns that tell temp and humidity that sensor is getting for specific zone
        col1, col2, col3 = st.columns(3)
        col1.metric("**Temperature:**", show(None if latest is None else latest["temperature"], " °C"))
        col2.metric("**Humidity:**", show(None if latest is None else latest["humidity"], " %"))
update_dashboard()

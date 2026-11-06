import pandas as pd
import requests
import streamlit as st
from sensor_api import get_sensors, get_zones, readings_to_frame

# NOT FINISHED YET #
st.title("Zones")
st.write("------------------------------------------")
# will have all the zone information,the box in figma called as "monitoring positions"
BACKEND_URL = "https://greenhouse.kentcs.org"
@st.fragment(run_every = "10s") # refresh page once every 10 seconds
def update_dashboard():
    zones_response = requests.get(f"{BACKEND_URL}/api/v1/zones")
    zones = zones_response.json().get("zones", [])
    sensors_response = requests.get(f"{BACKEND_URL}/api/v1/sensors")
    sensors = sensors_response.json().get("sensors", [])
    assigned = False

    if not zones:
        st.write("No zones available")
        return
    
    zone_options = {z["id"]: z.get("name") or z["status"] for z in zones}
    zone_id = st.segmented_control(
        "Choose a zone",
        options = list(zone_options.keys()),
        format_func = lambda name: zone_options[name],
        selection_mode = "single",
        default = next(iter(zone_options))
    )

    zone = next(z for z in zones if z["id"] == zone_id)
    if zone_id is None:
        st.write("Please select a zone.")
        return

    st.subheader("Zone Information")
    st.write(f"**Status:** {zone.get('status', 'Unknown')}")
    st.write(f"**Info:** {zone.get('description', 'N/A')}")
    # -------------------- CHARTS --------------------------
update_dashboard()

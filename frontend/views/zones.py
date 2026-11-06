import pandas as pd
import requests
import streamlit as st

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
    selected_id = st.segmented_control(
        "Choose a zone",
        options = list(zone_options.keys()),
        format_func = lambda name: zone_options[name],
        selection_mode = "single",
        default = next(iter(zone_options))
    )

    if selected_id is None:
        st.write("Please select a zone.")
        return
    for z in zones:
        st.write(f"**Status:** {z.get("status")}")
        st.write(f"**Info:** {z.get("description")}")
        for a in z['areas']: # this accesses array containing objects
            st.write(f"**Name:** {a.get("name")}")
        for s in sensors:
            if s.get('zone_id') is z.get("id"):
                assigned = True
                assigned_sensor = s.get('zone_id')
                break
        if assigned is False:
            st.write(f"**Assigned Sensor:** Unassigned")
        if assigned is True:
            st.write(f"**Assigned Sensor:** " + assigned_sensor)
    # -------------------- CHARTS --------------------------
    
update_dashboard()

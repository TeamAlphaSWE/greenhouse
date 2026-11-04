import pandas as pd
import requests
import streamlit as st

# WIP #
st.title("Zones")
st.write("------------------------------------------")
# will have all the zone information,the box in figma called as "monitoring positions"
BACKEND_URL = "https://greenhouse.kentcs.org"
@st.fragment(run_every = "10s") # refresh page once every 10 seconds
def update_dashboard():
    zones_response =  requests.get(f"{BACKEND_URL}/api/v1/zones")
    zones = zones_response.json().get("zones", [])

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
        st.write(f"**Zone:** {z.get("status")}")
        st.write(f"**Name:** {z.get("")}")
update_dashboard()


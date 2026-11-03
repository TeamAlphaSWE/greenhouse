import streamlit as st
import requests
import pandas as pd
import numpy as np

# WIP #
st.title("Dashboard")
st.write("------------------------------------------")
# will have all the zone information,the box in figma called as "monitoring positions"
BACKEND_URL = "https://greenhouse.kentcs.org"
@st.fragment(run_every = "10s") # refresh page once every 10 seconds
def update_dashboard():
    zones_response =  requests.get(f"{BACKEND_URL}/api/v1/zones")
    zones_response.raise_for_status() # make sure it got a response first before proceeding
    zones = zones_response.json().get("zones", [])

    if not zones:
        st.write("No zones available")
        return
    
    zone_options = {z["id"]: z.get("name") for z in zones}
    selected_id = st.segmented_control(
        "Choose a zone",
        options = list(zone_options.keys()),
        format_func = lambda name: zone_options[name],
        selection_mode = "single",
        default = next(iter(zone_options))
    )

    if selected_id is None:
        st.write("Select zone to view its data.")
        return
    response_data = requests.get(f"{BACKEND_URL}/api/v1/zones")
    response_data.raise_for_status()
    zones_data = response_data.json()
    record = zones_data.get("zones_data", [])
    chart_rows = []
update_dashboard()
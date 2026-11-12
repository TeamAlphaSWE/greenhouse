import pandas as pd
import streamlit as st
from sensor_api import get_sensors, get_zones, get_sensor_data, readings_to_frame
from datetime import datetime, time, timedelta, timezone

st.title("Report")
@st.fragment(run_every = "10s") # refresh page once every 10 seconds
def update_dashboard():
    st.subheader("test")

update_dashboard()
import pandas as pd
import streamlit as st
from sensor_api import get_sensors, get_zones, get_sensor_data, readings_to_frame
from datetime import datetime, time, timedelta, timezone

st.title("Report")
RANGES = {"24 hours": 1, "7 days": 7, "30 days": 30}
@st.fragment(run_every = "10s") # refresh page once every 10 seconds
def update_dashboard():
    st.subheader("Greenhouse Report")
    period = st.selectbox("Please select time range to report", [*RANGES, "All history", "Custom"],
        index=1, key="trend_range")
    now = datetime.now(timezone.utc)
    start = end = None
    if period in RANGES:
        start, end = now - timedelta(days=RANGES[period]), now
    elif period == "Custom":
        selected_dates = st.date_input(
            "Start and end dates (UTC)",
            value=(now.date() - timedelta(days=7), now.date()),
            key="trend_dates", format="YYYY-MM-DD")
        if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
            st.info("Select both a start date and an end date.")
            return
        first, last = selected_dates
        if first > last:
            st.error("The end date must be on or after the start date.")
            return
        start = datetime.combine(first, time.min, tzinfo=timezone.utc)
        end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=timezone.utc)
    
update_dashboard()
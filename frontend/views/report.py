import pandas as pd
import streamlit as st
from sensor_api import get_sensors, get_zones
from reports_api import print_report
from datetime import datetime, time, timedelta, timezone

#---------------NOT FINISHED-------------#
st.title("Report")
RANGES = {"24 hours": 1, "7 days": 7, "30 days": 30}
zones = get_zones()
sensors = get_sensors()

def update_dashboard():
    st.subheader("Get more detailed insight to the Greenhouse info")
    
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

    filter_options = st.selectbox(
        "Filter with Zone or Sensor?",
        options = ["Zones", "Sensors"]
    )

    zone = None
    sensor = None
    if filter_options == "Zones":
        zone_options = {"All": "All", **{z["id"]: z.get("name") or z["status"] for z in zones}}
        zone_id = st.selectbox(
            "Choose a zone or select all to see all zones.",
            options = list(zone_options),
            format_func = lambda name: zone_options[name],
        )
        zone = None if zone_id == "All" else next(z for z in zones if z["id"] == zone_id)

    else:
        sensor_options = {"All": "All", **{s["id"]: s.get("name") or s["hardware_id"] for s in sensors}}
        sensor_id = st.selectbox(
            "Choose a sensor or select all to see all sensors.",
            options = list(sensor_options),
            format_func = lambda sid: sensor_options[sid],
        )
        sensor = None if sensor_id == "All" else next(s for s in sensors if s["id"] == sensor_id)

    # ---------------------- ADD BUTTON THAT GENERATES REPORT --------------------------
    if st.button("Generate Report"):
        with st.spinner("Generating your report, please wait..."):
            try:
                report_data = print_report(start=start, end=end, zone=zone, sensor=sensor)
                st.success("Your report has been generated!")
                st.json(report_data)
            except:
                st.error("There was an issue generating your requested report...")
update_dashboard()
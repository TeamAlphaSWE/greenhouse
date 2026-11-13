from datetime import datetime

import requests
import streamlit as st

from alert_utils import describe_alert
from sensor_api import get_alerts, get_zones
from units import to_local


st.title("Greenhouse Alerts")
st.write("View temperature and humidity alerts for greenhouse zones.")

st.divider()

try:
    alerts = get_alerts()
    zones = get_zones()
except requests.RequestException:
    st.error("Could not load alerts from the backend. Try again in a moment.")
    st.stop()


st.subheader("Alert Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Alerts", len(alerts))

with col2:
    temperature_count = 0

    for alert in alerts:
        if alert["type"] == "temperature":
            temperature_count += 1

    st.metric("Temperature Alerts", temperature_count)
with col3:
    humidity_count = 0

    for alert in alerts:
        if alert["type"] == "humidity":
            humidity_count += 1

    st.metric("Humidity Alerts", humidity_count)

st.divider()


st.subheader("Recent Alerts")

if not alerts:
    st.info("No alerts yet. Every reading is inside its area's limits.")

for alert in alerts:
    text = describe_alert(alert, zones)

    with st.container(border=True):
        left, right = st.columns([3, 1])

        with left:
            st.write("**" + text["title"] + "**")
            st.write(text["message"])
            st.write(text["detail"])

            created_at = alert.get("created_at")
            if created_at:
                when = datetime.fromisoformat(created_at)
                st.caption(to_local(when).strftime("%Y-%m-%d %H:%M %Z"))

        with right:
            if text["direction"] == "above":
                # inverse turns the up arrow red, since too high is bad
                st.metric("Above limit", text["value"], text["difference"], delta_color="inverse")
            elif text["direction"] == "below":
                st.metric("Below limit", text["value"], text["difference"])
            else:
                st.metric("Value", text["value"])

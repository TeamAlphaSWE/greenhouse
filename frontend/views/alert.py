from datetime import datetime

import requests
import streamlit as st

from alert_utils import describe_alert
from sensor_api import get_alerts, get_zones
from theme import page_header
from units import to_local

st.set_page_config(
    page_title="Alerts | Greenhouse",
    page_icon="🌱",
    layout="wide"
)

page_header("Greenhouse Alerts", "View temperature and humidity alerts for greenhouse zones.")

st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #F6F7EF !important;
}
[data-testid="stMain"] * {
    color: #18372A !important;
}
[data-testid="stMain"] .gh-page-hero h1 {
    color: #fffdf4 !important;
}
[data-testid="stMain"] .gh-page-hero .gh-page-sub {
    color: #d4af37 !important;
}
.gh-page-hero {
    margin-bottom: 8px !important;
}
[data-testid="stMain"] hr {
    margin: 0.25rem 0 !important;
}
.st-key-alert_summary_section,
.st-key-recent_alerts_section {
    background: #DCE4D6;
    border: 1px solid #DCE4D6;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.st-key-recent_alerts_section {
    background: #FFFDF4;
    border: 1px solid #123D2D;
    border-radius: 12px;
}
.st-key-alert_summary_section {
    background: #FFFDF4;
    border: 1px solid #123D2D;
    border-radius: 12px;
}
[class*="st-key-recent_alert_"],
[class*="st-key-unknown_temperature_alert_"] {
    background: #FFF3CD !important;
}
[class*="st-key-recent_alert_"] [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-unknown_temperature_alert_"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFF3CD !important;
    border: 2px solid #D4AF37 !important;
}
</style>
""", unsafe_allow_html=True)

st.divider()

try:
    alerts = get_alerts()
    zones = get_zones()
except requests.RequestException:
    st.error("Could not load alerts from the backend. Try again in a moment.")
    st.stop()


with st.container(key="alert_summary_section"):
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

with st.container(key="recent_alerts_section"):
    st.subheader("Recent Alerts")

    if not alerts:
        st.info("No alerts yet. Every reading is inside its area's limits.")

    for alert_index, alert in enumerate(alerts):
        text = describe_alert(alert, zones)
        unknown_temperature = (
            alert.get("type") == "temperature"
            and text["direction"] is None
        )
        container_key = (
            f"unknown_temperature_alert_{alert_index}"
            if unknown_temperature
            else f"recent_alert_{alert_index}"
        )

        with st.container(border=True, key=container_key):
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

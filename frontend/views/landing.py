"""One sensor-history chart with shared temperature/humidity axis (issue #162)."""
from datetime import datetime, time, timedelta, timezone
import os

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "https://greenhouse.kentcs.org").rstrip("/")
RANGES = {"24 hours": 1, "7 days": 7, "30 days": 30}


def history_frame(readings, sensor_id):
    """Normalize dates to UTC and reject any explicitly mismatched sensor IDs."""
    rows = []
    for reading in readings:
        if str(reading.get("sensor_id", sensor_id)) != str(sensor_id):
            continue
        values = {v.get("type"): v.get("value") for v in reading.get("values", [])}
        rows.append({"Date": reading.get("timestamp"),"Temperature": values.get("temperature"),"Humidity": values.get("humidity")})
    frame = pd.DataFrame(rows, columns=["Date", "Temperature", "Humidity"])
    frame["Date"] = pd.to_datetime(frame["Date"], utc=True, errors="coerce", format="ISO8601")
    for column in ["Temperature", "Humidity"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (frame.dropna(subset=["Date"])
            .dropna(subset=["Temperature", "Humidity"], how="all")
            .sort_values("Date").reset_index(drop=True))


def filter_history(frame, start=None, end=None):
    """Use [start, end) so a custom end date includes its entire UTC day."""
    mask = pd.Series(True, index=frame.index)
    if start is not None:
        mask &= frame["Date"] >= start
    if end is not None:
        mask &= frame["Date"] < end
    return frame.loc[mask].copy()


st.markdown("""
<style>
.gh-dashboard-hero { background:#123d2d; color:#fffdf4; padding:28px 30px;
 border-radius:20px; margin-bottom:24px; }
.gh-dashboard-hero p { color:#c7e5aa; font-size:12px; letter-spacing:2px;
 text-transform:uppercase; margin:0 0 10px; }
.gh-dashboard-hero h1 { color:#fffdf4; font-size:clamp(28px,5vw,42px);
 margin:0; padding:0; line-height:1.2; }
.st-key-sensor_trends { border:1px solid #dce4d6; border-radius:18px; padding:20px; }
@media(max-width:540px) {
 .gh-dashboard-hero { padding:22px 18px; }
 .st-key-sensor_trends { padding:12px; }
}
</style>
<header class="gh-dashboard-hero"><p>Greenhouse Project / Dashboard</p>
<h1>A clearer view of your greenhouse.</h1></header>
""", unsafe_allow_html=True)


def api_get(path):
    response = requests.get(f"{BACKEND_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


@st.fragment(run_every="10s")
def update_dashboard():
    try:
        sensors = api_get("/api/v1/sensors").get("sensors", [])
    except (requests.RequestException, ValueError):
        st.error("Unable to load sensors. Check the backend connection and try again.")
        return
    if not sensors:
        st.info("No sensors available.")
        return
    pending_count = sum(1 for s in sensors if s.get("status") == "pending")
    if pending_count:
        noun = "sensor is" if pending_count == 1 else "sensors are"
        st.markdown("""
        <style>
        .st-key-activation_banner {
            background-color: #fff3cd;
            border: 1px solid #ffe69c;
            border-radius: 8px;
            padding: 12px 16px;
        }
        .st-key-activation_banner p {
            color: #664d03;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container(key="activation_banner"):
            message_col, action_col = st.columns(
                [4, 1], vertical_alignment="center"
            )

            with message_col:
                st.write(f"⚠️ {pending_count} {noun} pending activation.")

            with action_col:
                with st.container(horizontal=True, horizontal_alignment="right"):
                    st.page_link("views/sensors.py", label="Review")

    sensor_options = {s["id"]: s.get("name") or s.get("hardware_id") or s["id"]
                      for s in sensors}
    # Clear a removed sensor selection before creating its widget.
    if st.session_state.get("trend_sensor") not in sensor_options:
        st.session_state.pop("trend_sensor", None)
    selected_id = st.selectbox("Select a sensor", list(sensor_options),
                               format_func=sensor_options.get, key="trend_sensor")

    with st.container(key="sensor_trends"):
        st.subheader("Temperature & Humidity Over Time")
        period = st.selectbox("Time range", [*RANGES, "All history", "Custom"],
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

        try:
            readings = api_get(f"/api/v1/sensor_data/{selected_id}").get("sensor_data", [])
        except (requests.RequestException, ValueError):
            st.error("Unable to load this sensor's readings. Please try again.")
            return
        frame = history_frame(readings, selected_id)
        filtered = filter_history(frame, start, end)
        st.caption(f"Sensor: {sensor_options[selected_id]} · All times UTC · "
                   "Temperature and humidity share one Y-axis. Values use stored sensor units.")
        if start is not None:
            label_end = end - timedelta(microseconds=1) if period == "Custom" else end
            st.caption(f"Selected window: {start:%Y-%m-%d %H:%M} — {label_end:%Y-%m-%d %H:%M} UTC")
        if filtered.empty:
            st.info("No sensor data available for this range. Try All history or different dates.")
            return
        st.line_chart(filtered, x="Date", y=["Temperature", "Humidity"],
                      color=["#28734f", "#91b44c"], width="stretch", height=360)
        st.caption(f"{len(filtered):,} readings · "
                   f"{filtered['Date'].min():%Y-%m-%d %H:%M} — "
                   f"{filtered['Date'].max():%Y-%m-%d %H:%M} UTC")


update_dashboard()

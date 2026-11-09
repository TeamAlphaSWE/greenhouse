"""One sensor-history chart with shared temperature/humidity axis (issue #162)."""
from datetime import datetime, time, timedelta, timezone
import os

import pandas as pd
import requests
import streamlit as st

from charts import time_series_chart
from units import temperature_unit, to_display

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


STATUS_DISPLAY = {
    "normal": {"icon": "✓", "label": "In range", "dot": "#3fb950", "badge": "green"},
    "out_of_range": {"icon": "⚠", "label": "Alert", "dot": "#f85149", "badge": "red"},
    "offline_unknown": {"icon": "?", "label": "Offline/Unknown", "dot": "#8b949e", "badge": "gray"},
}


def area_kpis(summary):
    """(total, within range, needs attention) from an /areas/overview summary."""
    return (
        summary.get("total", 0),
        summary.get("normal", 0),
        summary.get("out_of_range", 0) + summary.get("offline_unknown", 0),
    )


def chunk(items, size):
    """Split a list into row-sized pieces for a column grid."""
    return [items[i:i + size] for i in range(0, len(items), size)]


st.markdown("""
<style>
.gh-dashboard-hero { background:#123d2d; color:#fffdf4; padding:28px 30px;
 border-radius:20px; margin-bottom:24px; }
.gh-dashboard-hero p { color:#c7e5aa; font-size:12px; letter-spacing:2px;
 text-transform:uppercase; margin:0 0 10px; }
.gh-dashboard-hero h1 { color:#fffdf4; font-size:clamp(28px,5vw,42px);
 margin:0; padding:0; line-height:1.2; }
.st-key-sensor_trends { border:1px solid #dce4d6; border-radius:18px; padding:20px; }
.st-key-area_overview_card { background:#060607; border-radius:20px; padding:26px 28px 22px;
 margin-bottom:24px; }
.st-key-area_overview_card h2, .st-key-area_overview_card h3, .st-key-area_overview_card h4,
.st-key-area_overview_card p, .st-key-area_overview_card span, .st-key-area_overview_card label {
 color:#ededed; }
.st-key-area_overview_card small { color:#8b8f94; }
.st-key-area_overview_card [data-testid="stMetric"] { text-align:center; }
.st-key-area_overview_card [data-testid="stMetricLabel"] { color:#8b8f94; justify-content:center; }
.st-key-area_overview_card hr { border-color:#242424; }
div[class*="st-key-area-tile-normal-"] { background:#04100a; border-radius:12px; padding:10px 14px 4px; }
div[class*="st-key-area-tile-out_of_range-"] { background:#1b0909; border-radius:12px; padding:10px 14px 4px; }
div[class*="st-key-area-tile-offline_unknown-"] { background:#141414; border-radius:12px; padding:10px 14px 4px; }
div[class*="st-key-area-tile-"] h4 { margin:2px 0 6px; font-size:1.4rem; }
div[class*="st-key-area-tile-"] button { background:transparent !important; border:none !important;
 box-shadow:none !important; padding:0 !important; }
div[class*="st-key-area-tile-normal-"] button p { color:#40c977; font-size:1.1rem; }
div[class*="st-key-area-tile-out_of_range-"] button p { color:#ff6764; font-size:1.1rem; }
div[class*="st-key-area-tile-offline_unknown-"] button p { color:#8b8f94; font-size:1.1rem; }
.st-key-area_detail { border:1px solid #242424; border-radius:14px; padding:16px 20px; }
@media(max-width:540px) {
 .gh-dashboard-hero { padding:22px 18px; }
 .st-key-sensor_trends { padding:12px; }
 .st-key-area_overview_card { padding:18px 16px; }
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

    unit = temperature_unit()
    area_to_sensor = {s["area_id"]: s["id"] for s in sensors if s.get("area_id")}
    try:
        overview = api_get("/api/v1/areas/overview")
    except (requests.RequestException, ValueError):
        st.error("Unable to load the area overview.")
    else:
        area_entries = [(zone, area) for zone in overview["zones"] for area in zone["areas"]]
        areas_by_id = {area["id"]: (zone, area) for zone, area in area_entries}

        with st.container(key="area_overview_card"):
            st.markdown("### Greenhouse Overview")

            total, normal, attention = area_kpis(overview["summary"])
            kpi_cols = st.columns(3)
            kpi_cols[0].metric("Areas", total)
            kpi_cols[1].metric("In range", normal)
            kpi_cols[2].metric("Attention", attention)

            header_col, legend_col = st.columns([3, 2])
            header_col.markdown("#### Area map")
            legend = "&nbsp;&nbsp;&nbsp;".join(
                f'<span style="color:{v["dot"]}">●</span> {v["label"]}'
                for v in STATUS_DISPLAY.values()
            )
            legend_col.markdown(f'<div style="text-align:right; padding-top:14px;">{legend}</div>',
                                unsafe_allow_html=True)

            if not area_entries:
                st.info("No areas configured yet.")
            for row in chunk(area_entries, 4):
                cols = st.columns(4)
                for col, (zone, area) in zip(cols, row):
                    sensor_id = area_to_sensor.get(area["id"])
                    status = STATUS_DISPLAY[area["state"]]
                    temperature = to_display(area["temperature"], unit)
                    temp_text = f"{temperature:g}{unit}" if temperature is not None else "—"
                    tile_name = f"{zone.get('name') or 'Unassigned'} - {area.get('name') or 'Unnamed'}"
                    with col:
                        with st.container(key=f"area-tile-{area['state']}-{area['id']}"):
                            st.caption(tile_name)
                            st.markdown(f"#### {temp_text}")
                            if st.button(status["icon"], key=f"area-btn-{area['id']}",
                                         help=status["label"], disabled=sensor_id is None,
                                         use_container_width=True):
                                st.session_state["selected_area_id"] = area["id"]
                                st.session_state["trend_sensor"] = sensor_id
                                st.rerun()

            if area_entries:
                st.caption("Tap an area to inspect it.")
                st.divider()

            selected_area_id = st.session_state.get("selected_area_id")
            zone, selected_area = areas_by_id.get(selected_area_id, (None, None))
            if selected_area:
                status = STATUS_DISPLAY[selected_area["state"]]
                temperature = to_display(selected_area["temperature"], unit)
                low = to_display(selected_area["temperature_min"], unit)
                high = to_display(selected_area["temperature_max"], unit)
                range_text = f"{low:g}–{high:g}{unit}" if low is not None and high is not None else "Not configured"
                with st.container(key="area_detail"):
                    title_col, badge_col = st.columns([3, 1])
                    title_col.markdown(f"**{zone.get('name') or 'Unassigned'} - {selected_area.get('name') or 'Unnamed'}**")
                    badge_col.badge(status["label"], color=status["badge"])
                    st.write(f"Current temperature: {temperature:g}{unit}" if temperature is not None else "Current temperature: —")
                    if selected_area["humidity"] is not None:
                        st.write(f"Current humidity: {selected_area['humidity']:g}%")
                    st.write(f"Required range: {range_text}")

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
        filtered["Temperature"] = to_display(filtered["Temperature"], unit)
        st.caption(f"Sensor: {sensor_options[selected_id]} · All times UTC · "
                   f"Temperature and humidity share one Y-axis. Temperature in {unit}, humidity in %.")
        if start is not None:
            label_end = end - timedelta(microseconds=1) if period == "Custom" else end
            st.caption(f"Selected window: {start:%Y-%m-%d %H:%M} — {label_end:%Y-%m-%d %H:%M} UTC")
        if filtered.empty:
            st.info("No sensor data available for this range. Try All history or different dates.")
            return
        st.altair_chart(time_series_chart(filtered, ["Temperature", "Humidity"],
                                          colors=["#28734f", "#91b44c"], height=360),
                        use_container_width=True)
        st.caption(f"{len(filtered):,} readings · "
                   f"{filtered['Date'].min():%Y-%m-%d %H:%M} — "
                   f"{filtered['Date'].max():%Y-%m-%d %H:%M} UTC")


update_dashboard()

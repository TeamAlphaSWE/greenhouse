"""One sensor-history chart with shared temperature/humidity axis (issue #162)."""
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import os

import pandas as pd
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates

from charts import time_series_chart
from units import fmt, temperature_unit, to_display

BACKEND_URL = os.environ.get("BACKEND_URL", "https://greenhouse.kentcs.org").rstrip("/")
ASSETS = Path(__file__).resolve().parent.parent / "assets"
RANGES = {"24 hours": 1, "7 days": 7, "30 days": 30}
MAP_DISPLAY_WIDTH = 760
MAP_BACKGROUND = "#f6f7ef"  # matches .st-key-area_map_panel so the canvas has no visible white box


def tint(hex_color, amount, background=MAP_BACKGROUND):
    """`hex_color` blended into the map's background at `amount` (0-1) opacity, as a flat RGB color."""
    fg = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    bg = tuple(int(background[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(round(b + (f - b) * amount) for f, b in zip(fg, bg))


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
#-------------------- KPI SUMMARY/ GREENHOUSE MAP PANEL ------------------------
STATUS_DISPLAY = {
    "normal": {"icon": "✓", "label": "In range", "dot": "#2e7d32", "badge": "green"},
    "out_of_range": {"icon": "⚠", "label": "Alert", "dot": "#d32f2f", "badge": "gray"},
    "offline_unknown": {"icon": "?", "label": "Offline/Unknown", "dot": "#808080", "badge": "gray"},
}
NO_SENSOR_DISPLAY = {"label": "No sensor", "dot": "#668675"}


def area_kpis(summary):
    """(total, within range, needs attention) from an /areas/overview summary."""
    return (
        summary.get("total", 0),
        summary.get("normal", 0),
        summary.get("out_of_range", 0) + summary.get("offline_unknown", 0),
    )


def rotate_region(region):
    """Rotate a region 90° left (CCW) so a tall floor plan lays out wide on the dashboard."""
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    return {**region, "x": y, "y": 1 - x - w, "w": h, "h": w}


def region_at(regions, x_fraction, y_fraction):
    """The first area-linked region containing a click; filler shapes never match."""
    for region in regions:
        if region.get("area_id") is None:
            continue
        if (region["x"] <= x_fraction <= region["x"] + region["w"]
                and region["y"] <= y_fraction <= region["y"] + region["h"]):
            return region
    return None


def place_label(draw, font, box, label, canvas_height, center=False):
    """Draw a region's label inside its box, or beside it with a leader line if it would
    overflow. Dropped entirely if there's no room above or below (e.g. a sliver-thin region).
    `center` places it in the middle of the box instead of pinned to the top-left corner."""
    if not label:
        return
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    text_w, text_h = right - left, bottom - top
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    if text_w + 8 <= box_w and text_h + 8 <= box_h:
        if center:
            xy = (box[0] + (box_w - text_w) / 2 - left, box[1] + (box_h - text_h) / 2 - top)
        else:
            xy = (box[0] + 4, box[1] + 4)
        draw.text(xy, label, fill="#18372a", font=font)
        return

    fits_above = box[1] - text_h - 8 >= 0
    fits_below = box[3] + text_h + 8 <= canvas_height
    if not fits_above and not fits_below:
        return

    center_x = (box[0] + box[2]) / 2
    above = fits_above
    label_y = box[1] - text_h - 6 if above else box[3] + 6
    draw.line(
        [(center_x, box[1] if above else box[3]), (center_x, label_y + text_h if above else label_y)],
        fill="#668675", width=1,
    )
    draw.text((center_x - text_w / 2, label_y), label, fill="#18372a", font=font)


def place_zone_block(draw, name_font, value_font, box, name, value_text, canvas_height):
    """Zone name plus its current reading, stacked and centered in the box. Falls back to
    just the name (with place_label's own overflow handling) if the two lines don't fit."""
    if not value_text:
        place_label(draw, name_font, box, name, canvas_height, center=True)
        return

    name_left, name_top, name_right, name_bottom = draw.textbbox((0, 0), name, font=name_font)
    name_w, name_h = name_right - name_left, name_bottom - name_top
    value_left, value_top, value_right, value_bottom = draw.textbbox((0, 0), value_text, font=value_font)
    value_w, value_h = value_right - value_left, value_bottom - value_top

    gap = 6
    block_w, block_h = max(name_w, value_w), name_h + gap + value_h
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    if block_w + 8 > box_w or block_h + 8 > box_h:
        place_label(draw, name_font, box, name, canvas_height, center=True)
        return

    block_top = box[1] + (box_h - block_h) / 2
    draw.text(
        (box[0] + (box_w - name_w) / 2 - name_left, block_top - name_top),
        name, fill="#18372a", font=name_font,
    )
    value_y = block_top + name_h + gap
    draw.text(
        (box[0] + (box_w - value_w) / 2 - value_left, value_y - value_top),
        value_text, fill="#18372a", font=value_font,
    )


def draw_map(image, regions, areas_with_sensor, areas_by_id, unit, selected_area_id):
    """Canvas sized to the source image's aspect ratio (rotated 90° left), painted to match
    the surrounding panel so it never shows as a white box, with only our generated region
    boxes drawn on it.

    Area-linked regions: muted green with no sensor assigned; otherwise colored by the
    area's status (green normal, red out_of_range, gray offline_unknown). Filler shapes
    stay thin gray. `regions` is expected to already be rotated (see rotate_region).
    """
    width, height = image.size
    display_height = round(MAP_DISPLAY_WIDTH * width / height)
    overlay = Image.new("RGB", (MAP_DISPLAY_WIDTH, display_height), MAP_BACKGROUND)
    draw = ImageDraw.Draw(overlay)
    zone_font = ImageFont.load_default(size=16)
    value_font = ImageFont.load_default(size=20)
    filler_font = ImageFont.load_default(size=14)
    for region in regions:
        box = (
            region["x"] * MAP_DISPLAY_WIDTH,
            region["y"] * display_height,
            (region["x"] + region["w"]) * MAP_DISPLAY_WIDTH,
            (region["y"] + region["h"]) * display_height,
        )
        area_id = region.get("area_id")
        if area_id is not None:
            selected = str(area_id) == str(selected_area_id)
            if area_id not in areas_with_sensor:
                color, width_px = "#668675", 2
                amount = 0.3 if selected else 0.08
                draw.rectangle(box, outline=color, fill=tint(color, amount), width=width_px)
                place_label(draw, zone_font, box, region.get("zone_name"), display_height, center=True)
            else:
                _, area = areas_by_id.get(area_id, (None, None))
                state = area["state"] if area else "offline_unknown"
                width_px = 3
                if state == "out_of_range":
                    color, amount = "#d32f2f", (0.45 if selected else 0.2)
                elif state == "offline_unknown":
                    color, amount = "#808080", (0.35 if selected else 0.12)
                else:
                    color, amount = "#2e7d32", (0.4 if selected else 0.15)
                draw.rectangle(box, outline=color, fill=tint(color, amount), width=width_px)
                temperature = to_display(area.get("temperature"), unit) if area else None
                temp_text = f"{fmt(temperature)}{unit}" if temperature is not None else None
                place_zone_block(
                    draw, zone_font, value_font, box, region.get("zone_name"), temp_text, display_height,
                )
        else:
            draw.rectangle(box, outline="#9aa79a", width=1)
            place_label(draw, filler_font, box, region.get("text"), display_height, center=False)
    return overlay, display_height
#------------------------------

st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
 background:#f6f7ef !important;
}
[data-testid="stSidebar"], [data-testid="stSidebarNav"] {
 background:#123d2d !important;
}
[data-testid="stSidebarNav"] * {
 color:#fffdf4;
}
.gh-dashboard-hero { background:#123d2d; color:#fffdf4; padding:28px 30px;
 border-radius:20px; margin-bottom:24px; }
.gh-dashboard-hero p { color:#d4af37; font-size:12px; font-weight:700; letter-spacing:2px;
 text-transform:uppercase; margin:0 0 10px; }
.gh-dashboard-hero h1 { color:#fffdf4; font-size:clamp(28px,5vw,42px);
 margin:0; padding:0; line-height:1.2; }
.st-key-sensor_trends {
 background:#fff; border:1px solid #dce4d6; border-radius:18px; padding:20px;
 color:#000;
}
.st-key-sensor_trends .st-key-trend_sensor button,
.st-key-sensor_trends .st-key-trend_sensor button *,
.st-key-sensor_trends .st-key-trend_range button,
.st-key-sensor_trends .st-key-trend_range button * {
 color:#d4af37 !important;
 -webkit-text-fill-color:#d4af37 !important;
}
.st-key-sensor_trends h1, .st-key-sensor_trends h2, .st-key-sensor_trends h3,
.st-key-sensor_trends p, .st-key-sensor_trends label,
.st-key-sensor_trends [data-testid="stCaptionContainer"] {
 color:#000 !important;
}

/* KPI Customization */
.st-key-area_overview_card { background:#fffdf4; color:#18372a; border:1px solid #dce4d6; border-radius:20px; padding:26px 28px 22px;
 margin-bottom:24px; }
.st-key-area_overview_card h2, .st-key-area_overview_card h3, .st-key-area_overview_card h4,
.st-key-area_overview_card p, .st-key-area_overview_card span, .st-key-area_overview_card label {
 color:#18372a; }
.st-key-area_overview_card small { color:#18372a; }
.st-key-area_overview_card [data-testid="stMetric"] { text-align:left; padding:0; }
.st-key-area_overview_card [data-testid="stMetricValue"] { color:#284a30; font-weight:700; }
.st-key-area_overview_card [data-testid="stMetricLabel"] { color:#526352; }
.st-key-area_kpi_in_range [data-testid="stMetricValue"],
.st-key-area_kpi_in_range [data-testid="stMetricLabel"] { color:#2e7d32; }
.area-kpi { display:flex; flex-direction:column; align-items:center; text-align:center; }
.area-kpi-value { color:#284a30; font-size:calc(2rem + 4px); font-weight:700; line-height:1.2; }
.area-kpi-label { color:#526352; font-size:.875rem; }
.area-kpi--normal .area-kpi-value, .area-kpi--normal .area-kpi-label { color:#2e7d32; }
.area-kpi--attention .area-kpi-value, .area-kpi--attention .area-kpi-label { color:#d32f2f; }
.area-map-title {
 color:#18372a; font-size:calc(1.75rem + 5px); font-weight:600;
 text-align:left; margin:0;
}
.area-map-header {
 display:flex; align-items:center; justify-content:space-between;
 gap:16px; padding-top:5px; margin-bottom:14px;
}
.area-map-legend {
 display:flex; align-items:center; justify-content:flex-end;
 gap:14px; color:#18372a; white-space:nowrap;
}
.area-map-legend-item { display:flex; align-items:center; gap:5px; }
@media(max-width:700px) {
 .area-map-header { align-items:flex-start; flex-direction:column; }
 .area-map-legend { justify-content:flex-start; flex-wrap:wrap; white-space:normal; }
}
.st-key-area_overview_card hr { border-color:#d5dfcd; }
.st-key-area_map_panel { background:#f6f7ef; border:1px solid #dce4d6; border-radius:12px;
 padding:18px 20px 14px; margin:4px 0 16px; }
.st-key-area_map_panel h4, .st-key-area_map_panel p,
.st-key-area_map_panel [data-testid="stCaptionContainer"] { color:#18372a; }
.st-key-area_map_panel [data-testid="stCaptionContainer"] { text-align:center; }
.st-key-area_detail { background:#fff; border:1px solid #dce4d6; border-radius:14px;
 min-height:110px; padding:14px 16px; margin-top:10px; }
.st-key-area_detail [data-testid="stHorizontalBlock"] { gap:.65rem; }
.st-key-area_detail [data-testid="stColumn"] [data-testid="stVerticalBlock"] { gap:.15rem; }
.st-key-area_detail [data-testid="stCaptionContainer"] {
 color:#526352; line-height:1.1; margin-bottom:2px;
 font-size:calc(1rem); font-style:normal; color:#000; }
.st-key-area_detail [data-testid="stMarkdownContainer"] p {
 color:#18372a; margin:0; line-height:1.25; font-size:calc(1rem + 10px); }
.st-key-area_detail .area-header { margin:0; }
.st-key-area_detail .area-title-row { display:flex; align-items:center; gap:10px; }
.st-key-area_detail .area-last-seen {
 color:#526352; font-size:.8rem; line-height:1.2; margin-top:3px; }
.st-key-area_detail .area-header .area-name {
 font-weight:700; font-size:1.1rem; color:#18372a; }
.st-key-area_detail .area-header .area-status {
 display:inline-flex; align-items:center; justify-content:center;
 padding:4px 10px; border-radius:8px; background:#d9f4df; color:#284a30;
 font-size:0.9rem; font-weight:600; line-height:1.2; }
.st-key-area_detail .area-value-row { margin-top:4px; }
.st-key-area_detail .area-empty-message { color:#526352; font-size:.95rem; margin:0; }]

@media(max-width:540px) {
 .gh-dashboard-hero { padding:22px 18px; }
 .st-key-sensor_trends { padding:12px; }
 .st-key-area_overview_card { padding:18px 16px; }
 .st-key-area_map_panel { padding:12px 10px 8px; }
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
    # Match the sensor trend chart's own default (sensors[0]) so the map starts in sync with it.
    st.session_state.setdefault("selected_area_id", sensors[0].get("area_id"))
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

#----------- APART OF KPI SUMMARY --------------------------------------------
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
            total, normal, attention = area_kpis(overview["summary"])
            kpi_cols = st.columns([0.75, 0.75, 0.75, 7.75], gap="small")
            with kpi_cols[0]:
                st.markdown(
                    '<div class="area-kpi">'
                    f'<div class="area-kpi-value">{total}</div>'
                    '<div class="area-kpi-label">Areas</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            with kpi_cols[1]:
                with st.container(key="area_kpi_in_range"):
                    st.markdown(
                        '<div class="area-kpi area-kpi--normal">'
                        f'<div class="area-kpi-value">{normal}</div>'
                        '<div class="area-kpi-label">In range</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            with kpi_cols[2]:
                with st.container(key="area_kpi_attention"):
                    st.markdown(
                        '<div class="area-kpi area-kpi--attention">'
                        f'<div class="area-kpi-value">{attention}</div>'
                        '<div class="area-kpi-label">Attention</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

            legend = "".join(
                f'<span class="area-map-legend-item">'
                f'<span style="color:{v["dot"]}">●</span> {v["label"]}</span>'
                for v in [*STATUS_DISPLAY.values(), NO_SENSOR_DISPLAY]
            )
            st.markdown(
                '<div class="area-map-header">'
                '<div class="area-map-title">Greenhouse Map</div>'
                f'<div class="area-map-legend">{legend}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            with st.container(key="area_map_panel"):
                try:
                    map_list = api_get("/api/v1/maps").get("maps", [])
                except (requests.RequestException, ValueError):
                    st.error("Unable to load the map.")
                    map_list = []

                if not map_list:
                    st.info("No map configured yet.")
                else:
                    try:
                        map_doc = api_get(f"/api/v1/maps/{map_list[0]['id']}").get("map", {})
                    except (requests.RequestException, ValueError):
                        st.error("Unable to load the map.")
                        map_doc = {}

                    image_path = ASSETS / map_doc["image_path"] if map_doc.get("image_path") else None
                    if image_path is None or not image_path.exists():
                        st.info("Map image is missing.")
                    else:
                        regions = [rotate_region(r) for r in map_doc.get("regions", [])]
                        selected_area_id = st.session_state.get("selected_area_id")
                        overlay, display_height = draw_map(
                            Image.open(image_path), regions, area_to_sensor, areas_by_id, unit, selected_area_id,
                        )
                        coords = streamlit_image_coordinates(overlay, key="greenhouse_map_click")
                        if coords and coords != st.session_state.get("_last_map_click"):
                            st.session_state["_last_map_click"] = coords
                            region = region_at(
                                regions,
                                coords["x"] / MAP_DISPLAY_WIDTH,
                                coords["y"] / display_height,
                            )
                            if region is not None:
                                area_id = region["area_id"]
                                st.session_state["selected_area_id"] = area_id
                                st.session_state["trend_sensor"] = area_to_sensor.get(area_id)
                                st.rerun()

            selected_area_id = st.session_state.get("selected_area_id")
            zone, selected_area = areas_by_id.get(selected_area_id, (None, None))
            if selected_area and area_to_sensor.get(selected_area_id) is None:
                with st.container(key="area_detail"):
                    st.markdown(
                        "<div class='area-empty-message'>No sensor is assigned to this region yet.</div>",
                        unsafe_allow_html=True,
                    )
            elif selected_area:
                status = STATUS_DISPLAY[selected_area["state"]]
                temperature = to_display(selected_area["temperature"], unit)
                low = to_display(selected_area["temperature_min"], unit)
                high = to_display(selected_area["temperature_max"], unit)
                range_text = (
                    f"{fmt(low)}–{fmt(high)}{unit}"
                    if low is not None and high is not None
                    else "Not configured"
                )
                battery = None
                last_seen_text = "No sensor reading yet"
                sensor_id = area_to_sensor.get(selected_area_id)
                if sensor_id is not None:
                    try:
                        sensor_health = api_get("/api/v1/sensors/health").get("sensors", [])
                    except (requests.RequestException, ValueError):
                        st.error("Unable to load sensor health data.")
                    else:
                        sensor_info = next(
                            (sensor for sensor in sensor_health
                             if str(sensor.get("id")) == str(sensor_id)),
                            {},
                        )
                        battery = sensor_info.get("battery")
                        minutes_ago = sensor_info.get("minutes_since_last_seen")
                        if minutes_ago is not None:
                            if minutes_ago < 1:
                                last_seen_text = "Recorded less than a minute ago"
                            elif minutes_ago < 60:
                                unit_label = "minute" if minutes_ago == 1 else "minutes"
                                last_seen_text = f"Recorded {minutes_ago} {unit_label} ago"
                            elif minutes_ago < 1440:
                                hours = minutes_ago // 60
                                last_seen_text = f"Recorded {hours} hour{'s' if hours != 1 else ''} ago"
                            else:
                                days = minutes_ago // 1440
                                last_seen_text = f"Recorded {days} day{'s' if days != 1 else ''} ago"
                with st.container(key="area_detail"):
                    detail_cols = st.columns([2.2, 1, 1, 1, 1.3], vertical_alignment="center")
                    with detail_cols[0]:
                        st.markdown(
                            "<div class='area-header'>"
                            "<div class='area-title-row'>"
                            f"<span class='area-name'>{zone.get('name') or 'Unassigned'} - "
                            f"{selected_area.get('name') or 'Unnamed'}</span>"
                            f"<span class='area-status'>{status['label']}</span>"
                            "</div>"
                            f"<div class='area-last-seen'>{last_seen_text}</div>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                    with detail_cols[1]:
                        st.caption("Temperature")
                        st.markdown(
                            f"**{fmt(temperature)}{unit}**"
                            if temperature is not None else "**—**"
                        )
                    with detail_cols[2]:
                        st.caption("Humidity")
                        humidity = selected_area["humidity"]
                        st.markdown(f"**{fmt(humidity)}%**" if humidity is not None else "**—**")
                    with detail_cols[3]:
                        st.caption("Battery")
                        st.markdown(f"**{fmt(battery)}%**" if battery is not None else "**—**")
                    with detail_cols[4]:
                        st.caption("Required range")
                        st.markdown(f"**{range_text}**")
#----------------------------------------------------------------
    sensor_options = {s["id"]: s.get("name") or s.get("hardware_id") or s["id"]
                      for s in sensors}

    
    # Clear a removed sensor selection before creating its widget.
    if st.session_state.get("trend_sensor") not in sensor_options:
        st.session_state.pop("trend_sensor", None)
    selected_id = st.segmented_control(
        "Select a sensor",
        options=list(sensor_options),
        default=next(iter(sensor_options), None),
        format_func=sensor_options.get,
        key="trend_sensor",
        selection_mode="single",
    )

    with st.container(key="sensor_trends"):
        st.subheader("Temperature & Humidity Over Time")
        period = st.segmented_control(
            "Time range",
            options=[*RANGES, "All history", "Custom"],
            default="7 days",
            key="trend_range",
            selection_mode="single",
        )
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
        if not readings:
            st.info("This sensor has not sent any readings yet.")
            return
        frame = history_frame(readings, selected_id)
        filtered = filter_history(frame, start, end)
        unit = temperature_unit()
        filtered["Temperature"] = to_display(filtered["Temperature"], unit)
        st.caption(f"Sensor: {sensor_options[selected_id]} · All times UTC · "
                   f"Temperature and humidity share one Y-axis. Temperature in {unit}, humidity in %.")
        if start is not None:
            label_end = end - timedelta(microseconds=1) if period == "Custom" else end
            st.caption(f"Selected window: {start:%Y-%m-%d %H:%M} — {label_end:%Y-%m-%d %H:%M} UTC")
        if filtered.empty:
            st.info("No sensor data available for this range. Try All history or different dates.")
            return
        chart = time_series_chart(
            filtered, ["Temperature", "Humidity"],
            colors=["#28734f", "#91b44c"], height=360,
        ).properties(background="#fff").configure_axis(
            labelColor="#000", titleColor="#000",
        ).configure_legend(labelColor="#000", titleColor="#000")
        st.altair_chart(chart, use_container_width=True)
        st.caption(f"{len(filtered):,} readings · "
                   f"{filtered['Date'].min():%Y-%m-%d %H:%M} — "
                   f"{filtered['Date'].max():%Y-%m-%d %H:%M} UTC")
       
        return

                 
update_dashboard()

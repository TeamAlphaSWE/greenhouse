import streamlit as st
st.title("Settings")


st.set_page_config(
    page_title="Settings",
    layout="wide"
)

st.caption("Manage greenhouse preferences and alert settings.")

st.divider()

# -------------------------
# Temperature
# -------------------------

st.subheader("Temperature")

temperature_unit = st.radio(
    "Temperature Unit",
    ["°C", "°F"],
    horizontal=True
)

col1, col2 = st.columns(2)

with col1:
    st.number_input(
        f"Minimum Temperature ({temperature_unit})",
        value=18.0
    )

with col2:
    st.number_input(
        f"Maximum Temperature ({temperature_unit})",
        value=28.0
    )

st.divider()

# -------------------------
# Humidity
# -------------------------

st.subheader("Humidity")

col1, col2 = st.columns(2)

with col1:
    st.number_input(
        "Minimum Humidity (%)",
        min_value=0,
        max_value=100,
        value=45
    )

with col2:
    st.number_input(
        "Maximum Humidity (%)",
        min_value=0,
        max_value=100,
        value=80
    )

st.divider()

# -------------------------
# Alerts
# -------------------------

st.subheader("Alerts")

alerts_enabled = st.toggle(
    "Enable Alerts",
    value=True
)

email_alerts = st.toggle(
    "Enable Email Notifications",
    value=False
)

email = st.text_input(
    "Notification Email",
)

st.divider()

# -------------------------
# Save
# -------------------------

if st.button(
    "Save Settings",
    type="primary",
    use_container_width=True
):
    st.success("Settings saved.")

import streamlit as st


st.title("Greenhouse Alerts")
st.write("View temperature and humidity alerts for greenhouse zones.")

st.divider()

alerts = [
    {"zone": "Zone 1", "type": "Temperature", "message": "Temperature is too high"},
    {"zone": "Zone 2", "type": "Humidity", "message": "Humidity is too low"},
    {"zone": "Zone 4", "type": "Temperature", "message": "Temperature is too low"}
]



st.subheader("Alert Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Alerts", len(alerts))

with col2:
    temperature_count = 0

    for alert in alerts:
        if alert["type"] == "Temperature":
            temperature_count += 1

    st.metric("Temperature Alerts", temperature_count)
with col3:
    humidity_count = 0

    for alert in alerts:
        if alert["type"] == "Humidity":
            humidity_count += 1

    st.metric("Humidity Alerts", humidity_count)

st.divider()


st.subheader("Recent Alerts")
st.caption("Sample alerts for testing the design")


for alert in alerts:
    with st.container(border=True):
        st.write("**" + alert["zone"] + " - " + alert["type"] + " Alert**")
        st.write(alert["message"])

# Navigation links
st.page_link("views/dashboard.py", label="Go to Dashboard")
st.page_link("views/settings.py", label="Go to Settings")
st.page_link("views/landing.py", label="Go to Home")

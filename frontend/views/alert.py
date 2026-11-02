
import streamlit as st


st.title("Greenhouse Alerts")
st.write("View temperature and humidity alerts for greenhouse zones.")

st.divider()

alerts = [
    {"zone": "Zone 1", "type": "Temperature", "message": "Temperature is too high", "value": 35, "threshold": 30},
   {"zone": "Zone 2", "type": "Humidity", "message": "Humidity is too low", "value": 35, "threshold": 45},
    {"zone": "Zone 4", "type": "Temperature", "message": "Temperature is too low", "value": 17, "threshold": 20}
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

        if alert["type"] == "Temperature" or alert["type"] == "Humidity":
            difference = abs(alert["value"] - alert["threshold"])

            if alert["type"] == "Temperature":
                unit = "°C"
            else:
                unit = " percentage points"

            if alert["value"] > alert["threshold"]:
                st.write(f'{alert["type"]} was {difference}{unit} above the limit')
            else:
                st.write(f'{alert["type"]} was {difference}{unit} below the limit')

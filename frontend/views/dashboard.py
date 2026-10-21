import streamlit as st
st.title("Dashboard")

# will have all the zone information,the box in figma called as "monitoring positions"

st.page_link("views/settings.py", label="Go to Settings")
st.page_link("views/alert.py", label="Go to Alerts")
st.page_link("views/landing.py", label="Go to home")

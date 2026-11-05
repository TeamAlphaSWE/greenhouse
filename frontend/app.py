import streamlit as st
import requests        # for making HTTP requests to the Flask local server

# Pandas and Numpy are a packaged deal since Pandas relies on Numpy for numerical operations!!
# lets work on a dashboard!
login = st.Page("login.py", title="Login")

landing=st.Page("views/landing.py", title="Home", default=True)
sensors_page=st.Page("views/sensors.py", title="Sensors")
activate_page=st.Page("views/activate_sensor.py", title="Activate Sensor")
alert=st.Page("views/alert.py", title="Alert")
settings=st.Page("views/settings.py", title="Settings")
credits=st.Page("views/credits.py", title="Credits")

if not st.session_state.get("logged_in", False):
    nav = st.navigation(
        [login],
        position="hidden"
    )
else:
    nav = st.navigation(
        [landing, sensors_page, activate_page, alert, settings, credits]
    )

nav.run()
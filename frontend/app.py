import streamlit as st
import requests        # for making HTTP requests to the Flask local server
from settings_api import get_settings, DEFAULT_SETTINGS
# Pandas and Numpy are a packaged deal since Pandas relies on Numpy for numerical operations!!
# lets work on a dashboard!
login = st.Page("login.py", title="Login")

landing=st.Page("views/landing.py", title="Home", default=True)
sensors_page=st.Page("views/sensors.py", title="Sensors")
alert=st.Page("views/alert.py", title="Alert")
ask=st.Page("views/ask.py", title="Ask Sprout 🌱")
settings=st.Page("views/settings.py", title="Settings")
credits=st.Page("views/credits.py", title="Credits")
zones=st.Page("views/zones.py", title="Zones")
change_pass=st.Page("views/change_pass.py", title="change password")

if not st.session_state.get("logged_in", False):
    nav = st.navigation(
        [login],
        position="hidden"
    )
else:
    nav = st.navigation(
        [landing, sensors_page, zones, alert, ask, settings, credits, change_pass]
    )
    if "settings" not in st.session_state:
        try:
            st.session_state["settings"] = get_settings()
        except requests.RequestException:
            st.session_state["settings"] = dict(DEFAULT_SETTINGS)
            st.toast("Saved settings could not be loaded. Settings will be set to defaults.")
        st.session_state["temperature_unit"] = st.session_state["settings"]["temperature_unit"]

if st.session_state.get("_last_page") != nav.title:
    st.session_state.pop("activating_sensor_id", None)
st.session_state["_last_page"] = nav.title

nav.run()
import streamlit as st
import requests        # for making HTTP requests to the Flask local server

# Pandas and Numpy are a packaged deal since Pandas relies on Numpy for numerical operations!!
# lets work on a dashboard!
login = st.Page("login.py", title="Login")

landing=st.Page("views/landing.py", title="Home", default=True)
dashboard=st.Page("views/dashboard.py", title="Dashboard")
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
        [landing, dashboard, alert, settings, credits]
    )

nav.run()
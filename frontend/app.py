import streamlit as st
import requests        # for making HTTP requests to the Flask local server


landing=st.Page("views/landing.py", title="Home", default=True)
dashboard=st.Page("views/dashboard.py", title="Dashboard")
alert=st.Page("views/alert.py", title="Alert")
settings=st.Page("views/settings.py", title="Settings")

nav=st.navigation([landing,dashboard,alert,settings])
nav.run()

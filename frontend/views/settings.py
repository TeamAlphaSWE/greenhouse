import requests
import streamlit as st

from settings_api import save_settings
from theme import page_header
from units import CELSIUS, FAHRENHEIT

current = st.session_state["settings"]
page_header("Settings", "Manage greenhouse preferences and alert settings.")


st.set_page_config(
    page_title="Settings | Greenhouse",
    page_icon="🌱",
    layout="wide"
)

st.divider()

# -------------------------
# Temperature
# -------------------------

st.subheader("Temperature")

unit_options = [CELSIUS, FAHRENHEIT]
selected_unit = st.radio(
    "Temperature Unit",
    unit_options,
    index=unit_options.index(current["temperature_unit"]),
    horizontal=True
)

st.divider()

# -------------------------
# Alerts
# -------------------------

st.subheader("Alerts")

alerts_enabled = st.toggle(
    "Enable Alerts",
    value=current["alerts_enabled"]
)

email_alerts = st.toggle(
    "Enable Email Notifications",
    value=current["email_alerts_enabled"]
)

email = st.text_input(
    "Notification Email",
    value=current["notification_email"] or ""
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
    new_settings = {
        "temperature_unit": selected_unit,
        "alerts_enabled": alerts_enabled,
        "email_alerts_enabled": email_alerts,
        "notification_email": email.strip() or None,
    }
    if new_settings["email_alerts_enabled"] and not new_settings["notification_email"]:
        st.error("Enter a notification email to turn on email alerts")
    else:
        try:
            saved = save_settings(new_settings)
            st.session_state["settings"] = saved
            st.session_state["temperature_unit"] = saved["temperature_unit"]
            st.success("Settings saved.")
        
        except requests.HTTPError as error:
            status = error.response.status_code
            if status == 401:
                st.error("You're not signed in or session has ended. Please sign in again.")
            elif status == 400:
                st.error(error.response.json().get("error", "Invalid settings"))
            else:
                st.error("Couldn't save settings. Please try again.")
        except requests.RequestException:
            st.error("Couldn't reach the server. Please try again.")

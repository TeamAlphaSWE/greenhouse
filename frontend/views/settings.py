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

st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #F6F7EF !important;
}
[data-testid="stMain"] * {
    color: #18372A !important;
}
[data-testid="stMain"] .gh-page-hero h1 {
    color: #fffdf4 !important;
}
[data-testid="stMain"] .gh-page-hero .gh-page-sub {
    color: #d4af37 !important;
}
.st-key-temperature_section,
.st-key-alerts_section,
.st-key-privacy_section {
    border: 1px solid #DCE4D6;
    background: #DCE4D6;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.st-key-privacy_section button {
    background: #123d2d !important;
    border-color: #123d2d !important;
}
.st-key-privacy_section button,
.st-key-privacy_section button * {
    color: #fffdf4 !important;
    -webkit-text-fill-color: #fffdf4 !important;
}
.st-key-alerts_section [data-baseweb="input"] > div {
    background: #123d2d !important;
    border-color: #123d2d !important;
}
.st-key-alerts_section input[type="text"] {
    background: transparent !important;
    color: #fffdf4 !important;
    -webkit-text-fill-color: #fffdf4 !important;
}
</style>
""", unsafe_allow_html=True)


with st.container(key="temperature_section"):
    st.subheader("Temperature")

    unit_options = [CELSIUS, FAHRENHEIT]
    selected_unit = st.radio(
        "Temperature Unit",
        unit_options,
        index=unit_options.index(current["temperature_unit"]),
        horizontal=True
    )

with st.container(key="alerts_section"):
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

with st.container(key="privacy_section"):
    st.subheader("Privacy/ Secruity")
    if st.button("Change Password"):
        st.switch_page("views/change_pass.py")

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

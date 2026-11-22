"""Helpers for reading and saving the logged-in user settings from the backend API."""
import requests
import streamlit as st

#TODO (#209): temporary import. 209 is expected to add frontend/api_client.py, replace with:
# from api_client import BACKEND_URL, TIMEOUT_SECONDS, auth_headers
# and delete the auth_headers() copy below

from sensor_api import BACKEND_URL, TIMEOUT_SECONDS

DEFAULT_SETTINGS = {
    "temperature_unit": "°C",
    "alerts_enabled": True,
    "email_alerts_enabled": False,
    "notification_email": None,
}

#TODO (#209) : temporary copy of api_client.auth_headers(). Delete aftet #209 gets merged
def auth_headers():
    token = st.session_state.get("token")
    return {"authorization": f"Bearer {token}"} if token else {}

def get_settings():
    response = requests.get(
        f"{BACKEND_URL}/api/v1/settings",
        headers=auth_headers(),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["settings"]

def save_settings(settings):
    response = requests.put(
        f"{BACKEND_URL}/api/v1/settings",
        headers=auth_headers(),
        json=settings,
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["settings"]
"""Helpers for reading and saving the logged-in user settings from the backend API."""
import requests

from api_client import BACKEND_URL, TIMEOUT_SECONDS, auth_headers

DEFAULT_SETTINGS = {
    "temperature_unit": "°C",
    "alerts_enabled": True,
    "email_alerts_enabled": False,
    "notification_email": None,
}

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
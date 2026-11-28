import requests
import streamlit as st

from api_client import BACKEND_URL, TIMEOUT_SECONDS, auth_headers


def get_current_user():
    response = requests.get(
        f"{BACKEND_URL}/api/v1/me",
        headers=auth_headers(),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["user"]


def is_admin():
    return st.session_state.get("admin") is True

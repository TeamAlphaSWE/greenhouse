from unittest.mock import MagicMock, patch

import pytest
import requests
import streamlit as st

import settings_api

SAVED = {
    "temperature_unit": "°F",
    "alerts_enabled": False,
    "email_alerts_enabled": True,
    "notification_email": "greenhouse@example.com",
}


def fake_response(status, body):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = body
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


@pytest.fixture
def token():
    st.session_state["token"] = "abc"
    yield
    del st.session_state["token"]


def test_get_settings_sends_token_and_unwraps(token):
    with patch("settings_api.requests.get", return_value=fake_response(200, {"settings": SAVED})) as get:
        result = settings_api.get_settings()

    args, kwargs = get.call_args
    assert args[0].endswith("/api/v1/settings")
    assert kwargs["headers"] == {"Authorization": "Bearer abc"}
    assert result == SAVED


def test_save_settings_puts_full_body_and_returns_saved(token):
    with patch("settings_api.requests.put", return_value=fake_response(200, {"settings": SAVED})) as put:
        result = settings_api.save_settings(SAVED)

    args, kwargs = put.call_args
    assert args[0].endswith("/api/v1/settings")
    assert kwargs["headers"] == {"Authorization": "Bearer abc"}
    assert kwargs["json"] == SAVED
    assert result == SAVED


def test_get_settings_raises_on_401():
    with patch("settings_api.requests.get", return_value=fake_response(401, {"error": "Missing or invalid Authorization header"})):
        with pytest.raises(requests.HTTPError):
            settings_api.get_settings()


def test_save_settings_raises_on_400(token):
    with patch("settings_api.requests.put", return_value=fake_response(400, {"error": "bad"})):
        with pytest.raises(requests.HTTPError):
            settings_api.save_settings(SAVED)
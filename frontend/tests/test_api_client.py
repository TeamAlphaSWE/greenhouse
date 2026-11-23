from unittest.mock import MagicMock, patch

import streamlit as st

import sensor_api
from api_client import auth_headers


def test_auth_headers_without_token():
    st.session_state.pop("token", None)

    assert auth_headers() == {}


def test_auth_headers_with_token():
    st.session_state["token"] = "abc"
    try:
        assert auth_headers() == {"Authorization": "Bearer abc"}
    finally:
        del st.session_state["token"]


def test_sensor_api_sends_token():
    st.session_state["token"] = "abc"
    response = MagicMock(status_code=200)
    response.json.return_value = {"sensors": []}
    try:
        with patch("sensor_api.requests.get", return_value=response) as get:
            sensor_api.get_sensors()
    finally:
        del st.session_state["token"]

    assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer abc"}

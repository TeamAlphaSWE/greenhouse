from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parents[1]
APP = FRONTEND / "app.py"
SENSORS = FRONTEND / "views" / "sensors.py"

PENDING = {"id": "s1", "hardware_id": "shellyhtg3-new", "status": "pending"}
SETTINGS = {"temperature_unit": "°C", "alerts_enabled": True,
            "email_alerts_enabled": False, "notification_email": None}


def response(status=200, payload=None):
    result = MagicMock()
    result.status_code = status
    result.json.return_value = payload or {}
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(f"status {status}")
    return result


def backend(me):
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs.get("headers")))
        if url.endswith("/me"):
            return me
        if url.endswith("/settings"):
            return response(payload={"settings": SETTINGS})
        if url.endswith("/sensors"):
            return response(payload={"sensors": [PENDING]})
        if url.endswith("/zones"):
            return response(payload={"zones": []})
        if url.endswith("/sensors/health"):
            return response(payload={"sensors": []})
        if url.endswith("/latest"):
            return response(status=404)
        if "/sensor_data/" in url:
            return response(payload={"sensor_data": []})
        if url.endswith("/areas/overview"):
            return response(payload={"zones": []})
        return response(payload={})

    return get, calls


def run_app(me):
    get, calls = backend(me)
    app = AppTest.from_file(str(APP), default_timeout=10)
    app.session_state["logged_in"] = True
    app.session_state["token"] = "abc"
    with patch("requests.get", side_effect=get):
        app.run()
    return app, calls


def test_admin_flag_fetched_from_me_after_login():
    app, calls = run_app(response(payload={"user": {"id": "u1", "username": "alice", "admin": True}}))

    assert app.session_state["admin"] is True
    me_calls = [c for c in calls if c[0].endswith("/api/v1/me")]
    assert me_calls == [(me_calls[0][0], {"Authorization": "Bearer abc"})]


def test_non_admin_flag_fetched_from_me():
    app, _ = run_app(response(payload={"user": {"id": "u1", "username": "bob", "admin": False}}))

    assert app.session_state["admin"] is False


def test_me_failure_treats_user_as_non_admin():
    app, _ = run_app(response(status=500))

    assert app.session_state["admin"] is False


def test_me_unreachable_treats_user_as_non_admin():
    get, _ = backend(None)

    def failing_get(url, **kwargs):
        if url.endswith("/me"):
            raise requests.ConnectionError()
        return get(url, **kwargs)

    app = AppTest.from_file(str(APP), default_timeout=10)
    app.session_state["logged_in"] = True
    with patch("requests.get", side_effect=failing_get):
        app.run()

    assert app.session_state["admin"] is False


def run_sensors(admin, activating=None):
    get, _ = backend(None)
    app = AppTest.from_file(str(SENSORS), default_timeout=10)
    if admin is not None:
        app.session_state["admin"] = admin
    if activating:
        app.session_state["activating_sensor_id"] = activating
    with patch("requests.get", side_effect=get):
        app.run()
    return app


def activate_buttons(app):
    return [b for b in app.button if b.label == "Activate"]


def test_admin_sees_activate_button():
    app = run_sensors(admin=True)

    assert len(activate_buttons(app)) == 1


def test_non_admin_does_not_see_activate_button():
    app = run_sensors(admin=False)

    assert activate_buttons(app) == []
    assert not app.exception


def test_unknown_role_does_not_see_activate_button():
    app = run_sensors(admin=None)

    assert activate_buttons(app) == []


def test_non_admin_cannot_open_activation_form():
    app = run_sensors(admin=False, activating="s1")

    assert [s.value for s in app.subheader if s.value == "Activate sensor"] == []
    assert "activating_sensor_id" not in app.session_state
    assert not app.exception

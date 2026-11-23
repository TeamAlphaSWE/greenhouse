from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parent.parent / "views" / "settings.py"

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


def load(settings=SAVED):
    app = AppTest.from_file(str(PAGE), default_timeout=10)
    app.session_state["settings"] = dict(settings)
    app.session_state["token"] = "abc"
    return app.run()


def click_save(app):
    [b for b in app.button if b.label == "Save Settings"][0].click().run()


def test_page_prefills_from_saved_settings():
    app = load()

    assert not app.exception
    assert app.radio[0].value == "°F"
    assert app.toggle[0].value is False
    assert app.toggle[1].value is True
    assert app.text_input[0].value == "greenhouse@example.com"


def test_page_has_no_min_max_inputs():
    app = load()

    assert len(app.number_input) == 0


def test_email_alerts_without_email_shows_error_and_does_not_save():
    app = load()
    with patch("requests.put") as put:
        app.text_input[0].input("   ").run()
        click_save(app)

    put.assert_not_called()
    assert "notification email" in app.error[0].value


def test_successful_save_sends_settings_and_updates_session():
    saved = {**SAVED, "temperature_unit": "°C", "notification_email": "green@monitoring.com"}
    app = load()
    with patch("requests.put", return_value=fake_response(200, {"settings": saved})) as put:
        app.radio[0].set_value("°C").run()
        app.text_input[0].input("  green@monitoring.com  ").run()
        click_save(app)

    assert put.call_args.kwargs["json"] == {
        "temperature_unit": "°C",
        "alerts_enabled": False,
        "email_alerts_enabled": True,
        "notification_email": "green@monitoring.com",
    }
    assert app.session_state["settings"] == saved
    assert app.session_state["temperature_unit"] == "°C"
    assert app.success[0].value == "Settings saved."
    assert not app.error


def test_400_shows_backend_message():
    app = load()
    response = fake_response(400, {"error": "temperature_unit must be '°C' or '°F'"})
    with patch("requests.put", return_value=response):
        click_save(app)

    assert app.error[0].value == "temperature_unit must be '°C' or '°F'"
    assert app.session_state["settings"] == SAVED


def test_401_asks_user_to_sign_in_again():
    app = load()
    with patch("requests.put", return_value=fake_response(401, {"error": "Missing or invalid Authorization header"})):
        click_save(app)

    assert "sign in again" in app.error[0].value


def test_server_unreachable_shows_error():
    app = load()
    with patch("requests.put", side_effect=requests.ConnectionError()):
        click_save(app)

    assert app.error[0].value == "Couldn't reach the server. Please try again."
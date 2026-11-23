from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parent.parent / "login.py"


def fake_response(status, body):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = body
    return response


def submit(username, password, post):
    app = AppTest.from_file(str(PAGE), default_timeout=10)
    with patch("requests.post", post):
        app.run()
        app.text_input[0].input(username)
        app.text_input[1].input(password)
        app.button[0].click().run()
    return app


def test_login_success_stores_token():
    post = MagicMock(return_value=fake_response(200, {"token": "abc"}))

    app = submit("Alice", "secret", post)

    args, kwargs = post.call_args
    assert args[0].endswith("/api/v1/login")
    assert kwargs["json"] == {"username": "alice", "password": "secret"}
    assert app.session_state["token"] == "abc"
    assert app.session_state["logged_in"] is True
    assert app.session_state["username"] == "alice"
    assert not app.error


def test_login_wrong_password_shows_error():
    post = MagicMock(return_value=fake_response(401, {"error": "Invalid username or password"}))

    app = submit("alice", "wrong", post)

    assert app.error[0].value == "Invalid email or password."
    assert "token" not in app.session_state
    assert app.session_state["logged_in"] is False


def test_login_server_error_shows_error():
    post = MagicMock(return_value=fake_response(500, {"error": "Unexpected server error"}))

    app = submit("alice", "secret", post)

    assert app.error[0].value == "Login failed. Please try again."
    assert "token" not in app.session_state


def test_login_backend_unreachable_shows_error():
    post = MagicMock(side_effect=requests.ConnectionError())

    app = submit("alice", "secret", post)

    assert app.error[0].value == "Unable to connect to the server."
    assert "token" not in app.session_state

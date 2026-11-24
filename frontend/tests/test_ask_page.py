import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parent.parent / "views" / "ask.py"


def fake_response(status, body):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = body
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


def load():
    app = AppTest.from_file(str(PAGE), default_timeout=10)
    app.session_state["token"] = "abc"
    return app.run()


def ask_question(app, text, response):
    """requests.post's json= kwarg is the same list object ask.py later appends
    to, so a mock's call_args would reflect post-call mutations. Snapshot it
    (deep copy) at call time instead."""
    sent = {}

    def fake_post(*args, **kwargs):
        sent["json"] = copy.deepcopy(kwargs["json"])
        return response

    with patch("requests.post", side_effect=fake_post):
        app.chat_input[0].set_value(text).run()
    return sent["json"]


def test_greeting_shown_before_any_question():
    app = load()

    assert not app.exception
    assert len(app.chat_message) == 1
    assert "Sprout" in app.chat_message[0].markdown[0].value


def test_question_is_sent_with_empty_history_and_response_is_rendered():
    app = load()
    response = fake_response(200, {"answer": "Here's what your sensors report."})

    sent = ask_question(app, "tell me about humidity", response)

    assert sent == {
        "message": "tell me about humidity",
        "history": [],
    }
    bubbles = app.chat_message
    assert bubbles[-2].name == "user"
    assert bubbles[-2].markdown[0].value == "tell me about humidity"
    assert bubbles[-1].name == "assistant"
    assert bubbles[-1].markdown[0].value == "Here's what your sensors report."
    assert not app.error


def test_followup_question_includes_prior_turns_in_history():
    app = load()
    ask_question(app, "first question", fake_response(200, {"answer": "first answer"}))

    sent = ask_question(app, "second question", fake_response(200, {"answer": "second answer"}))

    assert sent == {
        "message": "second question",
        "history": [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ],
    }


def test_empty_answer_shows_info_state():
    app = load()

    ask_question(app, "anything?", fake_response(200, {"answer": ""}))

    assert app.info[0].value == "Sprout didn't have anything to add. Try asking a different way."
    assert app.session_state["assistant_history"] == []


def test_assistant_unavailable_shows_error_and_does_not_save_history():
    app = load()

    ask_question(app, "tell me about humidity", fake_response(502, {"error": "AI assistant is unavailable"}))

    assert app.error[0].value == "AI assistant is unavailable"
    assert app.session_state["assistant_history"] == []


def test_401_asks_user_to_sign_in_again():
    app = load()

    ask_question(app, "tell me about humidity", fake_response(401, {"error": "Missing or invalid Authorization header"}))

    assert "sign in again" in app.error[0].value


def test_server_unreachable_shows_error():
    app = load()

    with patch("requests.post", side_effect=requests.ConnectionError()):
        app.chat_input[0].set_value("tell me about humidity").run()

    assert app.error[0].value == "Couldn't reach the server. Please try again."
    assert app.session_state["assistant_history"] == []

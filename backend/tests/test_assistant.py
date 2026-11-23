from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import pytest

from app.services.assistant_tools import ASSISTANT_TOOLS


def mock_ai_service(app, monkeypatch, answer="Everything looks fine."):
    service = MagicMock()
    service.invoke.return_value = answer
    monkeypatch.setitem(app.extensions, "ai_service", service)
    return service


def test_chat_service_unavailable_returns_503(app, client):
    response = client.post("/api/v1/assistant/chat", json={"message": "How's zone A?"})

    assert response.status_code == 503
    assert response.get_json() == {"error": "AI assistant is not configured"}


@pytest.mark.parametrize("body", [
    {},
    {"message": ""},
    {"message": "   "},
    {"message": 123},
])
def test_chat_requires_message(app, client, monkeypatch, body):
    mock_ai_service(app, monkeypatch)

    response = client.post("/api/v1/assistant/chat", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "message is required"}


def test_chat_invalid_json_returns_400(app, client, monkeypatch):
    mock_ai_service(app, monkeypatch)

    response = client.post("/api/v1/assistant/chat", data="not json",
                            content_type="application/json")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid JSON"}


@pytest.mark.parametrize("history, error", [
    ("not a list", "history must be a list"),
    ([1], "each history entry must be an object"),
    ([{"role": "system", "content": "x"}], "each history entry needs a role of 'user' or 'assistant'"),
    ([{"role": "user"}], "each history entry needs non-empty content"),
    ([{"role": "user", "content": "  "}], "each history entry needs non-empty content"),
])
def test_chat_invalid_history_returns_400(app, client, monkeypatch, history, error):
    mock_ai_service(app, monkeypatch)

    response = client.post("/api/v1/assistant/chat",
                            json={"message": "How's zone A?", "history": history})

    assert response.status_code == 400
    assert response.get_json() == {"error": error}


def test_chat_returns_model_answer(app, client, monkeypatch):
    mock_ai_service(app, monkeypatch, answer="It's 22C and normal.")

    response = client.post("/api/v1/assistant/chat", json={"message": "How's zone A?"})

    assert response.status_code == 200
    assert response.get_json() == {"answer": "It's 22C and normal."}


def test_chat_gives_the_model_the_assistant_tools(app, client, monkeypatch):
    service = mock_ai_service(app, monkeypatch)

    client.post("/api/v1/assistant/chat", json={"message": "How's Greenhouse Sensor 1?"})

    assert service.invoke.call_args.kwargs["tools"] is ASSISTANT_TOOLS
    messages = service.invoke.call_args.args[0]
    assert isinstance(messages[0], SystemMessage)
    assert "tools" in messages[0].content
    assert isinstance(messages[-1], HumanMessage)
    assert messages[-1].content == "How's Greenhouse Sensor 1?"


def test_chat_supports_conversation_history(app, client, monkeypatch):
    service = mock_ai_service(app, monkeypatch)
    history = [
        {"role": "user", "content": "What's the temperature in zone A?"},
        {"role": "assistant", "content": "It's 22C."},
    ]

    client.post("/api/v1/assistant/chat", json={"message": "And humidity?", "history": history})

    messages = service.invoke.call_args.args[0]
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "What's the temperature in zone A?"
    assert isinstance(messages[2], AIMessage)
    assert messages[2].content == "It's 22C."
    assert messages[-1].content == "And humidity?"


def test_chat_provider_failure_returns_502(app, client, monkeypatch):
    service = mock_ai_service(app, monkeypatch)
    service.invoke.side_effect = RuntimeError("LLM request timed out")

    response = client.post("/api/v1/assistant/chat", json={"message": "How's zone A?"})

    assert response.status_code == 502
    assert response.get_json() == {"error": "AI assistant is unavailable"}

from unittest.mock import MagicMock, patch
import pytest
from app.services.ai_service import AIService, build_image_message
from openai import APIConnectionError, APIStatusError, APITimeoutError

import io

@pytest.fixture
def ai_config():
    return {
        "AI_BASE_URL": "http://localhost:1234/v1",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "test-model",
        "AI_TEMPERATURE": 0.7,
        "AI_MAX_TOKENS": 2048,
        "AI_TIMEOUT": 30,
    }

@patch("app.services.ai_service.ChatOpenAI")
def test_ai_service_initialization(mock_chat_openai, ai_config):
    AIService(ai_config)

    mock_chat_openai.assert_called_once_with(
        base_url="http://localhost:1234/v1",
        api_key="test-key",
        model="test-model",
        temperature=0.7,
        max_tokens=2048,
        timeout=30,
        use_responses_api=True,
        store=False,
    )

def test_missing_configuration():
    with pytest.raises(
        ValueError,
        match="Missing required configuration: AI_BASE_URL"
    ):
        AIService({})

@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_text_message(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    mock_model.invoke.return_value.text = "Hello Greenhouse"

    ai = AIService(ai_config)
    response = ai.invoke([
        ("user", "Say hello")
    ])
    assert response == "Hello Greenhouse"
    mock_model.invoke.assert_called_once_with([
        ("user", "Say hello")
    ])

@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_image_message(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    mock_model.invoke.return_value.text = "Healthy plants"

    ai = AIService(ai_config)

    message = build_image_message(
        "Describe this greenhouse image",
        b"fake-image-data"
    )

    response = ai.invoke([message])

    assert response == "Healthy plants"

    sent_messages = mock_model.invoke.call_args.args[0]

    assert sent_messages[0].content[0]["type"] == "text"
    assert sent_messages[0].content[0]["text"] == (
        "Describe this greenhouse image"
    )

    assert sent_messages[0].content[1]["type"] == "image_url"

    image_url = sent_messages[0].content[1]["image_url"]["url"]

    assert image_url.startswith("data:image/jpeg;base64,")

@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_timeout(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    mock_model.invoke.side_effect = APITimeoutError(request=None)

    ai = AIService(ai_config)

    with pytest.raises(RuntimeError, match="LLM request timed out"):
        ai.invoke([("user", "Hello")])

@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_connection_error(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    mock_model.invoke.side_effect = APIConnectionError(request=None)

    ai = AIService(ai_config)

    with pytest.raises(RuntimeError, match="LLM provider is unavailable"):
        ai.invoke([("user", "Hello")])

@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_api_status_error(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value

    mock_model.invoke.side_effect = APIStatusError(
        "Invalid API key",
        response=MagicMock(status_code=401),
        body=None,
    )

    ai = AIService(ai_config)

    with pytest.raises(
        RuntimeError,
        match="LLM provider returned status 401"
    ):
        ai.invoke([("user", "Hello")])


# For flask endpoint testing

@pytest.fixture
def mock_ai_service(app, monkeypatch):
    mock_service = MagicMock()
    mock_service.invoke.return_value = "Greenhouse AI response"

    monkeypatch.setitem(
        app.extensions,
        "ai_service",
        mock_service,
    )

    return mock_service


def test_ai_text_invocation(client, mock_ai_service):

    response = client.post(
        "/api/v1/ai/invoke",
        data={"prompt": "Describe the greenhouse"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "response": "Greenhouse AI response"
    }

    messages = mock_ai_service.invoke.call_args.args[0]

    assert messages[0].content == "Describe the greenhouse"


def test_ai_image_invocation(client, mock_ai_service):

    image_data = b"fake-image-data"

    response = client.post(
        "/api/v1/ai/invoke",
        data={
            "prompt": "Describe this plant",
            "image": (
                io.BytesIO(image_data),
                "plant.jpg",
                "image/jpeg",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    messages = mock_ai_service.invoke.call_args.args[0]
    content = messages[0].content

    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Describe this plant"

    assert content[1]["type"] == "image_url"

    image_url = content[1]["image_url"]["url"]

    assert image_url.startswith("data:image/jpeg;base64,")


def test_ai_missing_prompt(client, mock_ai_service):

    response = client.post(
        "/api/v1/ai/invoke",
        data={},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "A prompt is required"
    }

    mock_ai_service.invoke.assert_not_called()


def test_ai_unsupported_image_type(
    client,
    mock_ai_service,
):

    response = client.post(
        "/api/v1/ai/invoke",
        data={
            "prompt": "Describe this file",
            "image": (
                io.BytesIO(b"fake-data"),
                "document.gif",
                "image/gif",
            ),
        }
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Unsupported image type"
    }

    mock_ai_service.invoke.assert_not_called()


def test_ai_empty_image(
    client,
    mock_ai_service,
):

    response = client.post(
        "/api/v1/ai/invoke",
        data={
            "prompt": "Describe this image",
            "image": (
                io.BytesIO(b""),
                "empty.jpg",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Uploaded image is empty"
    }

    mock_ai_service.invoke.assert_not_called()


def test_ai_image_too_large(
    client,
    mock_ai_service,
):

    oversized_image = b"x" * (4 * 1024 * 1024 + 1)

    response = client.post(
        "/api/v1/ai/invoke",
        data={
            "prompt": "Describe this image",
            "image": (
                io.BytesIO(oversized_image),
                "large.jpg",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 413
    assert response.get_json() == {
        "error": "Image exceeds the 4 MB size limit"
    }

    mock_ai_service.invoke.assert_not_called()


def test_ai_service_unavailable(app, client):

    app.extensions["ai_service"] = None

    response = client.post(
        "/api/v1/ai/invoke",
        data={"prompt": "Hello"},
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "error": "AI service is currently unavailable"
    }


def test_ai_provider_failure(
    client,
    mock_ai_service,
):

    mock_ai_service.invoke.side_effect = RuntimeError(
        "LLM provider is unavailable"
    )

    response = client.post(
        "/api/v1/ai/invoke",
        data={"prompt": "Hello"},
    )

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "AI provider invocation failed"
    }




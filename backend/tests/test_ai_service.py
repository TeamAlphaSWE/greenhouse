from io import BytesIO
from unittest.mock import MagicMock, patch
import pytest
from werkzeug.datastructures import FileStorage
from app.services.ai_service import AIService, build_image_message, image_from_request_files
from openai import APIConnectionError, APIStatusError, APITimeoutError

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


def test_image_from_request_files_missing_returns_none():
    image_bytes, mime_type = image_from_request_files({})

    assert image_bytes is None
    assert mime_type is None


def test_image_from_request_files_reads_bytes_and_mimetype():
    files = {
        "image": FileStorage(
            stream=BytesIO(b"fake-image-data"),
            filename="plant.jpg",
            content_type="image/jpeg",
        )
    }

    image_bytes, mime_type = image_from_request_files(files)

    assert image_bytes == b"fake-image-data"
    assert mime_type == "image/jpeg"


def test_image_from_request_files_rejects_unsupported_type():
    files = {
        "image": FileStorage(
            stream=BytesIO(b"fake-data"),
            filename="document.gif",
            content_type="image/gif",
        )
    }

    with pytest.raises(ValueError, match="Unsupported image type"):
        image_from_request_files(files)


def test_image_from_request_files_rejects_empty_image():
    files = {
        "image": FileStorage(
            stream=BytesIO(b""),
            filename="empty.jpg",
            content_type="image/jpeg",
        )
    }

    with pytest.raises(ValueError, match="Uploaded image is empty"):
        image_from_request_files(files)


def test_image_from_request_files_rejects_oversized_image():
    oversized_image = b"x" * (4 * 1024 * 1024 + 1)
    files = {
        "image": FileStorage(
            stream=BytesIO(oversized_image),
            filename="large.jpg",
            content_type="image/jpeg",
        )
    }

    with pytest.raises(ValueError, match="Image exceeds the 4 MB size limit"):
        image_from_request_files(files)



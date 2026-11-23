from io import BytesIO
from unittest.mock import MagicMock, patch
import pytest
from langchain_core.tools import tool
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


@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_with_tools_calls_tool_and_returns_final_answer(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    bound_model = mock_model.bind_tools.return_value

    tool_call_response = MagicMock()
    tool_call_response.tool_calls = [{"name": "get_greeting", "args": {"name": "Rocky"}, "id": "call_1"}]
    final_response = MagicMock()
    final_response.tool_calls = []
    final_response.text = "Hello, Rocky!"
    bound_model.invoke.side_effect = [tool_call_response, final_response]

    @tool
    def get_greeting(name: str) -> str:
        """Build a greeting for name."""
        return f"Hi {name}"

    ai = AIService(ai_config)
    response = ai.invoke([("user", "greet Rocky")], tools=[get_greeting])

    assert response == "Hello, Rocky!"
    mock_model.bind_tools.assert_called_once_with([get_greeting])
    second_call_messages = bound_model.invoke.call_args_list[1].args[0]
    tool_messages = [m for m in second_call_messages if getattr(m, "tool_call_id", None) == "call_1"]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "Hi Rocky"


@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_with_tools_reports_tool_failure_to_the_model(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    bound_model = mock_model.bind_tools.return_value

    tool_call_response = MagicMock()
    tool_call_response.tool_calls = [{"name": "broken_tool", "args": {}, "id": "call_1"}]
    final_response = MagicMock()
    final_response.tool_calls = []
    final_response.text = "Sorry, I couldn't retrieve that."
    bound_model.invoke.side_effect = [tool_call_response, final_response]

    @tool
    def broken_tool() -> str:
        """Always fails."""
        raise RuntimeError("database is down")

    ai = AIService(ai_config)
    response = ai.invoke([("user", "hi")], tools=[broken_tool])

    assert response == "Sorry, I couldn't retrieve that."
    second_call_messages = bound_model.invoke.call_args_list[1].args[0]
    tool_messages = [m for m in second_call_messages if getattr(m, "tool_call_id", None) == "call_1"]
    assert "database is down" in tool_messages[0].content


@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_with_tools_handles_unknown_tool_name(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    bound_model = mock_model.bind_tools.return_value

    tool_call_response = MagicMock()
    tool_call_response.tool_calls = [{"name": "nonexistent", "args": {}, "id": "call_1"}]
    final_response = MagicMock()
    final_response.tool_calls = []
    final_response.text = "I couldn't find that information."
    bound_model.invoke.side_effect = [tool_call_response, final_response]

    @tool
    def get_greeting(name: str) -> str:
        """Build a greeting for name."""
        return f"Hi {name}"

    ai = AIService(ai_config)
    response = ai.invoke([("user", "hi")], tools=[get_greeting])

    assert response == "I couldn't find that information."
    second_call_messages = bound_model.invoke.call_args_list[1].args[0]
    tool_messages = [m for m in second_call_messages if getattr(m, "tool_call_id", None) == "call_1"]
    assert tool_messages[0].content == "Unknown tool: nonexistent"


@patch("app.services.ai_service.ChatOpenAI")
def test_invoke_with_tools_raises_after_max_rounds(mock_chat_openai, ai_config):
    mock_model = mock_chat_openai.return_value
    bound_model = mock_model.bind_tools.return_value

    looping_response = MagicMock()
    looping_response.tool_calls = [{"name": "get_greeting", "args": {}, "id": "call_1"}]
    bound_model.invoke.return_value = looping_response

    @tool
    def get_greeting() -> str:
        """Greets."""
        return "hi"

    ai = AIService(ai_config)
    with pytest.raises(RuntimeError, match="tool-call limit"):
        ai.invoke([("user", "hi")], tools=[get_greeting])


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



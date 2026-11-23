
# AI Service

## Overview

The Greenhouse backend includes a reusable AI service built with LangChain.
The service communicates with configurable OpenAI-compatible LLM APIs, notably Rocky, through the ChatOpenAI integration.
Provider settings are supplied through env variables, allowing providers and models to be changed without editing code

The service supports:

- Text-based prompts
- Multimodal prompts containing text and images
- Configurable API endpoints and models
- Configurable inference settings
- Provider error handling

## Configuration

Configure the following environment variables in the repository root `.env` file:

| Variable | Default | Description |
|---|---|---|
| `AI_BASE_URL` | None | OpenAI-compatible API endpoint |
| `AI_API_KEY` | None | API authentication key |
| `AI_MODEL` | None | Model identifier |
| `AI_TEMPERATURE` | `0.7` | Controls response randomness (0–2) |
| `AI_MAX_TOKENS` | `2048` | Maximum generated tokens |
| `AI_TIMEOUT` | `180` | Request timeout in seconds |

Example:

```env
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=your-api-key
AI_MODEL=your-model-name
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=2048
AI_TIMEOUT=180
```

The AI service is initialized when all three required settings are configured:

- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL`

If these settings are missing, the Flask application remains available, but AI functionality returns 503

## API Endpoint

### Invoke AI

| Method | Path | Authentication |
|---|---|---|
| `POST` | `/api/v1/ai/invoke` | Bearer token required |

The endpoint accepts `multipart/form-data`.

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | Text | Yes | User's prompt |
| `image` | File | No | Optional image attachment |

### Successful Text Request

Example:

```bash
curl -X POST http://localhost:5000/api/v1/ai/invoke \
  -F "prompt=Describe the current greenhouse conditions"
```

Response:

```json
{
  "response": "The greenhouse conditions appear suitable..."
}
```

### Image Request

Images can be uploaded using multipart/form-data

Example:

```bash
curl -X POST http://localhost:5000/api/v1/ai/invoke \
  -F "prompt=Describe the plant in this image" \
  -F "image=@plant.jpg"
```

The endpoint reads the uploaded image and constructs a multimodal LangChain message

### Supported Image Formats

The endpoint currently accepts:

- JPEG (`image/jpeg`)
- PNG (`image/png`)
- WebP (`image/webp`)

Maximum image size: 4 MB

## Error Responses

| HTTP Status | Description |
|---|---|
| `400` | Missing prompt, unsupported image type, or empty image |
| `401` | Authentication required or invalid |
| `413` | Image exceeds the 4 MB limit |
| `502` | AI provider invocation failed |
| `503` | AI service is unavailable |

Errors use the standard API response format:

```json
{
  "error": "AI provider invocation failed"
}
```

## Using the AI Service Internally

The reusable service is registered in Flask application extensions
It can be accessed from a Flask application context:

```python
from flask import current_app
ai_service = current_app.extensions["ai_service"]
response = ai_service.invoke(messages)
```

The `invoke()` method accepts LangChain-compatible messages and returns the response content.

## Tool Calling

`invoke()` takes an optional `tools` argument: a list of LangChain `@tool`-decorated
functions the model can call on its own, instead of the caller pre-loading data into
the prompt. `AIService` binds them to the model and runs the round-trip loop itself
(model responds with a tool call -> the tool runs -> the result goes back to the model
as a `ToolMessage` -> repeat until the model returns a final answer, capped at 5 rounds).
A tool raising an exception doesn't fail the request - the error is reported back to
the model as that tool's result, so it can say it couldn't retrieve the data.

```python
from langchain_core.tools import tool

@tool
def get_greenhouse_zones() -> str:
    """List the greenhouse's zones."""
    return "North, South"

response = current_app.extensions["ai_service"].invoke(
    [("user", "What zones exist?")],
    tools=[get_greenhouse_zones],
)
```

See `app/services/assistant_tools.py` and `app/services/assistant_context.py` for
the Ask assistant's (`POST /api/v1/assistant/chat`) real tools built this way.

## Constructing Image Messages

The `build_image_message()` helper converts image bytes into a base64 data URI

Example:

```python
from flask import current_app
from app.services.ai_service import build_image_message

with open("plant.jpg", "rb") as image_file:
    image_bytes = image_file.read()

message = build_image_message(
    prompt="Describe this plant",
    image_bytes=image_bytes,
    mime_type="image/jpeg",
)

response = current_app.extensions["ai_service"].invoke(
    [message]
)
```

The helper constructs a LangChain `HumanMessage` containing text and an image URL

The image URL follows this format:

```text
data:image/jpeg;base64,<BASE64_ENCODED_IMAGE>
```

This allows compatible vision models to receive image data without requiring a publicly accessible image URL

## Testing

AI service and endpoint tests are located in:
```text
tests/test_ai_service.py
```
Run the tests with:
```bash
pytest tests/test_ai_service.py -v
```
The tests use mocked model responses and do not require a live LLM provider

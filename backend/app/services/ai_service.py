from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError
import base64
from langchain_core.messages import HumanMessage

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4 MB

def build_image_message(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> HumanMessage:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
    ])

def image_from_request_files(files, field="image"):
    image = files.get(field)
    if not image:
        return None, None
    if image.mimetype not in ALLOWED_IMAGE_MIMES:
        raise ValueError("Unsupported image type")
    image_bytes = image.stream.read(MAX_IMAGE_SIZE + 1)
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise ValueError("Image exceeds the 4 MB size limit")
    if not image_bytes:
        raise ValueError("Uploaded image is empty")
    return image_bytes, image.mimetype

class AIService:

    def __init__(self, config):
        required_settings = [
            "AI_BASE_URL",
            "AI_API_KEY",
            "AI_MODEL",
        ]
        for setting in required_settings:
            if not config.get(setting):
                raise ValueError(
                    f"Missing required configuration: {setting}"
                )
        temperature = float(config["AI_TEMPERATURE"])
        max_tokens = int(config["AI_MAX_TOKENS"])
        timeout = int(config["AI_TIMEOUT"])

        if not 0 <= temperature <= 2:
            raise ValueError("AI_TEMPERATURE must be between 0 and 2")
        if max_tokens <= 0:
            raise ValueError("AI_MAX_TOKENS must be positive")
        if timeout <= 0:
            raise ValueError("AI_TIMEOUT must be positive")
        
        self.model = ChatOpenAI(
            base_url=config["AI_BASE_URL"],
            api_key=config["AI_API_KEY"],
            model=config["AI_MODEL"],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            # Force LangChain to use POST /v1/responses
            use_responses_api=True,
            store=False,
        )

    def invoke(self, messages):
        try:
            response = self.model.invoke(messages)
            return response.text
        except APITimeoutError as error:
            raise RuntimeError("LLM request timed out") from error
        except APIConnectionError as error:
            raise RuntimeError("LLM provider is unavailable") from error
        except APIStatusError as error:
            raise RuntimeError(
                f"LLM provider returned status {error.status_code}"
            ) from error 
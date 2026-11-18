from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError
import base64
from langchain_core.messages import HumanMessage

def build_image_message(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> HumanMessage:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
    ])

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
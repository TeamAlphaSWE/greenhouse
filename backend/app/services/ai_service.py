from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError
import base64
from langchain_core.messages import HumanMessage, ToolMessage

# Bounds how many tool-call round trips a single invoke() can take, so a model
# that keeps calling tools instead of answering can't loop forever.
MAX_TOOL_ROUNDS = 5

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

    def invoke(self, messages, tools=None):
        model = self.model.bind_tools(tools) if tools else self.model
        tools_by_name = {t.name: t for t in tools} if tools else {}
        messages = list(messages)

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._call_model(model, messages)
            tool_calls = getattr(response, "tool_calls", None)
            if not isinstance(tool_calls, list) or not tool_calls:
                return response.text

            messages.append(response)
            for call in response.tool_calls:
                messages.append(ToolMessage(
                    content=self._run_tool(tools_by_name, call),
                    tool_call_id=call["id"],
                ))

        raise RuntimeError("Assistant did not produce an answer within the tool-call limit")

    def _call_model(self, model, messages):
        try:
            return model.invoke(messages)
        except APITimeoutError as error:
            raise RuntimeError("LLM request timed out") from error
        except APIConnectionError as error:
            raise RuntimeError("LLM provider is unavailable") from error
        except APIStatusError as error:
            raise RuntimeError(
                f"LLM provider returned status {error.status_code}"
            ) from error

    def _run_tool(self, tools_by_name, call):
        tool = tools_by_name.get(call["name"])
        if tool is None:
            return f"Unknown tool: {call['name']}"
        try:
            return str(tool.invoke(call["args"]))
        except Exception as error:
            # A tool failing (bad args, a DB hiccup, ...) shouldn't fail the
            # whole conversation - tell the model so it can say so, instead.
            return f"Tool '{call['name']}' failed: {error}"
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError
import base64
import json
import re
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# Bounds how many tool-call round trips a single invoke() can take, so a model
# that keeps calling tools instead of answering can't loop forever.
MAX_TOOL_ROUNDS = 5

# Matches a prompted tool-call reply, e.g. TOOL_CALL: get_sensor_status({"sensor_name": "A"})
TOOL_CALL_PATTERN = re.compile(r"TOOL_CALL:\s*(\w+)\((.*)\)", re.DOTALL)


class ToolsUnsupportedError(Exception):
    """Raised internally when the provider rejects the API's native `tools`
    parameter, so invoke() can fall back to prompting for tool calls in
    plain text instead of raising straight to the caller."""

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
        if not tools:
            return self._call_model(self.model, messages).text()

        try:
            return self._invoke_with_native_tools(messages, tools)
        except ToolsUnsupportedError:
            # The provider rejects the API's own `tools` parameter (seen on
            # Rocky's /v1/responses: 400 unsupported_parameter / param
            # "tools"). Fall back to prompting for tool calls in plain text
            # instead. Tried fresh on every call - the moment the provider
            # starts accepting `tools`, this branch stops firing on its own.
            return self._invoke_with_prompted_tools(messages, tools)

    def _invoke_with_native_tools(self, messages, tools):
        model = self.model.bind_tools(tools)
        tools_by_name = {t.name: t for t in tools}
        messages = list(messages)

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._call_model(model, messages)
            tool_calls = getattr(response, "tool_calls", None)
            if not isinstance(tool_calls, list) or not tool_calls:
                return response.text()

            messages.append(response)
            for call in response.tool_calls:
                messages.append(ToolMessage(
                    content=self._run_tool(tools_by_name, call),
                    tool_call_id=call["id"],
                ))

        raise RuntimeError("Assistant did not produce an answer within the tool-call limit")

    def _invoke_with_prompted_tools(self, messages, tools):
        """Same tools, same multi-round behavior as _invoke_with_native_tools,
        but for a provider that won't accept the `tools` parameter at all:
        tools are described in the prompt instead, and a tool call is a
        parsed `TOOL_CALL: name({...})` line in the model's plain-text reply
        rather than a structured response field."""
        tools_by_name = {t.name: t for t in tools}
        messages = self._with_tool_instructions(list(messages), tools)

        for _ in range(MAX_TOOL_ROUNDS):
            text = self._call_model(self.model, messages).text()
            match = TOOL_CALL_PATTERN.search(text)
            if match is None:
                return text

            name, args_text = match.groups()
            try:
                args = json.loads(args_text or "{}")
            except json.JSONDecodeError:
                return text

            messages.append(AIMessage(content=text))
            result = self._run_tool(tools_by_name, {"name": name, "args": args})
            messages.append(HumanMessage(content=f"TOOL_RESULT {name}: {result}"))

        raise RuntimeError("Assistant did not produce an answer within the tool-call limit")

    @staticmethod
    def _with_tool_instructions(messages, tools):
        descriptions = "\n".join(
            f"- {t.name}({', '.join(t.args)}): {' '.join(t.description.split())}"
            for t in tools
        )
        instructions = SystemMessage(content=(
            "You have these tools available:\n" + descriptions + "\n\n"
            "To call one, reply with ONLY this line, nothing else:\n"
            'TOOL_CALL: tool_name({"arg": "value"})\n'
            "Use {} for a tool with no arguments. After you get a tool's "
            "result, you may call another tool the same way, or give your "
            "final answer as plain text."
        ))
        if messages and isinstance(messages[0], SystemMessage):
            return [messages[0], instructions, *messages[1:]]
        return [instructions, *messages]

    def _call_model(self, model, messages):
        try:
            return model.invoke(messages)
        except APITimeoutError as error:
            raise RuntimeError("LLM request timed out") from error
        except APIConnectionError as error:
            raise RuntimeError("LLM provider is unavailable") from error
        except APIStatusError as error:
            if error.status_code == 400 and error.code == "unsupported_parameter" and error.param == "tools":
                raise ToolsUnsupportedError() from error
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
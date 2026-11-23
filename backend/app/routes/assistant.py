from flask import Blueprint, current_app, jsonify, request

from app.services.assistant_prompt import build_messages
from app.services.assistant_tools import ASSISTANT_TOOLS

assistant = Blueprint("assistant", __name__, url_prefix="/api/v1/assistant")

VALID_ROLES = {"user", "assistant"}


@assistant.post("/chat")
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message is required"}), 400

    history = data.get("history", [])
    error = _validate_history(history)
    if error:
        return jsonify({"error": error}), 400

    ai_service = current_app.extensions.get("ai_service")
    if ai_service is None:
        return jsonify({"error": "AI assistant is not configured"}), 503

    messages = build_messages(history, message.strip())

    try:
        answer = ai_service.invoke(messages, tools=ASSISTANT_TOOLS)
    except RuntimeError:
        current_app.logger.exception("Assistant request failed")
        return jsonify({"error": "AI assistant is unavailable"}), 502

    return jsonify({"answer": answer})


def _validate_history(history):
    if not isinstance(history, list):
        return "history must be a list"
    for turn in history:
        if not isinstance(turn, dict):
            return "each history entry must be an object"
        if turn.get("role") not in VALID_ROLES:
            return "each history entry needs a role of 'user' or 'assistant'"
        content = turn.get("content")
        if not isinstance(content, str) or not content.strip():
            return "each history entry needs non-empty content"
    return None

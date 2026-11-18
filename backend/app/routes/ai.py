
from flask import Blueprint, current_app, jsonify, request

from app.services.ai_service import build_image_message
from langchain_core.messages import HumanMessage

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4 MB

ai = Blueprint("ai", __name__, url_prefix="/api/v1/ai")


@ai.post("/invoke")
def invoke_ai():
    ai_service = current_app.extensions.get("ai_service")
    if ai_service is None:
        return jsonify({"error": "AI service is currently unavailable"}), 503
    prompt = request.form.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "A prompt is required"}), 400
    
    image = request.files.get("image")
    if image:
        if image.mimetype not in ALLOWED_IMAGE_MIMES:
            return jsonify({"error": "Unsupported image type"}), 400
        image_bytes = image.stream.read(MAX_IMAGE_SIZE + 1)
        if len(image_bytes) > MAX_IMAGE_SIZE:
            return jsonify({"error": "Image exceeds the 4 MB size limit"}), 413
        if not image_bytes:
            return jsonify({"error": "Uploaded image is empty"}), 400
        messages = [build_image_message(prompt, image_bytes, image.mimetype)]
    else:
        messages = [HumanMessage(content=prompt)]
    try:
        response = ai_service.invoke(messages)
    except RuntimeError:
        current_app.logger.exception("AI provider invocation failed")
        return jsonify({"error": "AI provider invocation failed"}), 502
    return jsonify({"response": response}), 200


from flask import Blueprint, current_app, g, jsonify, request
from pymongo.errors import PyMongoError

from app.auth import require_auth
from app.repositories.users import users as user_repository

settings = Blueprint("settings", __name__, url_prefix="/api/v1/settings")

DEFAULT_SETTINGS = {
    "temperature_unit": "°C",
    "alerts_enabled": True,
    "email_alerts_enabled": False,
    "notification_email": None,
}


@settings.get("")
@require_auth
def get_settings():
    return jsonify({"settings": g.user.get("settings") or DEFAULT_SETTINGS})


@settings.put("")
@require_auth
def update_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    temperature_unit = data.get("temperature_unit")
    alerts_enabled = data.get("alerts_enabled")
    email_alerts_enabled = data.get("email_alerts_enabled")
    notification_email = data.get("notification_email")

    if temperature_unit not in ("°C", "°F"):
        return jsonify({"error": "temperature_unit must be '°C' or '°F'"}), 400
    if not isinstance(alerts_enabled, bool) or not isinstance(email_alerts_enabled, bool):
        return jsonify({"error": "alerts_enabled and email_alerts_enabled must be booleans"}), 400
    if notification_email is not None and not isinstance(notification_email, str):
        return jsonify({"error": "notification_email must be a string or null"}), 400
    if email_alerts_enabled and not notification_email:
        return jsonify({"error": "notification_email is required when email_alerts_enabled is true"}), 400

    new_settings = {
        "temperature_unit": temperature_unit,
        "alerts_enabled": alerts_enabled,
        "email_alerts_enabled": email_alerts_enabled,
        "notification_email": notification_email,
    }

    try:
        user_repository.update(g.user["id"], {"settings": new_settings})
    except PyMongoError:
        current_app.logger.exception("Failed to update settings")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"settings": new_settings})

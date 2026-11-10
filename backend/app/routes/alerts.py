from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from app.repositories.alerts import alerts as alert_repository

alerts = Blueprint("alerts", __name__, url_prefix="/api/v1/alerts")

DEFAULT_LIMIT = 50


@alerts.get("")
def list_alerts():
    limit = request.args.get("limit", str(DEFAULT_LIMIT))
    if not limit.isdigit() or int(limit) < 1:
        return jsonify({"error": "limit must be a positive integer"}), 400
    limit = int(limit)

    try:
        alert_list = alert_repository.find(sort=[("created_at", -1)], limit=limit)
    except PyMongoError:
        current_app.logger.exception("Failed to load alerts")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({
        "alerts": alert_list,
        "total": len(alert_list),
    })

from flask import Blueprint, jsonify

health = Blueprint("health", __name__, url_prefix="/api/v1")

@health.get("/health")
def get_health():
    return jsonify({
        "status": "ok"
    })
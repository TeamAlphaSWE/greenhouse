from flask import Blueprint, current_app, jsonify
from pymongo.errors import PyMongoError

from app.repositories.zones import zones as zone_repository

zones = Blueprint("zones", __name__, url_prefix="/api/v1/zones")


@zones.get("")
def list_zones():
    try:
        zone_list = zone_repository.find(sort=[("name", 1)])
    except PyMongoError:
        current_app.logger.exception("Failed to load zones")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({
        "zones": zone_list,
        "total": len(zone_list),
    })
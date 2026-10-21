from flask import Blueprint, current_app, jsonify
from pymongo.errors import PyMongoError

from app.repositories.sensors import sensors as sensor_repository

sensors = Blueprint("sensors", __name__, url_prefix="/api/v1/sensors")


@sensors.get("")
def list_sensors():
    try:
        sensor_list = sensor_repository.find(sort=[("name", 1)])
    except PyMongoError:
        current_app.logger.exception("Failed to load sensors")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({
        "sensors": sensor_list,
        "total": len(sensor_list),
    })
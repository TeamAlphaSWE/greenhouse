from flask import Blueprint, current_app, jsonify
from pymongo.errors import PyMongoError

from app.repositories.sensor_data import sensor_data as sensor_data_repository

sensor_data = Blueprint("sensor_data", __name__, url_prefix="/api/v1/sensor_data")


@sensor_data.get("/<sensor_id>")
def list_sensor_data(sensor_id):
    try:
        readings = sensor_data_repository.find_by_sensor_id(sensor_id)
    except PyMongoError:
        current_app.logger.exception("Failed to load sensor data")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({
        "sensor_data": readings,
        "total": len(readings),
    })

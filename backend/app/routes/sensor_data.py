from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError
from app.repositories.sensor_data import sensor_data as sensor_data_repository
from app.repositories.sensors import sensors as sensor_repository

sensor_data = Blueprint("sensor_data", __name__, url_prefix="/api/v1/sensor_data")


@sensor_data.get("/<sensor_id>")
def list_sensor_data(sensor_id):
    if sensor_data_repository._to_object_id(sensor_id) is None:
        return jsonify({"error": "Invalid sensor_id"}), 400

    try:
        readings = sensor_data_repository.find_by_sensor_id(sensor_id)
    except PyMongoError:
        current_app.logger.exception("Failed to load sensor data")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({
        "sensor_data": readings,
        "total": len(readings),
    })
    
@sensor_data.post("")
def create_sensor_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    error = _validate_reading(data)
    if error:
        return jsonify({"error": error}), 400

    values = [{"type": v["type"], "value": v["value"]} for v in data["values"]]

    try:
        sensor = sensor_repository.find_by_hardware_id(data["hardware_id"])
        if sensor is None:
            sensor = sensor_repository.create_pending(data["hardware_id"])
        reading = sensor_data_repository.create_reading(sensor["id"], values)
    except PyMongoError:
        current_app.logger.exception("Failed to save sensor data")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"sensor_data": {"id": reading["id"]}}), 201


def _validate_reading(data):
    hardware_id = data.get("hardware_id")
    if not isinstance(hardware_id, str) or not hardware_id:
        return "hardware_id is required"

    values = data.get("values")
    if not isinstance(values, list) or not values:
        return "values is required and must be a non-empty list"

    for item in values:
        if not isinstance(item, dict):
            return "each value must be an object"
        if not isinstance(item.get("type"), str) or not item["type"]:
            return "each value needs a type"
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "each value needs a numeric value"

    return None

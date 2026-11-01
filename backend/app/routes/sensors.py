from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from app.repositories.sensors import sensors as sensor_repository
from app.repositories.zones import zones as zone_repository

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


@sensors.patch("/<sensor_id>")
def activate_sensor(sensor_id):
    if sensor_repository._to_object_id(sensor_id) is None:
        return jsonify({"error": "Invalid sensor id"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required"}), 400

    area_oid = zone_repository._to_object_id(data.get("area_id"))
    if area_oid is None:
        return jsonify({"error": "area_id is required"}), 400

    try:
        sensor = sensor_repository.get(sensor_id)
        if sensor is None:
            return jsonify({"error": "Sensor not found"}), 404

        zone = zone_repository.find_by_area_id(area_oid)
        if zone is None:
            return jsonify({"error": "area_id does not match any zone's area"}), 400

        updated = sensor_repository.update(sensor_id, {
            "name": name.strip(),
            "area_id": area_oid,
            "zone_id": zone_repository._to_object_id(zone["id"]),
            "status": "active",
            "updated_at": datetime.now(timezone.utc),
        })
    except PyMongoError:
        current_app.logger.exception("Failed to activate sensor")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"sensor": updated})
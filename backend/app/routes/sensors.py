from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from app.repositories.sensor_data import sensor_data as sensor_data_repository
from app.repositories.sensors import sensors as sensor_repository
from app.sensor_health import sensor_health, summarize

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

@sensors.get("/health")
def get_sensor_health():
    query = {}
    zone_id = request.args.get("zone_id")
    if zone_id is not None:
        if not ObjectId.is_valid(zone_id):
            return jsonify({"error": "Invalid zone_id"}), 400
        query["zone_id"] = ObjectId(zone_id)

    try:
        sensor_list = sensor_repository.find(query, sort=[("name", 1)])
        latest = sensor_data_repository.latest_by_sensor(
            [ObjectId(s["id"]) for s in sensor_list]
        )
    except PyMongoError:
        current_app.logger.exception("Failed to load sensor health")
        return jsonify({"error": "Unexpected server error"}), 500

    health = [sensor_health(s, latest.get(s["id"]), current_app.config) for s in sensor_list]

    return jsonify({
        "summary": summarize(health),
        "sensors": health,
        "total": len(health),
    })
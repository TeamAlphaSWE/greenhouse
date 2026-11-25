from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from app.area_overview import build_overview, summarize
from app.repositories.sensor_data import sensor_data as sensor_data_repository
from app.repositories.sensors import sensors as sensor_repository
from app.repositories.zones import zones as zone_repository

areas = Blueprint("areas", __name__, url_prefix="/api/v1/areas")


@areas.get("/overview")
def areas_overview():
    try:
        zone_list = zone_repository.find(sort=[("name", 1)])
        sensor_list = [s for s in sensor_repository.find() if s.get("area_id")]
        latest = sensor_data_repository.latest_by_sensor(
            [sensor_repository._to_object_id(s["id"]) for s in sensor_list]
        )
    except PyMongoError:
        current_app.logger.exception("Failed to load area overview")
        return jsonify({"error": "Unexpected server error"}), 500

    latest_by_area = {s["area_id"]: latest.get(s["id"]) for s in sensor_list}
    overview = build_overview(zone_list, latest_by_area, current_app.config, datetime.now(timezone.utc))

    return jsonify({
        "zones": overview,
        "summary": summarize(overview),
    })


MEASUREMENTS = ("temperature", "humidity")


@areas.patch("/<area_id>/target_conditions")
def update_target_conditions(area_id):
    area_oid = zone_repository._to_object_id(area_id)
    if area_oid is None:
        return jsonify({"error": "Invalid area id"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    error = _validate_target_conditions(data)
    if error:
        return jsonify({"error": error}), 400

    conditions = {
        measurement: {"min": limits["min"], "max": limits["max"]}
        for measurement, limits in data.items()
    }

    try:
        zone = zone_repository.set_target_conditions(area_oid, conditions)
    except PyMongoError:
        current_app.logger.exception("Failed to update target conditions")
        return jsonify({"error": "Unexpected server error"}), 500

    if zone is None:
        return jsonify({"error": "Area not found"}), 404

    area = next(a for a in zone["areas"] if a.get("id") == area_oid)
    return jsonify({"area": area})


def _validate_target_conditions(data):
    if not data:
        return "temperature or humidity is required"

    for measurement, limits in data.items():
        if measurement not in MEASUREMENTS:
            return f"Unknown measurement: {measurement}"
        if not isinstance(limits, dict) or set(limits) != {"min", "max"}:
            return f"{measurement} needs both min and max"
        low, high = limits["min"], limits["max"]
        if not _is_integer(low) or not _is_integer(high):
            return f"{measurement} min and max must be integers"
        if low >= high:
            return f"{measurement} min must be less than max"

    return None


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)

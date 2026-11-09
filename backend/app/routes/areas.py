from flask import Blueprint, current_app, jsonify
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
    overview = build_overview(zone_list, latest_by_area)

    return jsonify({
        "zones": overview,
        "summary": summarize(overview),
    })

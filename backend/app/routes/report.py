from flask import Blueprint, request, jsonify
from datetime import datetime
from app.repositories.sensor_data import sensor_data as sensor_data_repository
from app.repositories.alerts import alerts as alerts_repository
from app.repositories.sensors import sensors as sensor_repository
from app.repositories.zones import zones as zone_repository
import statistics

report = Blueprint("report", __name__, url_prefix="/api/v1/report")

NO_DATA_MESSAGE = "No data for this time range can be reported, please choose another time to report on."


def _reading_value(reading, type_name):
    return next(
        (v.get("value") for v in reading.get("values", []) if v.get("type") == type_name),
        None,
    )


def _summarize(report_filter, alert_filter):
    """Temperature/humidity min/max/avg plus alert count for one filter pair."""
    readings = sensor_data_repository.find(report_filter)
    num_alerts = alerts_repository.collection.count_documents(alert_filter)

    if not readings:
        return {"report": {}, "alerts": 0, "message": NO_DATA_MESSAGE}

    temperatures = [t for t in (_reading_value(r, "temperature") for r in readings) if t is not None]
    humidities = [h for h in (_reading_value(r, "humidity") for r in readings) if h is not None]

    return {
        "report": {
            "temperature": {
                "min": round(min(temperatures), 2) if temperatures else None,
                "max": round(max(temperatures), 2) if temperatures else None,
                "avg": round(statistics.mean(temperatures), 2) if temperatures else None,
            },
            "humidity": {
                "min": round(min(humidities), 2) if humidities else None,
                "max": round(max(humidities), 2) if humidities else None,
                "avg": round(statistics.mean(humidities), 2) if humidities else None,
            },
        },
        "alerts": num_alerts,
    }


def _sensor_ids_in_zone(zone_oid):
    return [
        sensor_repository._to_object_id(s["id"])
        for s in sensor_repository.find({"zone_id": zone_oid})
    ]


@report.post("")
def generate_report():
    """Collect data once report_api from frontend sends it to backend"""
    data = request.get_json()
    start = data.get('start')
    end = data.get('end')
    zone_info = data.get('zone')
    sensor_info = data.get('sensor')

    """Have to convert date recieved from frontend to match database for comparision"""
    start_data = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_data = datetime.fromisoformat(end.replace("Z", "+00:00"))
    time_filter = {"$gte": start_data, "$lte": end_data}

    zone_info = zone_info.get("id") if isinstance(zone_info, dict) else zone_info
    sensor_info = sensor_info.get("id") if isinstance(sensor_info, dict) else sensor_info
    zone_oid = zone_repository._to_object_id(zone_info) if zone_info and zone_info != "All" else None
    sensor_oid = sensor_repository._to_object_id(sensor_info) if sensor_info and sensor_info != "All" else None

    try:
        """A specific sensor is the most precise filter there is."""
        if sensor_oid is not None:
            result = _summarize(
                {"timestamp": time_filter, "sensor_id": sensor_oid},
                {"created_at": time_filter, "sensor_id": sensor_oid},
            )
            return jsonify({
                "period": {"start": start, "end": end},
                "area": {"zone": zone_info, "sensor": sensor_info},
                **result,
            }), 200

        """A specific zone: sensor_data has no zone_id of its own, so go
        through the sensors assigned to that zone instead."""
        if zone_oid is not None:
            result = _summarize(
                {"timestamp": time_filter, "sensor_id": {"$in": _sensor_ids_in_zone(zone_oid)}},
                {"created_at": time_filter, "zone_id": zone_oid},
            )
            return jsonify({
                "period": {"start": start, "end": end},
                "area": {"zone": zone_info, "sensor": sensor_info},
                **result,
            }), 200

        """Neither picked ("All"): pooling every sensor in the greenhouse into
        one number hides which zone actually has a problem, so report one
        summary per zone instead."""
        breakdown = []
        for zone in zone_repository.find():
            this_zone_oid = zone_repository._to_object_id(zone["id"])
            result = _summarize(
                {"timestamp": time_filter, "sensor_id": {"$in": _sensor_ids_in_zone(this_zone_oid)}},
                {"created_at": time_filter, "zone_id": this_zone_oid},
            )
            breakdown.append({"zone": zone["id"], "zone_name": zone.get("name"), **result})

        return jsonify({
            "period": {"start": start, "end": end},
            "zones": breakdown,
        }), 200
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

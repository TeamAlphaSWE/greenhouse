from flask import Blueprint, request, jsonify
from datetime import datetime
from app.repositories.sensor_data import sensor_data as sensor_data_repository
from app.repositories.alerts import alerts as alerts_repository
import statistics
report = Blueprint("report", __name__, url_prefix="/api/v1/report")

@report.post('/')
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

    report_filter = {
        "timestamp":{"$gte":start_data, "$lte":end_data}
    }
    alert_filter = {
        "created_at":{"$gte":start_data, "$lte":end_data}
    }

    zone_info = zone_info.get("id") if isinstance(zone_info, dict) else zone_info
    sensor_info = sensor_info.get("id") if isinstance(sensor_info, dict) else sensor_info
    """If all is selected it would just check all zones/sensors and count number alerts collected during specified timeframe"""
    if zone_info and zone_info != "All":
        report_filter["zone_id"] = zone_info
    if sensor_info and sensor_info != "All":
        report_filter["sensor_id"] = sensor_info

    """Error state"""
    try:
        reading = list(sensor_data_repository.find(report_filter))
        """Gather temperature/humidity data from time range"""
        temperatures = [r["temperature"] for r in reading if r.get("temperature") is not None]
        humidities = [r["humidity"] for r in reading if r.get("humidity") is not None]

        if zone_info and zone_info != "All":
            alert_filter["zone_id"] = zone_info
        if sensor_info and sensor_info != "All":
            alert_filter["sensor_id"] = sensor_info

        num_alerts = alerts_repository.collection.count_documents(alert_filter)
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

    """Empty data case (a zone/sensor has no data to provide)"""
    if not reading:
        return jsonify({
            "period": {"start": start, "end": end},
            "area": {"zone": zone_info, "sensor": sensor_info},
            "report": {},
            "alerts": 0,
            "message": "No data for this time range can be reported, please choose another time to report on."
        }), 200

    """Temperature and Humidity Statistics: provides average, min, and max"""
    summary = {
        "temperature": {
            "min": round(min(temperatures), 2) if temperatures else None,
            "max": round(max(temperatures), 2) if temperatures else None,
            "avg": round(statistics.mean(temperatures), 2) if temperatures else None
        },

        "humidity": {
            "min": round(min(humidities), 2) if humidities else None,
            "max": round(max(humidities), 2) if humidities else None,
            "avg": round(statistics.mean(humidities), 2) if humidities else None
        }
    }

    return jsonify({
        "period": {"start": start, "end": end},
        "area": {"zone": zone_info, "sensor": sensor_info},
        "report": summary,
        "alerts": num_alerts,
    }), 200
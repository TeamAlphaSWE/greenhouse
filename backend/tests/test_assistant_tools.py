import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.db import get_collection
from app.services.assistant_tools import get_current_conditions, get_sensor_history, get_sensor_status

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)


def seed_zone_with_area(app, area_id):
    with app.app_context():
        get_collection("zones").insert_one({
            "name": "North",
            "areas": [{
                "id": area_id,
                "name": "Tomatoes",
                "target_conditions": {"temperature": {"min": 18, "max": 26}},
            }],
        })


def seed_sensor(app, area_id=None, name="Sensor A"):
    with app.app_context():
        return get_collection("sensors").insert_one({
            "name": name,
            "hardware_id": name.lower().replace(" ", "-"),
            "area_id": area_id,
        }).inserted_id


def seed_reading(app, sensor_id, at, temperature=22.0):
    with app.app_context():
        get_collection("sensor_data").insert_one({
            "sensor_id": sensor_id,
            "timestamp": at,
            "values": [{"type": "temperature", "value": temperature}],
        })


def test_get_current_conditions_returns_matching_area(app):
    area_id = ObjectId()
    seed_zone_with_area(app, area_id)

    with app.app_context():
        result = get_current_conditions.invoke({"area_name": "Tomatoes"})

    areas = json.loads(result)
    assert areas[0]["name"] == "Tomatoes"


def test_get_current_conditions_no_match_returns_message(app):
    with app.app_context():
        result = get_current_conditions.invoke({"area_name": "Nope"})

    assert result == "No area found matching 'Nope'."


def test_get_current_conditions_none_configured_returns_message(app):
    with app.app_context():
        result = get_current_conditions.invoke({})

    assert result == "No areas configured."


def test_get_sensor_status_returns_matching_sensor(app):
    seed_sensor(app, name="Sensor A")
    seed_sensor(app, name="Sensor B")

    with app.app_context():
        result = get_sensor_status.invoke({"sensor_name": "Sensor B"})

    sensors = json.loads(result)
    assert len(sensors) == 1
    assert sensors[0]["name"] == "Sensor B"


def test_get_sensor_status_no_match_returns_message(app):
    with app.app_context():
        result = get_sensor_status.invoke({"sensor_name": "Nope"})

    assert result == "No sensor found matching 'Nope'."


def test_get_sensor_status_none_found_returns_message(app):
    with app.app_context():
        result = get_sensor_status.invoke({})

    assert result == "No sensors found."


def test_get_sensor_history_unknown_sensor_returns_message(app):
    with app.app_context():
        result = get_sensor_history.invoke({"sensor_name": "Nope"})

    assert result == "No sensor named 'Nope' found."


def test_get_sensor_history_no_readings_returns_message(app):
    seed_sensor(app, name="Sensor A")

    with app.app_context():
        result = get_sensor_history.invoke({"sensor_name": "Sensor A"})

    assert result == "'Sensor A' has no readings in the last 24 hours."


def test_get_sensor_history_returns_stats(app):
    sensor_id = seed_sensor(app, name="Sensor A")
    seed_reading(app, sensor_id, datetime.now(timezone.utc) - timedelta(minutes=5), temperature=22.0)

    with app.app_context():
        result = get_sensor_history.invoke({"sensor_name": "Sensor A"})

    stats = json.loads(result)
    assert stats["temperature"] == {"min": 22.0, "max": 22.0, "avg": 22.0}

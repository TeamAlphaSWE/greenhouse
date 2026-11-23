from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.db import get_collection
from app.services.assistant_context import current_conditions, sensor_history, sensor_status

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)


def seed_zone_with_area(app, area_id, temperature_min=18, temperature_max=26):
    with app.app_context():
        get_collection("zones").insert_one({
            "name": "North",
            "areas": [{
                "id": area_id,
                "name": "Tomatoes",
                "target_conditions": {"temperature": {"min": temperature_min, "max": temperature_max}},
            }],
        })


def seed_sensor(app, area_id=None, name="Sensor A"):
    with app.app_context():
        return get_collection("sensors").insert_one({
            "name": name,
            "hardware_id": name.lower().replace(" ", "-"),
            "area_id": area_id,
        }).inserted_id


def seed_reading(app, sensor_id, at, temperature=22.0, humidity=55.0):
    with app.app_context():
        get_collection("sensor_data").insert_one({
            "sensor_id": sensor_id,
            "timestamp": at,
            "values": [
                {"type": "temperature", "value": temperature},
                {"type": "humidity", "value": humidity},
            ],
        })


def test_current_conditions_empty(app):
    with app.app_context():
        assert current_conditions() == []


def test_current_conditions_reflects_in_range_reading(app):
    area_id = ObjectId()
    seed_zone_with_area(app, area_id)
    sensor_id = seed_sensor(app, area_id=area_id)
    seed_reading(app, sensor_id, NOW - timedelta(minutes=5), temperature=22.0, humidity=55.0)

    with app.app_context():
        areas = current_conditions()

    assert len(areas) == 1
    assert areas[0]["name"] == "Tomatoes"
    assert areas[0]["zone"] == "North"
    assert areas[0]["state"] == "normal"
    assert areas[0]["temperature"] == 22.0


def test_current_conditions_filters_by_area_name(app):
    area_id = ObjectId()
    seed_zone_with_area(app, area_id)

    with app.app_context():
        assert current_conditions("Tomatoes") != []
        assert current_conditions("tomatoes") != []
        assert current_conditions("Peppers") == []


def test_current_conditions_handles_area_with_no_sensor(app):
    area_id = ObjectId()
    seed_zone_with_area(app, area_id)

    with app.app_context():
        areas = current_conditions()

    assert areas[0]["state"] == "offline_unknown"
    assert areas[0]["temperature"] is None


def test_sensor_status_filters_by_name(app):
    seed_sensor(app, name="Sensor A")
    seed_sensor(app, name="Sensor B")

    with app.app_context():
        from flask import current_app
        result = sensor_status("Sensor B", current_app.config)

    assert len(result) == 1
    assert result[0]["name"] == "Sensor B"


def test_sensor_status_reflects_no_data(app):
    seed_sensor(app, name="Sensor A")

    with app.app_context():
        from flask import current_app
        result = sensor_status(config=current_app.config)

    assert result[0]["state"] == "no_data"


def test_sensor_history_unknown_sensor_returns_none(app):
    with app.app_context():
        assert sensor_history("Nonexistent") is None


def test_sensor_history_no_readings_returns_empty(app):
    seed_sensor(app, name="Sensor A")

    with app.app_context():
        assert sensor_history("Sensor A") == {}


def test_sensor_history_excludes_old_readings(app):
    sensor_id = seed_sensor(app, name="Sensor A")
    seed_reading(app, sensor_id, NOW - timedelta(hours=25), temperature=10.0)
    seed_reading(app, sensor_id, NOW - timedelta(hours=1), temperature=22.0)

    with app.app_context():
        stats = sensor_history("Sensor A", hours=24, now=NOW)

    assert stats["temperature"] == {"min": 22.0, "max": 22.0, "avg": 22.0}


def test_sensor_history_computes_min_max_avg(app):
    sensor_id = seed_sensor(app, name="Sensor A")
    seed_reading(app, sensor_id, NOW - timedelta(hours=3), temperature=20.0)
    seed_reading(app, sensor_id, NOW - timedelta(hours=2), temperature=24.0)
    seed_reading(app, sensor_id, NOW - timedelta(hours=1), temperature=22.0)

    with app.app_context():
        stats = sensor_history("Sensor A", hours=24, now=NOW)

    assert stats["temperature"] == {"min": 20.0, "max": 24.0, "avg": 22.0}


def test_sensor_history_custom_window(app):
    sensor_id = seed_sensor(app, name="Sensor A")
    seed_reading(app, sensor_id, NOW - timedelta(hours=3), temperature=20.0)

    with app.app_context():
        assert sensor_history("Sensor A", hours=1, now=NOW) == {}
        assert sensor_history("Sensor A", hours=4, now=NOW) != {}

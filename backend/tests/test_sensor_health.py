from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.db import get_collection
from app.repositories.sensors import sensors


def minutes_ago(minutes):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def add_sensor(app, name, zone_id=None, **fields):
    with app.app_context():
        doc = {"name": name, "hardware_id": name.lower(), "zone_id": zone_id, **fields}
        return get_collection("sensors").insert_one(doc).inserted_id


def add_reading(app, sensor_id, at, battery=80):
    with app.app_context():
        get_collection("sensor_data").insert_one({
            "sensor_id": sensor_id,
            "timestamp": at,
            "values": [
                {"type": "temperature", "value": 23.4},
                {"type": "battery", "value": battery},
            ],
        })


def test_sensor_health_empty(client):
    response = client.get("/api/v1/sensors/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "summary": {"total": 0, "reporting": 0, "stale": 0, "no_data": 0, "low_battery": 0},
        "sensors": [],
        "total": 0,
    }


def test_sensor_health_states_and_summary(app, client):
    fresh = add_sensor(app, "A")
    old = add_sensor(app, "B")
    add_sensor(app, "C")  # never reported
    add_reading(app, fresh, minutes_ago(300), battery=90)
    add_reading(app, fresh, minutes_ago(5), battery=14)  # latest wins
    add_reading(app, old, minutes_ago(300), battery=76)

    body = client.get("/api/v1/sensors/health").get_json()
    by_name = {s["name"]: s for s in body["sensors"]}

    assert body["summary"] == {"total": 3, "reporting": 1, "stale": 1, "no_data": 1, "low_battery": 1}
    assert by_name["A"]["state"] == "reporting"
    assert by_name["A"]["battery"] == 14
    assert by_name["A"]["low_battery"] is True
    assert by_name["A"]["minutes_since_last_seen"] == 5
    assert by_name["B"]["state"] == "stale"
    assert by_name["C"]["state"] == "no_data"
    assert by_name["C"]["last_seen"] is None
    assert by_name["C"]["battery"] is None


def test_sensor_health_uses_per_sensor_interval(app, client):
    usb = add_sensor(app, "USB", report_interval_minutes=5)
    add_reading(app, usb, minutes_ago(47))

    body = client.get("/api/v1/sensors/health").get_json()

    assert body["sensors"][0]["state"] == "stale"


def test_sensor_health_filters_by_zone(app, client):
    zone_b = ObjectId()
    add_sensor(app, "In B", zone_id=zone_b)
    add_sensor(app, "Elsewhere", zone_id=ObjectId())

    body = client.get(f"/api/v1/sensors/health?zone_id={zone_b}").get_json()

    assert [s["name"] for s in body["sensors"]] == ["In B"]


def test_sensor_health_invalid_zone_id_returns_400(client):
    response = client.get("/api/v1/sensors/health?zone_id=not-an-id")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid zone_id"}


def test_sensor_health_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(sensors, "find", fail)

    response = client.get("/api/v1/sensors/health")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}
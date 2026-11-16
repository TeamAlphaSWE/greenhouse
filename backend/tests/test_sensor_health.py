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
    values = [{"type": "temperature", "value": 23.4}]
    if battery is not None:
        values.append({"type": "battery", "value": battery})
    with app.app_context():
        get_collection("sensor_data").insert_one({
            "sensor_id": sensor_id,
            "timestamp": at,
            "values": values,
        })


def test_sensor_health_empty(client):
    response = client.get("/api/v1/sensors/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "summary": {
            "total": 0, "reporting": 0, "no_data": 0, "low_battery": 0,
            "stale": 0, "healthy": 0, "warning": 0, "unknown": 0,
        },
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

    assert body["summary"] == {
        "total": 3, "reporting": 2, "no_data": 1, "low_battery": 1,
        "stale": 1, "healthy": 0, "warning": 2, "unknown": 1,
    }
    assert by_name["A"]["state"] == "reporting"
    assert by_name["A"]["battery"] == 14
    assert by_name["A"]["low_battery"] is True
    assert by_name["A"]["minutes_since_last_seen"] == 5
    assert by_name["B"]["state"] == "reporting"
    assert by_name["B"]["minutes_since_last_seen"] == 300    
    assert by_name["C"]["state"] == "no_data"
    assert by_name["C"]["last_seen"] is None
    assert by_name["C"]["battery"] is None


def test_sensor_health_returns_zone_and_area(app, client):
    zone_id, area_id = ObjectId(), ObjectId()
    add_sensor(app, "A", zone_id=zone_id, area_id=area_id)

    sensor = client.get("/api/v1/sensors/health").get_json()["sensors"][0]

    assert sensor["zone_id"] == str(zone_id)
    assert sensor["area_id"] == str(area_id)

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


def _health_by_name(client):
    return {s["name"]: s for s in client.get("/api/v1/sensors/health").get_json()["sensors"]}


def test_sensor_health_recent_reading_with_battery_is_healthy(app, client):
    sensor = add_sensor(app, "A")
    add_reading(app, sensor, minutes_ago(10), battery=80)

    health = _health_by_name(client)["A"]

    assert health["status"] == "healthy"
    assert health["stale"] is False
    assert health["low_battery"] is False


def test_sensor_health_stale_after_interval_times_factor(app, client):
    on_time = add_sensor(app, "On time")
    late = add_sensor(app, "Late")
    add_reading(app, on_time, minutes_ago(240))
    add_reading(app, late, minutes_ago(241))

    health = _health_by_name(client)

    assert health["On time"]["stale"] is False
    assert health["On time"]["status"] == "healthy"
    assert health["Late"]["stale"] is True
    assert health["Late"]["status"] == "warning"


def test_sensor_health_stale_threshold_follows_config(app, client):
    app.config["SENSOR_REPORT_INTERVAL_MINUTES"] = 5
    app.config["SENSOR_STALE_FACTOR"] = 2
    sensor = add_sensor(app, "A")
    add_reading(app, sensor, minutes_ago(11))

    assert _health_by_name(client)["A"]["stale"] is True


def test_sensor_health_low_battery_is_warning(app, client):
    low = add_sensor(app, "Low")
    at_limit = add_sensor(app, "At limit")
    add_reading(app, low, minutes_ago(5), battery=19)
    add_reading(app, at_limit, minutes_ago(5), battery=20)

    health = _health_by_name(client)

    assert health["Low"]["status"] == "warning"
    assert health["At limit"]["status"] == "healthy"


def test_sensor_health_missing_data_is_unknown_not_healthy(app, client):
    no_battery = add_sensor(app, "No battery")
    add_sensor(app, "Never reported")
    add_reading(app, no_battery, minutes_ago(5), battery=None)

    health = _health_by_name(client)

    assert health["No battery"]["status"] == "unknown"
    assert health["No battery"]["battery"] is None
    assert health["Never reported"]["status"] == "unknown"
    assert health["Never reported"]["stale"] is False


def test_sensor_health_stale_without_battery_is_warning(app, client):
    sensor = add_sensor(app, "A")
    add_reading(app, sensor, minutes_ago(500), battery=None)

    assert _health_by_name(client)["A"]["status"] == "warning"

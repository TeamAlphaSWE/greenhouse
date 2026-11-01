from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.db import get_collection
from app.repositories.sensors import sensors


def test_list_sensors_empty(client):
    response = client.get("/api/v1/sensors")

    assert response.status_code == 200
    assert response.get_json() == {"sensors": [], "total": 0}


def test_list_sensors(app, client):
    with app.app_context():
        get_collection("sensors").insert_many([
            {"name": "Sensor_1"},
            {"name": "Sensor_2"},
            {"name": "Sensor_3"},
            {"name": "Sensor_4"},
        ])

    response = client.get("/api/v1/sensors")
    body = response.get_json()


    assert response.status_code == 200
    assert body["total"] == 4
    assert [s["name"] for s in body["sensors"]] == [
        "Sensor_1", "Sensor_2", "Sensor_3", "Sensor_4",
    ]
    assert all(isinstance(s["id"], str) for s in body["sensors"])


def test_list_sensors_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(sensors, "find", fail)

    response = client.get("/api/v1/sensors")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}


def _insert_pending_sensor(app):
    with app.app_context():
        return get_collection("sensors").insert_one({
            "hardware_id": "shellyhtg3-e4b3233085e8",
            "status": "pending",
            "created_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        }).inserted_id


def _insert_zone_with_area(app, area_id):
    with app.app_context():
        get_collection("zones").insert_one({
            "name": "Zone 1",
            "description": "Test zone",
            "status": "active",
            "areas": [{
                "id": area_id,
                "name": "Area 1",
                "status": "active",
                "target_conditions": {
                    "humidity": {"min": 40, "max": 60},
                    "temperature": {"min": 18, "max": 26},
                },
            }],
        })


def test_activate_sensor(app, client):
    area_id = ObjectId()
    sensor_id = _insert_pending_sensor(app)
    _insert_zone_with_area(app, area_id)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={"name": "Flower Bed 1", "area_id": str(area_id)},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["sensor"]["status"] == "active"
    assert body["sensor"]["name"] == "Flower Bed 1"
    assert body["sensor"]["area_id"] == str(area_id)
    assert isinstance(body["sensor"]["zone_id"], str)

    with app.app_context():
        doc = get_collection("sensors").find_one({"_id": sensor_id})

    assert doc["status"] == "active"
    assert doc["area_id"] == area_id
    assert isinstance(doc["zone_id"], ObjectId)
    assert doc["updated_at"] > datetime(2026, 10, 1)


def test_activate_sensor_missing_name_returns_400(app, client):
    area_id = ObjectId()
    sensor_id = _insert_pending_sensor(app)
    _insert_zone_with_area(app, area_id)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={"area_id": str(area_id)},
    )

    assert response.status_code == 400


def test_activate_sensor_empty_name_returns_400(app, client):
    area_id = ObjectId()
    sensor_id = _insert_pending_sensor(app)
    _insert_zone_with_area(app, area_id)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={"name": "   ", "area_id": str(area_id)},
    )

    assert response.status_code == 400


def test_activate_sensor_malformed_area_id_returns_400(app, client):
    sensor_id = _insert_pending_sensor(app)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={"name": "Flower Bed 1", "area_id": "not-an-id"},
    )

    assert response.status_code == 400


def test_activate_sensor_unowned_area_id_returns_400(app, client):
    sensor_id = _insert_pending_sensor(app)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={"name": "Flower Bed 1", "area_id": str(ObjectId())},
    )

    assert response.status_code == 400


def test_activate_sensor_malformed_sensor_id_returns_400(client):
    response = client.patch(
        "/api/v1/sensors/not-an-id",
        json={"name": "Flower Bed 1", "area_id": str(ObjectId())},
    )

    assert response.status_code == 400


def test_activate_sensor_unknown_sensor_id_returns_404(app, client):
    area_id = ObjectId()
    _insert_zone_with_area(app, area_id)

    response = client.patch(
        f"/api/v1/sensors/{ObjectId()}",
        json={"name": "Flower Bed 1", "area_id": str(area_id)},
    )

    assert response.status_code == 404


def test_activate_sensor_invalid_json_returns_400(app, client):
    sensor_id = _insert_pending_sensor(app)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_activate_sensor_database_error_returns_500(app, client, monkeypatch):
    area_id = ObjectId()
    sensor_id = _insert_pending_sensor(app)
    _insert_zone_with_area(app, area_id)

    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(sensors, "update", fail)

    response = client.patch(
        f"/api/v1/sensors/{sensor_id}",
        json={"name": "Flower Bed 1", "area_id": str(area_id)},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

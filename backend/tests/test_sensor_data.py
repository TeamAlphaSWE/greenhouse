from bson import ObjectId
from pymongo.errors import PyMongoError
import pytest

from app.db import get_collection
from app.repositories.sensor_data import sensor_data
from app.repositories.sensors import sensors


def test_list_sensor_data_empty(client):
    response = client.get(f"/api/v1/sensor_data/{ObjectId()}")

    assert response.status_code == 200
    assert response.get_json() == {"sensor_data": [], "total": 0}


def test_list_sensor_data_filters_by_sensor_id(app, client):
    sensor_id = ObjectId()
    other_sensor_id = ObjectId()

    with app.app_context():
        get_collection("sensor_data").insert_many([
            {
                "sensor_id": sensor_id,
                "timestamp": "2026-10-09T12:05:00Z",
                "values": [{"type": "temperature", "value": 23.6}],
            },
            {
                "sensor_id": sensor_id,
                "timestamp": "2026-10-09T12:00:00Z",
                "values": [{"type": "temperature", "value": 23.4}],
            },
            {
                "sensor_id": other_sensor_id,
                "timestamp": "2026-10-09T12:00:00Z",
                "values": [{"type": "temperature", "value": 19.0}],
            },
        ])

    response = client.get(f"/api/v1/sensor_data/{sensor_id}")
    body = response.get_json()

    assert response.status_code == 200
    assert body["total"] == 2
    assert [r["sensor_id"] for r in body["sensor_data"]] == [str(sensor_id), str(sensor_id)]
    assert [r["timestamp"] for r in body["sensor_data"]] == [
        "2026-10-09T12:00:00Z", "2026-10-09T12:05:00Z",
    ]
    assert all(isinstance(r["id"], str) for r in body["sensor_data"])


def test_list_sensor_data_invalid_sensor_id_returns_400(client):
    response = client.get("/api/v1/sensor_data/not-an-id")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid sensor_id"}


def test_list_sensor_data_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(sensor_data, "find", fail)

    response = client.get(f"/api/v1/sensor_data/{ObjectId()}")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}
    
def valid_reading(**overrides):
    body = {
        "hardware_id": "shellyhtg3-e4b3233085e8",
        "values": [
            {"type": "temperature", "value": 23.4},
            {"type": "humidity", "value": 50},
            {"type": "battery", "value": 82},
        ],
    }
    body.update(overrides)
    return body


def test_create_sensor_data_creates_pending_sensor_for_unknown_hardware_id(app, client):
    body = valid_reading()

    response = client.post("/api/v1/sensor_data", json=body)

    assert response.status_code == 201
    reading_id = response.get_json()["sensor_data"]["id"]

    with app.app_context():
        reading = get_collection("sensor_data").find_one({"_id": ObjectId(reading_id)})
        sensor = get_collection("sensors").find_one({"hardware_id": body["hardware_id"]})

    assert sensor is not None
    assert sensor["status"] == "pending"
    assert "zone_id" not in sensor
    assert "area_id" not in sensor
    assert reading["sensor_id"] == sensor["_id"]
    assert reading["values"] == body["values"]
    assert "timestamp" in reading


def test_create_sensor_data_reuses_existing_sensor_for_known_hardware_id(app, client):
    body = valid_reading()

    with app.app_context():
        sensor_id = sensors.create({
            "hardware_id": body["hardware_id"],
            "status": "active",
            "zone_id": ObjectId(),
            "area_id": ObjectId(),
        })["id"]

    response = client.post("/api/v1/sensor_data", json=body)

    assert response.status_code == 201
    reading_id = response.get_json()["sensor_data"]["id"]

    with app.app_context():
        reading = get_collection("sensor_data").find_one({"_id": ObjectId(reading_id)})
        sensor_count = get_collection("sensors").count_documents({"hardware_id": body["hardware_id"]})

    assert sensor_count == 1
    assert str(reading["sensor_id"]) == sensor_id


def test_create_sensor_data_saves_only_expected_fields(app, client):
    body = valid_reading(extra="ignored")
    body["values"][0]["unit"] = "C"

    response = client.post("/api/v1/sensor_data", json=body)
    reading_id = response.get_json()["sensor_data"]["id"]

    with app.app_context():
        doc = get_collection("sensor_data").find_one({"_id": ObjectId(reading_id)})

    assert set(doc) == {"_id", "sensor_id", "timestamp", "values"}
    assert doc["values"][0] == {"type": "temperature", "value": 23.4}


def test_create_sensor_data_invalid_json_returns_400(client):
    response = client.post(
        "/api/v1/sensor_data", data="not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid JSON"}


@pytest.mark.parametrize("body", [
    valid_reading(hardware_id=None),
    valid_reading(hardware_id=""),
    valid_reading(values=None),
    valid_reading(values=[]),
    valid_reading(values=["temperature"]),
    valid_reading(values=[{"value": 23.4}]),
    valid_reading(values=[{"type": "temperature"}]),
    valid_reading(values=[{"type": "temperature", "value": "hot"}]),
    valid_reading(values=[{"type": "temperature", "value": True}]),
])
def test_create_sensor_data_validation_returns_400(client, body):
    response = client.post("/api/v1/sensor_data", json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_sensor_data_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(sensor_data, "create", fail)

    response = client.post("/api/v1/sensor_data", json=valid_reading())

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

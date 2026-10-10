from bson import ObjectId
from pymongo.errors import PyMongoError

from app.db import get_collection
from app.repositories.sensor_data import sensor_data


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


def test_list_sensor_data_invalid_sensor_id_returns_empty(client):
    response = client.get("/api/v1/sensor_data/not-an-id")

    assert response.status_code == 200
    assert response.get_json() == {"sensor_data": [], "total": 0}


def test_list_sensor_data_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(sensor_data, "find", fail)

    response = client.get(f"/api/v1/sensor_data/{ObjectId()}")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

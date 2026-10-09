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
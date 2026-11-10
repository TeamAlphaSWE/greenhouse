from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.db import get_collection
from app.repositories.alerts import alerts


def _alert(created_at, value=30.0):
    return {
        "sensor_id": ObjectId(),
        "zone_id": ObjectId(),
        "area_id": ObjectId(),
        "type": "temperature",
        "value": value,
        "message": "temperature out of range",
        "created_at": created_at,
    }


def test_list_alerts_empty(client):
    response = client.get("/api/v1/alerts")

    assert response.status_code == 200
    assert response.get_json() == {"alerts": [], "total": 0}


def test_list_alerts_newest_first(app, client):
    with app.app_context():
        get_collection("alerts").insert_many([
            _alert(datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc), value=30.0),
            _alert(datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc), value=31.0),
        ])

    response = client.get("/api/v1/alerts")
    body = response.get_json()

    assert response.status_code == 200
    assert body["total"] == 2
    assert [a["value"] for a in body["alerts"]] == [31.0, 30.0]
    assert all(isinstance(a["id"], str) for a in body["alerts"])
    assert all(isinstance(a["area_id"], str) for a in body["alerts"])


def test_list_alerts_limit(app, client):
    with app.app_context():
        get_collection("alerts").insert_many([
            _alert(datetime(2026, 11, day, tzinfo=timezone.utc)) for day in range(1, 4)
        ])

    response = client.get("/api/v1/alerts?limit=2")

    assert response.status_code == 200
    assert response.get_json()["total"] == 2


def test_list_alerts_invalid_limit_returns_400(client):
    for limit in ["0", "-1", "abc"]:
        response = client.get(f"/api/v1/alerts?limit={limit}")

        assert response.status_code == 400
        assert response.get_json() == {"error": "limit must be a positive integer"}


def test_list_alerts_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(alerts, "find", fail)

    response = client.get("/api/v1/alerts")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

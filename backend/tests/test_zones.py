from pymongo.errors import PyMongoError

from app.db import get_collection
from app.repositories.zones import zones


def test_list_zones_empty(client):
    response = client.get("/api/v1/zones")

    assert response.status_code == 200
    assert response.get_json() == {"zones": [], "total": 0}


def test_list_zones(app, client):
    with app.app_context():
        get_collection("zones").insert_many([
            {"name": "Zone_1"},
            {"name": "Zone_2"},
            {"name": "Zone_3"},
        ])

    response = client.get("/api/v1/zones")
    body = response.get_json()


    assert response.status_code == 200
    assert body["total"] == 3
    assert [z["name"] for z in body["zones"]] == ["Zone_1", "Zone_2", "Zone_3"]
    assert all(isinstance(z["id"], str) for z in body["zones"])


def test_list_zones_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(zones, "find", fail)

    response = client.get("/api/v1/zones")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}
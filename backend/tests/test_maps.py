from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.db import get_collection
from app.repositories.maps import maps


def _insert_map(app, **overrides):
    doc = {
        "name": "Greenhouse Floor 1",
        "image_path": "/maps/greenhouse-floor-1.png",
        "regions": [],
        "created_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        **overrides,
    }
    with app.app_context():
        return get_collection("maps").insert_one(doc).inserted_id


def _insert_zone_with_area(app, area_id, zone_name="Zone 1", area_name="Area 1", region_id=None):
    area = {
        "id": area_id,
        "name": area_name,
        "status": "active",
        "target_conditions": {
            "humidity": {"min": 40, "max": 60},
            "temperature": {"min": 18, "max": 26},
        },
    }
    if region_id is not None:
        area["region_id"] = region_id

    with app.app_context():
        return get_collection("zones").insert_one({
            "name": zone_name,
            "description": "Test zone",
            "status": "active",
            "areas": [area],
        }).inserted_id


def _get_area(app, area_id):
    with app.app_context():
        zone = get_collection("zones").find_one({"areas.id": area_id})
    return next(a for a in zone["areas"] if a["id"] == area_id)


def test_list_maps_empty(client):
    response = client.get("/api/v1/maps")

    assert response.status_code == 200
    assert response.get_json() == {"maps": [], "total": 0}


def test_list_maps_returns_id_and_name_only(app, client):
    _insert_map(app, name="Floor A")
    _insert_map(app, name="Floor B")

    response = client.get("/api/v1/maps")
    body = response.get_json()

    assert response.status_code == 200
    assert body["total"] == 2
    assert [m["name"] for m in body["maps"]] == ["Floor A", "Floor B"]
    assert all(isinstance(m["id"], str) for m in body["maps"])
    assert all("image_path" not in m and "regions" not in m for m in body["maps"])


def test_list_maps_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(maps, "find", fail)

    response = client.get("/api/v1/maps")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}


def test_get_map_joins_area_and_zone_names(app, client):
    area_id = ObjectId()
    region_id = ObjectId()
    _insert_zone_with_area(app, area_id, zone_name="Zone 1", area_name="Flower Bed", region_id=region_id)
    map_id = _insert_map(app, regions=[{"id": region_id, "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}])

    response = client.get(f"/api/v1/maps/{map_id}")
    body = response.get_json()

    assert response.status_code == 200
    region = body["map"]["regions"][0]
    assert region["area_name"] == "Flower Bed"
    assert region["zone_name"] == "Zone 1"
    assert region["id"] == str(region_id)
    assert isinstance(region["zone_id"], str)
    assert region["x"] == 0.1


def test_get_map_region_with_unknown_id_has_null_names(app, client):
    map_id = _insert_map(app, regions=[{"id": ObjectId(), "x": 0, "y": 0, "w": 1, "h": 1}])

    response = client.get(f"/api/v1/maps/{map_id}")
    body = response.get_json()

    assert response.status_code == 200
    region = body["map"]["regions"][0]
    assert region["area_name"] is None
    assert region["zone_name"] is None
    assert region["zone_id"] is None


def test_get_map_filler_region_has_no_id_and_keeps_text(app, client):
    map_id = _insert_map(app, regions=[{"x": 0.5, "y": 0.02, "w": 0.3, "h": 0.05, "text": "Office"}])

    response = client.get(f"/api/v1/maps/{map_id}")
    body = response.get_json()

    assert response.status_code == 200
    region = body["map"]["regions"][0]
    assert "id" not in region
    assert region["text"] == "Office"
    assert region["area_name"] is None


def test_get_map_malformed_id_returns_400(client):
    response = client.get("/api/v1/maps/not-an-id")

    assert response.status_code == 400


def test_get_map_unknown_id_returns_404(client):
    response = client.get(f"/api/v1/maps/{ObjectId()}")

    assert response.status_code == 404


def test_get_map_database_error_returns_500(app, client, monkeypatch):
    map_id = _insert_map(app)

    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(maps, "get", fail)

    response = client.get(f"/api/v1/maps/{map_id}")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}


def test_create_map(client):
    response = client.post(
        "/api/v1/maps",
        json={"name": "Greenhouse Floor 1", "image_path": "/maps/floor-1.png"},
    )
    body = response.get_json()

    assert response.status_code == 201
    assert body["map"]["name"] == "Greenhouse Floor 1"
    assert body["map"]["image_path"] == "/maps/floor-1.png"
    assert body["map"]["regions"] == []
    assert isinstance(body["map"]["id"], str)


def test_create_map_missing_name_returns_400(client):
    response = client.post("/api/v1/maps", json={"image_path": "/maps/floor-1.png"})

    assert response.status_code == 400


def test_create_map_empty_name_returns_400(client):
    response = client.post(
        "/api/v1/maps",
        json={"name": "   ", "image_path": "/maps/floor-1.png"},
    )

    assert response.status_code == 400


def test_create_map_missing_image_path_returns_400(client):
    response = client.post("/api/v1/maps", json={"name": "Greenhouse Floor 1"})

    assert response.status_code == 400


def test_create_map_invalid_json_returns_400(client):
    response = client.post(
        "/api/v1/maps",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_map_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(maps, "create", fail)

    response = client.post(
        "/api/v1/maps",
        json={"name": "Greenhouse Floor 1", "image_path": "/maps/floor-1.png"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}


def test_update_map_regions_links_area_and_generates_id(app, client):
    area_id = ObjectId()
    zone_id = _insert_zone_with_area(app, area_id)
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"area_id": str(area_id), "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}]},
    )
    body = response.get_json()

    assert response.status_code == 200
    region = body["map"]["regions"][0]
    assert isinstance(region["id"], str)

    area = _get_area(app, area_id)
    assert str(area["region_id"]) == region["id"]

    with app.app_context():
        zone = get_collection("zones").find_one({"_id": zone_id})
    assert str(zone["map_id"]) == str(map_id)


def test_update_map_regions_preserves_given_id(app, client):
    area_id = ObjectId()
    region_id = ObjectId()
    _insert_zone_with_area(app, area_id)
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"id": str(region_id), "area_id": str(area_id), "x": 0, "y": 0, "w": 1, "h": 1}]},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["map"]["regions"][0]["id"] == str(region_id)

    area = _get_area(app, area_id)
    assert area["region_id"] == region_id


def test_update_map_regions_filler_region_has_no_id(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"x": 0.5, "y": 0.02, "w": 0.3, "h": 0.05, "text": "Office"}]},
    )
    body = response.get_json()

    assert response.status_code == 200
    region = body["map"]["regions"][0]
    assert "id" not in region
    assert region["text"] == "Office"


def test_update_map_regions_unlinks_area_when_region_removed(app, client):
    area_id = ObjectId()
    region_id = ObjectId()
    _insert_zone_with_area(app, area_id, region_id=region_id)
    map_id = _insert_map(app, regions=[{"id": region_id, "x": 0, "y": 0, "w": 1, "h": 1}])

    response = client.put(f"/api/v1/maps/{map_id}/regions", json={"regions": []})

    assert response.status_code == 200
    assert response.get_json()["map"]["regions"] == []

    area = _get_area(app, area_id)
    assert "region_id" not in area


def test_update_map_regions_malformed_map_id_returns_400(client):
    response = client.put("/api/v1/maps/not-an-id/regions", json={"regions": []})

    assert response.status_code == 400


def test_update_map_regions_unknown_map_returns_404(app, client):
    area_id = ObjectId()
    _insert_zone_with_area(app, area_id)

    response = client.put(
        f"/api/v1/maps/{ObjectId()}/regions",
        json={"regions": [{"area_id": str(area_id), "x": 0, "y": 0, "w": 1, "h": 1}]},
    )

    assert response.status_code == 404


def test_update_map_regions_not_a_list_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(f"/api/v1/maps/{map_id}/regions", json={"regions": "nope"})

    assert response.status_code == 400


def test_update_map_regions_malformed_area_id_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"area_id": "not-an-id", "x": 0, "y": 0, "w": 1, "h": 1}]},
    )

    assert response.status_code == 400


def test_update_map_regions_malformed_region_id_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"id": "not-an-id", "x": 0, "y": 0, "w": 1, "h": 1}]},
    )

    assert response.status_code == 400


def test_update_map_regions_non_numeric_coordinate_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"area_id": str(ObjectId()), "x": "oops", "y": 0, "w": 1, "h": 1}]},
    )

    assert response.status_code == 400


def test_update_map_regions_non_string_text_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"x": 0, "y": 0, "w": 1, "h": 1, "text": 42}]},
    )

    assert response.status_code == 400


def test_update_map_regions_unowned_area_id_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"area_id": str(ObjectId()), "x": 0, "y": 0, "w": 1, "h": 1}]},
    )

    assert response.status_code == 400


def test_update_map_regions_invalid_json_returns_400(app, client):
    map_id = _insert_map(app)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_map_regions_database_error_returns_500(app, client, monkeypatch):
    area_id = ObjectId()
    _insert_zone_with_area(app, area_id)
    map_id = _insert_map(app)

    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(maps, "update", fail)

    response = client.put(
        f"/api/v1/maps/{map_id}/regions",
        json={"regions": [{"area_id": str(area_id), "x": 0, "y": 0, "w": 1, "h": 1}]},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

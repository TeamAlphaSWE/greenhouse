from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.errors import PyMongoError
import pytest

from app.db import get_collection
from app.repositories.zones import zones


def seed_zone(app):
    tomatoes, peppers = ObjectId(), ObjectId()
    with app.app_context():
        zone_id = get_collection("zones").insert_one({
            "name": "North",
            "areas": [
                {"id": tomatoes, "name": "Tomatoes", "target_conditions": {
                    "temperature": {"min": 18, "max": 26},
                    "humidity": {"min": 40, "max": 70},
                }},
                {"id": peppers, "name": "Peppers", "target_conditions": {
                    "temperature": {"min": 20, "max": 30},
                    "humidity": {"min": 50, "max": 80},
                }},
            ],
        }).inserted_id
    return zone_id, tomatoes, peppers


def stored_areas(app, zone_id):
    with app.app_context():
        doc = get_collection("zones").find_one({"_id": zone_id})
    return {a["name"]: a for a in doc["areas"]}, doc


def test_areas_overview_shows_warning_for_stale_in_range_sensor(app, client):
    zone_id, tomatoes, _ = seed_zone(app)
    app.config["SENSOR_REPORT_INTERVAL_MINUTES"] = 5
    app.config["SENSOR_STALE_FACTOR"] = 2
    with app.app_context():
        sensor_id = get_collection("sensors").insert_one(
            {"name": "A", "hardware_id": "a", "area_id": tomatoes}
        ).inserted_id
        get_collection("sensor_data").insert_one({
            "sensor_id": sensor_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=11),
            "values": [{"type": "temperature", "value": 22}],
        })

    body = client.get("/api/v1/areas/overview").get_json()

    areas = {a["name"]: a for zone in body["zones"] for a in zone["areas"]}
    assert areas["Tomatoes"]["state"] == "warning"


def test_update_target_conditions_sets_both_measurements(app, client):
    zone_id, tomatoes, _ = seed_zone(app)
    body = {"temperature": {"min": 15, "max": 25}, "humidity": {"min": 35, "max": 65}}

    response = client.patch(f"/api/v1/areas/{tomatoes}/target_conditions", json=body)

    assert response.status_code == 200
    area = response.get_json()["area"]
    assert area["id"] == str(tomatoes)
    assert area["name"] == "Tomatoes"
    assert area["target_conditions"] == body
    areas, _ = stored_areas(app, zone_id)
    assert areas["Tomatoes"]["target_conditions"] == body


def test_update_target_conditions_only_changes_given_measurement(app, client):
    zone_id, tomatoes, _ = seed_zone(app)

    response = client.patch(
        f"/api/v1/areas/{tomatoes}/target_conditions",
        json={"temperature": {"min": 10, "max": 20}},
    )

    assert response.status_code == 200
    areas, _ = stored_areas(app, zone_id)
    assert areas["Tomatoes"]["target_conditions"] == {
        "temperature": {"min": 10, "max": 20},
        "humidity": {"min": 40, "max": 70},
    }


def test_update_target_conditions_leaves_other_areas_alone(app, client):
    zone_id, tomatoes, _ = seed_zone(app)

    client.patch(f"/api/v1/areas/{tomatoes}/target_conditions",
                 json={"temperature": {"min": 10, "max": 20}})

    areas, _ = stored_areas(app, zone_id)
    assert areas["Peppers"]["target_conditions"] == {
        "temperature": {"min": 20, "max": 30},
        "humidity": {"min": 50, "max": 80},
    }


def test_update_target_conditions_sets_zone_updated_at(app, client):
    zone_id, tomatoes, _ = seed_zone(app)

    client.patch(f"/api/v1/areas/{tomatoes}/target_conditions",
                 json={"humidity": {"min": 30, "max": 60}})

    _, doc = stored_areas(app, zone_id)
    assert isinstance(doc["updated_at"], datetime)


def test_update_target_conditions_invalid_id_returns_400(client):
    response = client.patch("/api/v1/areas/not-an-id/target_conditions",
                            json={"temperature": {"min": 10, "max": 20}})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid area id"}


def test_update_target_conditions_unknown_area_returns_404(app, client):
    seed_zone(app)

    response = client.patch(f"/api/v1/areas/{ObjectId()}/target_conditions",
                            json={"temperature": {"min": 10, "max": 20}})

    assert response.status_code == 404
    assert response.get_json() == {"error": "Area not found"}


def test_update_target_conditions_invalid_json_returns_400(app, client):
    _, tomatoes, _ = seed_zone(app)

    response = client.patch(f"/api/v1/areas/{tomatoes}/target_conditions",
                            data="not json", content_type="application/json")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid JSON"}


@pytest.mark.parametrize("body, error", [
    ({}, "temperature or humidity is required"),
    ({"light": {"min": 1, "max": 2}}, "Unknown measurement: light"),
    ({"temperature": {"min": 10}}, "temperature needs both min and max"),
    ({"temperature": {"max": 20}}, "temperature needs both min and max"),
    ({"temperature": {"min": 10, "max": 20, "unit": "C"}}, "temperature needs both min and max"),
    ({"temperature": 20}, "temperature needs both min and max"),
    ({"temperature": {"min": 20, "max": 20}}, "temperature min must be less than max"),
    ({"temperature": {"min": 25, "max": 20}}, "temperature min must be less than max"),
    ({"humidity": {"min": "40", "max": 70}}, "humidity min and max must be integers"),
    ({"humidity": {"min": 40.5, "max": 70}}, "humidity min and max must be integers"),
    ({"humidity": {"min": None, "max": 70}}, "humidity min and max must be integers"),
    ({"humidity": {"min": False, "max": True}}, "humidity min and max must be integers"),
    ({"temperature": {"min": 10, "max": 20}, "humidity": {"min": 70, "max": 40}},
     "humidity min must be less than max"),
])
def test_update_target_conditions_validation_returns_400(app, client, body, error):
    zone_id, tomatoes, _ = seed_zone(app)
    before, _ = stored_areas(app, zone_id)

    response = client.patch(f"/api/v1/areas/{tomatoes}/target_conditions", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": error}
    after, _ = stored_areas(app, zone_id)
    assert after == before


def test_update_target_conditions_database_error_returns_500(app, client, monkeypatch):
    _, tomatoes, _ = seed_zone(app)

    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(zones, "set_target_conditions", fail)

    response = client.patch(f"/api/v1/areas/{tomatoes}/target_conditions",
                            json={"temperature": {"min": 10, "max": 20}})

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

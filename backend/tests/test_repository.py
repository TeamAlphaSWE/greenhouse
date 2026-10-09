from bson import ObjectId
from flask import jsonify

from app.repository import Repository


class PlantRepository(Repository):
    collection_name = "plants"


plants = PlantRepository()


def test_create_returns_entity_with_string_id(app):
    with app.app_context():
        plant = plants.create({"name": "Basil"})

        assert set(plant) == {"id", "name"}
        assert isinstance(plant["id"], str)


def test_get(app):
    with app.app_context():
        plant = plants.create({"name": "Basil"})

        assert plants.get(plant["id"]) == plant


def test_get_with_invalid_or_unknown_id_returns_none(app):
    with app.app_context():
        assert plants.get("not-an-id") is None
        assert plants.get(None) is None
        assert plants.get(str(ObjectId())) is None


def test_find(app):
    with app.app_context():
        plants.create({"name": "Basil", "kind": "herb"})
        plants.create({"name": "Tomato", "kind": "vegetable"})

        herbs = plants.find({"kind": "herb"})

        assert [p["name"] for p in herbs] == ["Basil"]


def test_update(app):
    with app.app_context():
        plant = plants.create({"name": "Basil"})

        updated = plants.update(plant["id"], {"name": "Thai Basil", "id": "ignored"})

        assert updated == {"id": plant["id"], "name": "Thai Basil"}
        assert plants.update("not-an-id", {"name": "x"}) is None


def test_delete(app):
    with app.app_context():
        plant = plants.create({"name": "Basil"})

        assert plants.delete(plant["id"]) is True
        assert plants.delete(plant["id"]) is False
        assert plants.delete("not-an-id") is False


def test_jsonify_serializes_object_ids(app):
    oid = ObjectId()
    with app.app_context():
        assert jsonify({"ref": oid}).get_json() == {"ref": str(oid)}

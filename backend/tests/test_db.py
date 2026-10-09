from pymongo import MongoClient

from app import create_app
from app.db import get_client, get_collection, get_db, ping


def test_get_db_uses_configured_database(app):
    with app.app_context():
        assert get_db().name == "greenhouse_test"


def test_get_collection_round_trip(app):
    with app.app_context():
        plants = get_collection("plants")
        plants.insert_one({"name": "Basil"})

        assert plants.find_one({"name": "Basil"}, {"_id": 0}) == {"name": "Basil"}


def test_client_is_shared_across_requests(app):
    with app.app_context():
        first = get_client()
    with app.app_context():
        assert get_client() is first


def test_ping(app):
    with app.app_context():
        assert ping() is True


def test_default_client_is_pymongo():
    app = create_app({"MONGO_URI": "mongodb://localhost:27017"})
    with app.app_context():
        assert isinstance(get_client(), MongoClient)

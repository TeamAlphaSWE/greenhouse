"""MongoDB access for the Flask app.

A single `MongoClient` is created per app in `init_db()` and reused for every
request (PyMongo clients are thread-safe and pool connections internally).
Route and service code should use the helpers below instead of building
clients themselves:

    from app.db import get_collection

    plants = get_collection("plants")
    plants.find_one({"name": "Basil"})
"""

from flask import Flask, current_app
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

EXTENSION_KEY = "mongo"


def init_db(app: Flask) -> None:
    """Attach a MongoClient to the app.

    Setting `MONGO_CLIENT` in the app config injects an existing client
    (e.g. a mongomock client in tests) instead of connecting to `MONGO_URI`.
    The client connects lazily, so the app starts even if MongoDB is down.
    """
    client = app.config.get("MONGO_CLIENT")
    if client is None:
        client = MongoClient(
            app.config["MONGO_URI"],
            serverSelectionTimeoutMS=app.config["MONGO_SERVER_SELECTION_TIMEOUT_MS"],
            tz_aware=True,
        )
    app.extensions[EXTENSION_KEY] = client


def get_client() -> MongoClient:
    """Return the MongoClient for the current app."""
    return current_app.extensions[EXTENSION_KEY]


def get_db() -> Database:
    """Return the configured database for the current app."""
    return get_client()[current_app.config["MONGO_DB_NAME"]]


def get_collection(name: str) -> Collection:
    """Return a collection from the configured database."""
    return get_db()[name]


def ping() -> bool:
    """Return True if the MongoDB server is reachable."""
    try:
        get_client().admin.command("ping")
    except Exception:
        return False
    return True

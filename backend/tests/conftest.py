import mongomock
import pytest

from app import create_app


@pytest.fixture
def app():
    return create_app({
        "TESTING": True,
        "MONGO_CLIENT": mongomock.MongoClient(),
        "MONGO_DB_NAME": "greenhouse_test",
    })


@pytest.fixture
def client(app):
    return app.test_client()

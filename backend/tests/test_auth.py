from bson import ObjectId
from flask import g, jsonify
from pymongo.errors import PyMongoError
from werkzeug.security import generate_password_hash
import pytest

from app.auth import issue_token, require_auth
from app.db import get_collection
from app.repositories.users import users


def seed_user(app, username="alice", password="correct-horse", is_admin=False):
    with app.app_context():
        return users.create({
            "username": username,
            "password_hash": generate_password_hash(password, method="pbkdf2:sha256"),
            "is_admin": is_admin,
        })


def test_login_succeeds_with_correct_credentials(app, client):
    seed_user(app, username="alice", password="correct-horse")

    response = client.post("/api/v1/login", json={"username": "alice", "password": "correct-horse"})

    assert response.status_code == 200
    assert isinstance(response.get_json()["token"], str)


def test_login_rejects_wrong_password(app, client):
    seed_user(app, username="alice", password="correct-horse")

    response = client.post("/api/v1/login", json={"username": "alice", "password": "wrong"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid username or password"}


def test_login_rejects_unknown_username(client):
    response = client.post("/api/v1/login", json={"username": "nobody", "password": "whatever"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid username or password"}


def test_login_invalid_json_returns_400(client):
    response = client.post("/api/v1/login", data="not json", content_type="application/json")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid JSON"}


@pytest.mark.parametrize("body", [
    {"password": "whatever"},
    {"username": "alice"},
    {"username": "alice", "password": 123},
])
def test_login_validation_returns_400(client, body):
    response = client.post("/api/v1/login", json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_login_database_error_returns_500(client, monkeypatch):
    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(users, "find_by_username", fail)

    response = client.post("/api/v1/login", json={"username": "alice", "password": "whatever"})

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}


def _protected_view():
    return jsonify({"user_id": g.user["id"]})


def test_require_auth_accepts_valid_token(app, client):
    app.add_url_rule("/__protected", "protected", require_auth(_protected_view), methods=["GET"])
    user = seed_user(app)

    with app.app_context():
        token = issue_token(app, user["id"])

    response = client.get("/__protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json() == {"user_id": user["id"]}


def test_require_auth_rejects_missing_header(app, client):
    app.add_url_rule("/__protected", "protected", require_auth(_protected_view), methods=["GET"])

    response = client.get("/__protected")

    assert response.status_code == 401


def test_require_auth_rejects_malformed_token(app, client):
    app.add_url_rule("/__protected", "protected", require_auth(_protected_view), methods=["GET"])

    response = client.get("/__protected", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_require_auth_rejects_token_for_deleted_user(app, client):
    app.add_url_rule("/__protected", "protected", require_auth(_protected_view), methods=["GET"])
    user = seed_user(app)

    with app.app_context():
        token = issue_token(app, user["id"])
        get_collection("users").delete_one({"_id": ObjectId(user["id"])})

    response = client.get("/__protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401

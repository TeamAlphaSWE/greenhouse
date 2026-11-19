from pymongo.errors import PyMongoError
from werkzeug.security import generate_password_hash
import pytest

from app.auth import issue_token
from app.repositories.users import users
from app.routes.settings import DEFAULT_SETTINGS


def seed_user(app, username="alice", password="correct-horse", admin=False):
    with app.app_context():
        return users.create({
            "username": username,
            "password_hash": generate_password_hash(password, method="pbkdf2:sha256"),
            "admin": admin,
        })


def _auth_header(app, user):
    with app.app_context():
        return {"Authorization": f"Bearer {issue_token(app, user['id'])}"}


VALID_SETTINGS = {
    "temperature_unit": "°F",
    "alerts_enabled": False,
    "email_alerts_enabled": True,
    "notification_email": "alice@example.com",
}


def test_get_settings_returns_defaults_when_unset(app, client):
    user = seed_user(app)

    response = client.get("/api/v1/settings", headers=_auth_header(app, user))

    assert response.status_code == 200
    assert response.get_json() == {"settings": DEFAULT_SETTINGS}


def test_get_settings_requires_auth(client):
    response = client.get("/api/v1/settings")

    assert response.status_code == 401


def test_put_settings_saves_and_echoes_back(app, client):
    user = seed_user(app)

    response = client.put(
        "/api/v1/settings", json=VALID_SETTINGS, headers=_auth_header(app, user),
    )

    assert response.status_code == 200
    assert response.get_json() == {"settings": VALID_SETTINGS}

    get_response = client.get("/api/v1/settings", headers=_auth_header(app, user))
    assert get_response.get_json() == {"settings": VALID_SETTINGS}


def test_put_settings_requires_auth(client):
    response = client.put("/api/v1/settings", json=VALID_SETTINGS)

    assert response.status_code == 401


def test_put_settings_invalid_json_returns_400(app, client):
    user = seed_user(app)

    response = client.put(
        "/api/v1/settings", data="not json", content_type="application/json",
        headers=_auth_header(app, user),
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid JSON"}


@pytest.mark.parametrize("body", [
    {**VALID_SETTINGS, "temperature_unit": "F"},
    {**VALID_SETTINGS, "alerts_enabled": "yes"},
    {**VALID_SETTINGS, "email_alerts_enabled": 1},
    {**VALID_SETTINGS, "notification_email": 123},
    {**VALID_SETTINGS, "email_alerts_enabled": True, "notification_email": None},
    {**VALID_SETTINGS, "email_alerts_enabled": True, "notification_email": ""},
])
def test_put_settings_validation_returns_400(app, client, body):
    user = seed_user(app)

    response = client.put("/api/v1/settings", json=body, headers=_auth_header(app, user))

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_put_settings_database_error_returns_500(app, client, monkeypatch):
    user = seed_user(app)

    def fail(*args, **kwargs):
        raise PyMongoError("database is down")

    monkeypatch.setattr(users, "update", fail)

    response = client.put(
        "/api/v1/settings", json=VALID_SETTINGS, headers=_auth_header(app, user),
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Unexpected server error"}

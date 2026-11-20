from datetime import datetime, timezone
from unittest.mock import MagicMock

from bson import ObjectId
from werkzeug.security import generate_password_hash

from app.db import get_collection
from app.repositories.users import users
from scripts.notify_alerts import run


def _alert(notified=None):
    doc = {
        "sensor_id": ObjectId(),
        "zone_id": ObjectId(),
        "area_id": ObjectId(),
        "type": "temperature",
        "value": 30.0,
        "message": "temperature out of range",
        "created_at": datetime(2026, 11, 1, tzinfo=timezone.utc),
    }
    if notified is not None:
        doc["notified"] = notified
    return doc


def _recipient(app, email_alerts_enabled=True, notification_email="alice@example.com"):
    with app.app_context():
        return users.create({
            "username": "alice",
            "password_hash": generate_password_hash("pw", method="pbkdf2:sha256"),
            "admin": False,
            "settings": {
                "email_alerts_enabled": email_alerts_enabled,
                "notification_email": notification_email,
            },
        })


def _mock_email_service(app, monkeypatch, send_return=True):
    mock_service = MagicMock()
    mock_service.send.return_value = send_return
    monkeypatch.setitem(app.extensions, "email_service", mock_service)
    return mock_service


def test_nothing_to_send_skips_email_service(app, monkeypatch):
    mock_service = _mock_email_service(app, monkeypatch)

    run(app)

    mock_service.send.assert_not_called()


def test_one_recipient_gets_a_summary_and_alert_is_marked_notified(app, monkeypatch):
    with app.app_context():
        get_collection("alerts").insert_one(_alert())

    _recipient(app)
    mock_service = _mock_email_service(app, monkeypatch)

    run(app)

    mock_service.send.assert_called_once()
    to, subject, body = mock_service.send.call_args.args
    assert to == "alice@example.com"
    assert "1" in subject
    assert "temperature out of range" in body

    with app.app_context():
        alert = get_collection("alerts").find_one({})
        assert alert["notified"] is True


def test_recipients_without_alerts_enabled_are_skipped(app, monkeypatch):
    with app.app_context():
        get_collection("alerts").insert_one(_alert())

    _recipient(app, email_alerts_enabled=False)
    mock_service = _mock_email_service(app, monkeypatch)

    run(app)

    mock_service.send.assert_not_called()


def test_already_notified_alerts_are_not_resent(app, monkeypatch):
    with app.app_context():
        get_collection("alerts").insert_one(_alert(notified=True))

    _recipient(app)
    mock_service = _mock_email_service(app, monkeypatch)

    run(app)

    mock_service.send.assert_not_called()


def test_send_failure_does_not_raise_and_alert_is_still_marked_notified(app, monkeypatch):
    with app.app_context():
        get_collection("alerts").insert_one(_alert())

    _recipient(app)
    _mock_email_service(app, monkeypatch, send_return=False)

    run(app)

    with app.app_context():
        alert = get_collection("alerts").find_one({})
        assert alert["notified"] is True


def test_email_service_unconfigured_skips_without_raising(app, monkeypatch):
    with app.app_context():
        get_collection("alerts").insert_one(_alert())

    _recipient(app)
    monkeypatch.setitem(app.extensions, "email_service", None)

    run(app)

    with app.app_context():
        alert = get_collection("alerts").find_one({})
        assert alert.get("notified") is not True

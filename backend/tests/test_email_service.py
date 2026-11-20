from unittest.mock import patch

import pytest

from app.services.email_service import EmailService


@pytest.fixture
def email_config():
    return {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": 587,
        "SMTP_USER": "ksu.greenhouse@gmail.com",
        "SMTP_PASSWORD": "test-password",
    }


@patch("app.services.email_service.smtplib.SMTP")
def test_send_succeeds(mock_smtp, email_config):
    server = mock_smtp.return_value.__enter__.return_value

    service = EmailService(email_config)
    result = service.send("alice@example.com", "Alert", "Body text")

    assert result is True
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("ksu.greenhouse@gmail.com", "test-password")

    sent_message = server.send_message.call_args.args[0]
    assert sent_message["Subject"] == "Alert"
    assert sent_message["From"] == "ksu.greenhouse@gmail.com"
    assert sent_message["To"] == "alice@example.com"
    assert sent_message.get_content().strip() == "Body text"


@patch("app.services.email_service.smtplib.SMTP")
def test_send_failure_is_caught_and_logged(mock_smtp, email_config):
    mock_smtp.return_value.__enter__.side_effect = OSError("connection refused")

    service = EmailService(email_config)
    result = service.send("alice@example.com", "Alert", "Body text")

    assert result is False

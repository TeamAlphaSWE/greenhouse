"""Emails a summary of new alerts to users with email alerts enabled.

Run on a schedule (see deploy/systemd/greenhouse-notify.*). Pending alerts
are marked notified once a run has attempted delivery, even if some
recipients failed, so a persistently bad address doesn't resend the same
backlog forever.
"""
import logging

from app import create_app
from app.repositories.alerts import alerts as alert_repository
from app.repositories.users import users as user_repository

logger = logging.getLogger(__name__)


def _format_summary(pending_alerts):
    lines = [f"- {alert['type']}: {alert['message']}" for alert in pending_alerts]
    return "\n".join(lines)


def run(app):
    with app.app_context():
        pending_alerts = alert_repository.find({"notified": {"$ne": True}})
        if not pending_alerts:
            return

        email_service = app.extensions.get("email_service")
        if email_service is None:
            logger.warning("Email service is not configured; skipping alert notifications")
            return

        subject = f"Greenhouse: {len(pending_alerts)} new alert(s)"
        body = _format_summary(pending_alerts)

        recipients = user_repository.find({"settings.email_alerts_enabled": True})
        for recipient in recipients:
            to = recipient.get("settings", {}).get("notification_email")
            if not to:
                continue
            email_service.send(to, subject, body)

        for alert in pending_alerts:
            alert_repository.update(alert["id"], {"notified": True})


if __name__ == "__main__":
    run(create_app())

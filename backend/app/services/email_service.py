import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, config):
        self.host = config["SMTP_HOST"]
        self.port = int(config["SMTP_PORT"])
        self.user = config["SMTP_USER"]
        self.password = config["SMTP_PASSWORD"]

    def send(self, to, subject, body):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.user
        message["To"] = to
        message.set_content(body)

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(message)
        except Exception:
            logger.exception("Failed to send email to %s", to)
            return False
        return True

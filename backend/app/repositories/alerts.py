from __future__ import annotations

from app.repository import Repository


class AlertRepository(Repository):
    collection_name = "alerts"


alerts = AlertRepository()

from __future__ import annotations

from datetime import datetime, timezone

from app.repository import Repository


class SensorRepository(Repository):
    collection_name = "sensors"

    def find_by_hardware_id(self, hardware_id: str) -> dict | None:
        return self.find_one({"hardware_id": hardware_id})

    def create_pending(self, hardware_id: str) -> dict:
        now = datetime.now(timezone.utc)
        return self.create({
            "hardware_id": hardware_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        })


sensors = SensorRepository()
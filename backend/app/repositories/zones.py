from __future__ import annotations

from bson import ObjectId

from app.repository import Repository


class ZoneRepository(Repository):
    collection_name = "zones"

    def find_by_area_id(self, area_id: ObjectId) -> dict | None:
        return self.find_one({"areas.id": area_id})


zones = ZoneRepository()
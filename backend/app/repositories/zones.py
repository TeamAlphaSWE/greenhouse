from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from app.repository import Repository


class ZoneRepository(Repository):
    collection_name = "zones"

    def find_by_area_id(self, area_id: ObjectId) -> dict | None:
        return self.find_one({"areas.id": area_id})

    def link_area_to_region(self, area_id: ObjectId, region_id: ObjectId, map_id: ObjectId) -> None:
        self.collection.update_one(
            {"areas.id": area_id},
            {"$set": {"areas.$.region_id": region_id, "map_id": map_id}},
        )

    def unlink_area_region(self, area_id: ObjectId) -> None:
        self.collection.update_one(
            {"areas.id": area_id},
            {"$unset": {"areas.$.region_id": ""}},
        )


    def set_target_conditions(self, area_id: ObjectId, conditions: dict) -> dict | None:
        changes = {
            f"areas.$.target_conditions.{measurement}": limits
            for measurement, limits in conditions.items()
        }
        changes["updated_at"] = datetime.now(timezone.utc)
        doc = self.collection.find_one_and_update(
            {"areas.id": area_id},
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_entity(doc)


zones = ZoneRepository()
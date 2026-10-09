"""Base class for MongoDB data access.

Subclass `Repository` once per collection and add domain-specific queries.
Documents leave the repository with a string `id` instead of Mongo's
`_id: ObjectId`, and ids passed in are strings, so callers never deal with
BSON types:

    class ZoneRepository(Repository):
        collection_name = "zones"

        def find_by_name(self, name):
            return self.find_one({"name": name})

    zones = ZoneRepository()
    zone = zones.create({"name": "Zone A"})   # {"id": "...", "name": "Zone A"}
    zones.get(zone["id"])
"""

from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.collection import Collection

from app.db import get_collection


class Repository:
    collection_name: str

    @property
    def collection(self) -> Collection:
        # Resolved on each access so module-level instances work with any app.
        return get_collection(self.collection_name)

    def find(self, filter=None, **kwargs) -> list[dict]:
        return [self._to_entity(doc) for doc in self.collection.find(filter or {}, **kwargs)]

    def find_one(self, filter) -> dict | None:
        return self._to_entity(self.collection.find_one(filter))

    def get(self, id: str) -> dict | None:
        oid = self._to_object_id(id)
        return self.find_one({"_id": oid}) if oid else None

    def create(self, data: dict) -> dict:
        document = {k: v for k, v in data.items() if k != "id"}
        result = self.collection.insert_one(document)
        return self._to_entity({**document, "_id": result.inserted_id})

    def update(self, id: str, changes: dict) -> dict | None:
        oid = self._to_object_id(id)
        if oid is None:
            return None
        changes = {k: v for k, v in changes.items() if k != "id"}
        doc = self.collection.find_one_and_update(
            {"_id": oid}, {"$set": changes}, return_document=ReturnDocument.AFTER
        )
        return self._to_entity(doc)

    def delete(self, id: str) -> bool:
        oid = self._to_object_id(id)
        return oid is not None and self.collection.delete_one({"_id": oid}).deleted_count == 1

    @staticmethod
    def _to_object_id(id: str) -> ObjectId | None:
        try:
            return ObjectId(id)
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _to_entity(doc: dict | None) -> dict | None:
        if doc is None:
            return None
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

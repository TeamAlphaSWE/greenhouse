from datetime import datetime, timezone
from bson import ObjectId
from app.repository import Repository
class SensorDataRepository(Repository):
    collection_name = "sensor_data"

    def find_by_sensor_id(self, sensor_id: str) -> list[dict]:
        oid = self._to_object_id(sensor_id)
        if oid is None:
            return []
        return self.find({"sensor_id": oid}, sort=[("timestamp", 1)])

    def latest_by_sensor(self, sensor_ids: list) -> dict:
        """Return {sensor_id (str): latest reading} for the given sensor ObjectIds."""
        pipeline = [
            {"$match": {"sensor_id": {"$in": sensor_ids}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$sensor_id", "doc": {"$first": "$$ROOT"}}},
        ]
        return {
            str(row["_id"]): self._to_entity(row["doc"])
            for row in self.collection.aggregate(pipeline)
        }
    
    def create_reading(self, sensor_id: str, values: list[dict]) -> dict:
        return self.create({
            "sensor_id": ObjectId(sensor_id),
            "timestamp": datetime.now(timezone.utc),
            "values": values,
        })


sensor_data = SensorDataRepository()
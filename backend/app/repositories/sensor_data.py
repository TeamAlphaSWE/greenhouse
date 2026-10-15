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

    def create_reading(self, sensor_id: str, values: list[dict]) -> dict:
        return self.create({
            "sensor_id": ObjectId(sensor_id),
            "timestamp": datetime.now(timezone.utc),
            "values": values,
        })


sensor_data = SensorDataRepository()
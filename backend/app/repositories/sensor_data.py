from app.repository import Repository


class SensorDataRepository(Repository):
    collection_name = "sensor_data"

    def find_by_sensor_id(self, sensor_id: str) -> list[dict]:
        oid = self._to_object_id(sensor_id)
        if oid is None:
            return []
        return self.find({"sensor_id": oid}, sort=[("timestamp", 1)])


sensor_data = SensorDataRepository()

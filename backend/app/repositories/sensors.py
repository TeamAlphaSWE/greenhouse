from app.repository import Repository


class SensorRepository(Repository):
    collection_name = "sensors"


sensors = SensorRepository()
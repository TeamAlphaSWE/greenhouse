from app.repository import Repository


class ZoneRepository(Repository):
    collection_name = "zones"


zones = ZoneRepository()
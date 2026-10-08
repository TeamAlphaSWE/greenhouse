from app.repository import Repository


class PlantRepository(Repository):
    collection_name = "plants"


plants = PlantRepository()

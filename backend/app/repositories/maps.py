from __future__ import annotations

from app.repository import Repository


class MapRepository(Repository):
    collection_name = "maps"


maps = MapRepository()

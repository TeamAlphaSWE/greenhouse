from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from app.map_regions import join_regions
from app.repositories.maps import maps as map_repository
from app.repositories.zones import zones as zone_repository

maps = Blueprint("maps", __name__, url_prefix="/api/v1/maps")


@maps.get("")
def list_maps():
    try:
        map_list = map_repository.find(projection={"name": 1}, sort=[("name", 1)])
    except PyMongoError:
        current_app.logger.exception("Failed to load maps")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({
        "maps": map_list,
        "total": len(map_list),
    })


@maps.get("/<map_id>")
def get_map(map_id):
    if map_repository._to_object_id(map_id) is None:
        return jsonify({"error": "Invalid map id"}), 400

    try:
        map_doc = map_repository.get(map_id)
        if map_doc is None:
            return jsonify({"error": "Map not found"}), 404

        zone_list = zone_repository.find()
    except PyMongoError:
        current_app.logger.exception("Failed to load map")
        return jsonify({"error": "Unexpected server error"}), 500

    map_doc["regions"] = join_regions(map_doc.get("regions", []), zone_list)

    return jsonify({"map": map_doc})


@maps.post("")
def create_map():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required"}), 400

    image_path = data.get("image_path")
    if not isinstance(image_path, str) or not image_path.strip():
        return jsonify({"error": "image_path is required"}), 400

    now = datetime.now(timezone.utc)
    try:
        created = map_repository.create({
            "name": name.strip(),
            "image_path": image_path.strip(),
            "regions": [],
            "created_at": now,
            "updated_at": now,
        })
    except PyMongoError:
        current_app.logger.exception("Failed to create map")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"map": created}), 201


def _parse_regions(raw_regions):
    """Validate shape/types and assign ids. `area_id` is a write-only hint
    here (it drives the area<->region link below); it's never stored on
    the region itself. A region with no `id` and no `area_id` is a filler
    shape (not linkable to anything).

    Returns (regions, links, error_message) where regions is what gets
    stored in maps.regions and links is {area_id: region_id} for every
    region this request ties to an area.
    """
    if not isinstance(raw_regions, list):
        return None, None, "regions must be a list"

    regions = []
    links = {}
    for region in raw_regions:
        if not isinstance(region, dict):
            return None, None, "each region must be an object"

        entry = {}
        for key in ("x", "y", "w", "h"):
            value = region.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None, None, f"region {key} must be a number"
            entry[key] = value

        if region.get("text") is not None:
            text = region.get("text")
            if not isinstance(text, str) or not text.strip():
                return None, None, "region text must be a non-empty string"
            entry["text"] = text.strip()

        if region.get("label") is not None:
            label = region.get("label")
            if not isinstance(label, str) or not label.strip():
                return None, None, "region label must be a non-empty string"
            entry["label"] = label.strip()

        region_id = None
        if region.get("id") is not None:
            region_id = map_repository._to_object_id(region.get("id"))
            if region_id is None:
                return None, None, "region id must be a valid ObjectId"

        area_oid = None
        if region.get("area_id") is not None:
            area_oid = map_repository._to_object_id(region.get("area_id"))
            if area_oid is None:
                return None, None, "region area_id must be a valid ObjectId"
            if region_id is None:
                region_id = ObjectId()

        if region_id is not None:
            entry["id"] = region_id
        regions.append(entry)

        if area_oid is not None:
            links[area_oid] = region_id

    return regions, links, None


@maps.put("/<map_id>/regions")
def update_map_regions(map_id):
    map_oid = map_repository._to_object_id(map_id)
    if map_oid is None:
        return jsonify({"error": "Invalid map id"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    regions, links, error = _parse_regions(data.get("regions"))
    if error:
        return jsonify({"error": error}), 400

    try:
        existing = map_repository.get(map_id)
        if existing is None:
            return jsonify({"error": "Map not found"}), 404

        zone_list = zone_repository.find()
        area_ids = {area["id"] for zone in zone_list for area in zone.get("areas", [])}

        if any(area_id not in area_ids for area_id in links):
            return jsonify({"error": "region area_id does not match any zone's area"}), 400

        previous_region_ids = {r["id"] for r in existing.get("regions", []) if "id" in r}
        areas_to_unlink = [
            area["id"]
            for zone in zone_list
            for area in zone.get("areas", [])
            if area.get("region_id") in previous_region_ids and area["id"] not in links
        ]

        for area_id in areas_to_unlink:
            zone_repository.unlink_area_region(area_id)
        for area_id, region_id in links.items():
            zone_repository.link_area_to_region(area_id, region_id, map_oid)

        updated = map_repository.update(map_id, {
            "regions": regions,
            "updated_at": datetime.now(timezone.utc),
        })
    except PyMongoError:
        current_app.logger.exception("Failed to update map regions")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"map": updated})

"""Join a map's regions with their area and zone names.

The link is owned by the area, not the region: an area that's been drawn
on a map carries that region's id as `region_id` (areas are nested inside
their zone document, not their own collection, the same relationship
area_overview.py already joins through). A region with no `id` is a
filler shape (a corridor, an office) with nothing to link to; it only
ever renders with whatever `text` it was given.
"""
from __future__ import annotations


def join_regions(regions, zones):
    """regions: a map's regions list. zones: GET /api/v1/zones shape."""
    region_lookup = {
        area["region_id"]: {
            "area_name": area.get("name"),
            "zone_id": zone["id"],
            "zone_name": zone.get("name"),
        }
        for zone in zones
        for area in zone.get("areas", [])
        if area.get("region_id")
    }
    empty = {"area_name": None, "zone_id": None, "zone_name": None}

    return [
        {**region, **region_lookup.get(region.get("id"), empty)}
        for region in regions
    ]

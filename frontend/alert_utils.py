"""Turn alert records from the backend into the text shown on the Alert page."""

UNITS = {"temperature": "°C", "humidity": "%"}
DETAIL_UNITS = {"temperature": "°C", "humidity": " percentage points"}


def describe_alert(alert, zones):
    """Return the text for one alert card.

    {"title", "message", "detail", "direction", "value", "difference"}
    direction is "above", "below", or None when the limit can't be found.

    zones is the list from GET /api/v1/zones. The limit comes from the area's
    target_conditions. If the area or its limits can't be found, detail falls
    back to the message the backend saved with the alert.
    """
    alert_type = alert.get("type", "")
    label = alert_type.capitalize()
    unit = UNITS.get(alert_type, "")
    detail_unit = DETAIL_UNITS.get(alert_type, "")

    zone = next((z for z in zones if z.get("id") == alert.get("zone_id")), None)
    zone_name = zone.get("name", "Unknown zone") if zone else "Unknown zone"

    area = None
    if zone:
        area = next((a for a in zone.get("areas", []) if a.get("id") == alert.get("area_id")), None)
    limits = (area or {}).get("target_conditions", {}).get(alert_type, {})

    value = alert.get("value")
    low, high = limits.get("min"), limits.get("max")

    if high is not None and value > high:
        direction = "above"
        difference = f"+{value - high:g}{unit}"
        message = f"{label} is too high"
        detail = f"{label} was {value - high:g}{detail_unit} above the limit"
    elif low is not None and value < low:
        direction = "below"
        difference = f"-{low - value:g}{unit}"
        message = f"{label} is too low"
        detail = f"{label} was {low - value:g}{detail_unit} below the limit"
    else:
        direction = None
        difference = None
        message = f"{label} was out of range"
        detail = alert.get("message", "")

    return {
        "title": f"{zone_name} - {label} Alert",
        "message": message,
        "detail": detail,
        "direction": direction,
        "value": f"{value:g}{unit}",
        "difference": difference,
    }

from alert_utils import describe_alert

ZONES = [{
    "id": "z1",
    "name": "Zone 1",
    "areas": [{
        "id": "a1",
        "name": "Area 1",
        "target_conditions": {
            "temperature": {"min": 18, "max": 30},
            "humidity": {"min": 45, "max": 60},
        },
    }],
}]


def _alert(alert_type, value, zone_id="z1", area_id="a1"):
    return {
        "type": alert_type,
        "value": value,
        "zone_id": zone_id,
        "area_id": area_id,
        "message": f"{alert_type} out of range: {value}",
    }


def test_describe_alert_above_limit():
    text = describe_alert(_alert("temperature", 35), ZONES)

    assert text == {
        "title": "Zone 1 - Temperature Alert",
        "message": "Temperature is too high",
        "detail": "Temperature was 5°C above the limit",
        "direction": "above",
        "value": "35°C",
        "difference": "+5°C",
    }


def test_describe_alert_below_limit():
    text = describe_alert(_alert("humidity", 35), ZONES)

    assert text["message"] == "Humidity is too low"
    assert text["detail"] == "Humidity was 10 percentage points below the limit"
    assert text["direction"] == "below"
    assert text["value"] == "35%"
    assert text["difference"] == "-10%"


def test_describe_alert_unknown_area_falls_back_to_saved_message():
    text = describe_alert(_alert("temperature", 35, zone_id="missing"), ZONES)

    assert text["title"] == "Unknown zone - Temperature Alert"
    assert text["detail"] == "temperature out of range: 35"
    assert text["direction"] is None

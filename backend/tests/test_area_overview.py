from datetime import datetime, timedelta, timezone

from app.area_overview import area_status, build_overview, summarize

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
CONFIG = {"SENSOR_REPORT_INTERVAL_MINUTES": 5, "SENSOR_STALE_FACTOR": 2}


def area(temperature_min=18, temperature_max=26):
    return {
        "id": "area-1",
        "name": "Tomatoes",
        "target_conditions": {"temperature": {"min": temperature_min, "max": temperature_max}},
    }


def reading(temperature, minutes_old):
    return {
        "timestamp": NOW - timedelta(minutes=minutes_old),
        "values": [{"type": "temperature", "value": temperature}],
    }


def test_normal_unaffected_by_new_warning_state():
    status = area_status(area(), reading(22.0, minutes_old=2), CONFIG, NOW)

    assert status["state"] == "normal"


def test_out_of_range_unaffected_by_new_warning_state():
    status = area_status(area(), reading(30.0, minutes_old=2), CONFIG, NOW)

    assert status["state"] == "out_of_range"


def test_offline_unknown_unaffected_when_sensor_never_reported():
    status = area_status(area(), None, CONFIG, NOW)

    assert status["state"] == "offline_unknown"


def test_offline_unknown_unaffected_when_no_target_conditions():
    status = area_status({"id": "area-1", "name": "Tomatoes"}, reading(22.0, minutes_old=2), CONFIG, NOW)

    assert status["state"] == "offline_unknown"


def test_warning_for_stale_in_range_reading():
    status = area_status(area(), reading(22.0, minutes_old=11), CONFIG, NOW)

    assert status["state"] == "warning"


def test_out_of_range_wins_over_warning_when_both_apply():
    status = area_status(area(), reading(30.0, minutes_old=11), CONFIG, NOW)

    assert status["state"] == "out_of_range"


def test_without_config_staleness_is_never_checked():
    status = area_status(area(), reading(22.0, minutes_old=11), config=None, now=NOW)

    assert status["state"] == "normal"


def test_build_overview_threads_config_and_now_into_every_area():
    zones = [{"id": "zone-1", "name": "North", "areas": [area()]}]
    latest_by_area = {"area-1": reading(22.0, minutes_old=11)}

    overview = build_overview(zones, latest_by_area, CONFIG, NOW)

    assert overview[0]["areas"][0]["state"] == "warning"


def test_summarize_counts_warning_areas():
    overview = [{"id": "zone-1", "name": "North", "areas": [
        area_status(area(), reading(22.0, minutes_old=11), CONFIG, NOW),
        area_status(area(), reading(22.0, minutes_old=2), CONFIG, NOW),
    ]}]

    summary = summarize(overview)

    assert summary == {"total": 2, "normal": 1, "out_of_range": 0, "warning": 1, "offline_unknown": 0}

import pandas as pd

from sensor_api import readings_to_frame


def test_readings_to_frame_one_column_per_type_sorted_by_date():
    readings = [
        {"timestamp": "2026-10-26T12:05:00+00:00",
         "values": [{"type": "temperature", "value": 24.0}, {"type": "battery", "value": 80}]},
        {"timestamp": "2026-10-26T12:00:00+00:00",
         "values": [{"type": "temperature", "value": 23.4}, {"type": "humidity", "value": 50}]},
    ]

    frame = readings_to_frame(readings)

    assert list(frame.columns) == ["Date", "temperature", "humidity", "battery"]
    assert list(frame["temperature"]) == [23.4, 24.0]
    assert frame["humidity"].iloc[0] == 50
    assert pd.isna(frame["humidity"].iloc[1])
    assert frame["Date"].is_monotonic_increasing


def test_readings_to_frame_empty():
    frame = readings_to_frame([])

    assert frame.empty
    assert list(frame.columns) == ["Date", "temperature", "humidity", "battery"]
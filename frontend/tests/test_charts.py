import pandas as pd

from charts import time_series_chart


def _frame():
    return pd.DataFrame({
        "Date": pd.to_datetime(["2026-11-05T19:42:00Z", "2026-11-06T01:42:30Z"], utc=True),
        "Temperature": [21.0, 22.0],
        "Humidity": [84.0, None],
    })


def test_tooltip_shows_date_and_time_utc():
    spec = time_series_chart(_frame(), ["Temperature", "Humidity"]).to_dict()

    tooltip = [t["field"] for t in spec["layer"][1]["encoding"]["tooltip"]]
    assert tooltip == ["Time (UTC)", "Reading", "Value"]
    rows = list(spec["datasets"].values())[0]
    assert sorted({r["Time (UTC)"] for r in rows}) == ["2026-11-05 19:42 UTC", "2026-11-06 01:42 UTC"]


def test_missing_values_are_skipped():
    spec = time_series_chart(_frame(), ["Temperature", "Humidity"]).to_dict()

    rows = list(spec["datasets"].values())[0]
    assert len(rows) == 3


def test_single_series_chart():
    spec = time_series_chart(_frame(), ["Temperature"]).to_dict()

    rows = list(spec["datasets"].values())[0]
    assert {r["Reading"] for r in rows} == {"Temperature"}

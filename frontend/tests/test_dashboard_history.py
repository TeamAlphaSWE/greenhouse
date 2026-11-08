"""Run: python -m unittest discover -s frontend/tests -p test_dashboard_history.py."""
import ast
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
import unittest
from unittest.mock import patch
import altair as alt
import pandas as pd
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[1] / "views" / "landing.py"
# Load pure transformation functions without running a Streamlit page or HTTP calls.
tree = ast.parse(PAGE.read_text())
helpers = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                          and n.name in {"history_frame", "filter_history", "history_chart"}], type_ignores=[])
namespace = {"pd": pd, "alt": alt}
exec(compile(helpers, str(PAGE), "exec"), namespace)
history_frame = namespace["history_frame"]
filter_history = namespace["filter_history"]
history_chart = namespace["history_chart"]


def reading(sensor, when, temperature=22, humidity=60):
    return {"sensor_id": sensor, "timestamp": when,
            "values": [{"type": "temperature", "value": temperature},
                       {"type": "humidity", "value": humidity}]}


class HistoryTests(unittest.TestCase):
    def test_sensor_identity_and_bad_rows(self):
        frame = history_frame([
            reading("A", "2026-11-02T10:00:00Z"),
            reading("B", "2026-11-02T10:00:00Z", 99),
            reading("A", "invalid"),
            reading("A", "2026-11-02T09:00:00Z", "21.5"),
        ], "A")
        self.assertEqual(list(frame.Temperature), [21.5, 22])
        self.assertEqual(list(frame.Humidity), [60, 60])

    def test_custom_end_day_and_timezone(self):
        frame = history_frame([
            reading("A", "2026-11-02T00:00:00Z"),
            reading("A", "2026-11-02T18:59:59-05:00"),
            reading("A", "2026-11-03T00:00:00Z"),
        ], "A")
        result = filter_history(frame, pd.Timestamp("2026-11-02", tz="UTC"),
                                pd.Timestamp("2026-11-03", tz="UTC"))
        self.assertEqual(len(result), 2)

    def test_predefined_boundaries(self):
        now = pd.Timestamp("2026-11-04T12:00:00Z")
        for days in [1, 7, 30]:
            with self.subTest(days=days):
                start = now - timedelta(days=days)
                frame = history_frame([
                    reading("A", (start - timedelta(seconds=1)).isoformat()),
                    reading("A", start.isoformat()),
                    reading("A", (now - timedelta(seconds=1)).isoformat()),
                    reading("A", now.isoformat()),
                ], "A")
                self.assertEqual(len(filter_history(frame, start, now)), 2)
                self.assertEqual(len(filter_history(frame)), 4)

    def test_empty_history(self):
        self.assertTrue(filter_history(history_frame([], "A")).empty)

    def test_missing_measurement_keeps_other_line(self):
        row = reading("A", "2026-11-02T00:00:00Z")
        row["values"].pop()
        result = history_frame([row], "A")
        self.assertEqual(result.Temperature.iloc[0], 22)
        self.assertTrue(pd.isna(result.Humidity.iloc[0]))
        
    def test_chart_tooltip_shows_date_and_time_utc(self):
        frame = history_frame([
            reading("A", "2026-11-05T19:42:00Z", 21, 84),
            reading("A", "2026-11-06T01:42:30Z", 22, 80),
        ], "A")
        spec = history_chart(frame).to_dict()

        tooltip = [t["field"] for t in spec["layer"][1]["encoding"]["tooltip"]]
        self.assertEqual(tooltip, ["Time (UTC)", "Reading", "Value"])
        rows = list(spec["datasets"].values())[0]
        self.assertEqual(sorted({r["Time (UTC)"] for r in rows}),
                         ["2026-11-05 19:42 UTC", "2026-11-06 01:42 UTC"])


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.urls = []
        now = datetime.now(timezone.utc)
        self.records = {
            sensor: [reading(sensor, (now - timedelta(days=days)).isoformat(), temp)
                     for days, temp in [(0.1, base), (3, base+1), (20, base+2)]]
            for sensor, base in [("A", 20), ("B", 30)]
        }

    def get(self, url, **kwargs):
        self.urls.append(url)
        class Response:
            def raise_for_status(self): pass
            def json(inner):
                if url.endswith('/sensors'):
                    return {"sensors": [{"id": s, "name": s, "status": "active"}
                                        for s in ["A", "B"]]}
                return {"sensor_data": self.records[url.rsplit('/', 1)[-1]]}
        return Response()

    def test_controls_sensor_change_and_single_chart(self):
        with patch("requests.get", side_effect=self.get):
            app = AppTest.from_file(str(PAGE)).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("vega_lite_chart")), 1)
            self.assertIn("2 readings", app.caption[-1].value)
            app.selectbox(key="trend_range").select("24 hours").run()
            self.assertIn("1 readings", app.caption[-1].value)
            app.selectbox(key="trend_sensor").select("B").run()
            self.assertTrue(self.urls[-1].endswith("/sensor_data/B"))
            self.assertIn("Sensor: B", app.caption[0].value)
            app.selectbox(key="trend_range").select("All history").run()
            self.assertIn("3 readings", app.caption[-1].value)
            self.assertEqual(len(app.get("vega_lite_chart")), 1)
            app.selectbox(key="trend_range").select("Custom").run()
            app.date_input[0].set_value((date(2020,1,1), date(2020,1,2))).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("vega_lite_chart")), 0)
            self.assertIn("No sensor data", app.info[0].value)

    def test_api_failure(self):
        import requests
        with patch("requests.get", side_effect=requests.ConnectionError("offline")):
            app = AppTest.from_file(str(PAGE)).run()
            self.assertFalse(app.exception)
            self.assertIn("Unable to load sensors", app.error[0].value)


if __name__ == "__main__":
    unittest.main()

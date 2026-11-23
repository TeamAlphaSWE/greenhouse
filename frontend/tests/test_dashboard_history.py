"""Run: python -m unittest discover -s frontend/tests -p test_dashboard_history.py."""
import ast
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[1] / "views" / "landing.py"
# Load pure transformation functions without running a Streamlit page or HTTP calls.
tree = ast.parse(PAGE.read_text())
helpers = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                          and n.name in {"history_frame", "filter_history"}], type_ignores=[])
namespace = {"pd": pd}
exec(compile(helpers, str(PAGE), "exec"), namespace)
history_frame = namespace["history_frame"]
filter_history = namespace["filter_history"]


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


def pin_segmented_controls(app):
    """Re-pin every segmented_control's current value before any run().

    AppTest's button_group wrapper (segmented_control's underlying widget) only
    reads a widget's *current* session value as a list when you've just set it
    yourself; for selection_mode="single" that value is actually a bare string,
    so any OTHER segmented_control left untouched gets its string value iterated
    character by character on the next run and crashes. Re-pinning every
    segmented_control's current value (as a singleton list) before any run()
    sidesteps that.
    """
    for widget in app.get("button_group"):
        widget.set_value([widget.value])


def select_segmented(app, key, value):
    pin_segmented_controls(app)
    app.button_group(key=key).set_value([value])
    app.run()


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
                if url.endswith('/areas/overview'):
                    return {"zones": [], "summary": {"total": 0, "normal": 0,
                                                     "out_of_range": 0, "offline_unknown": 0}}
                if url.endswith('/maps'):
                    return {"maps": []}
                if '/sensor_data/' in url:
                    return {"sensor_data": self.records[url.rsplit('/', 1)[-1]]}
                raise AssertionError(f"unexpected GET {url}")
        return Response()

    def test_controls_sensor_change_and_single_chart(self):
        with patch("requests.get", side_effect=self.get):
            app = AppTest.from_file(str(PAGE)).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("arrow_vega_lite_chart")), 1)
            self.assertIn("2 readings", app.caption[-1].value)
            select_segmented(app, "trend_range", "24 hours")
            self.assertIn("1 readings", app.caption[-1].value)
            select_segmented(app, "trend_sensor", "B")
            self.assertTrue(self.urls[-1].endswith("/sensor_data/B"))
            self.assertIn("Sensor: B", app.caption[0].value)
            select_segmented(app, "trend_range", "All history")
            self.assertIn("3 readings", app.caption[-1].value)
            self.assertEqual(len(app.get("arrow_vega_lite_chart")), 1)
            select_segmented(app, "trend_range", "Custom")
            pin_segmented_controls(app)
            app.date_input[0].set_value((date(2020,1,1), date(2020,1,2)))
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("arrow_vega_lite_chart")), 0)
            self.assertTrue(any("No sensor data" in i.value for i in app.info))

    def test_api_failure(self):
        import requests
        with patch("requests.get", side_effect=requests.ConnectionError("offline")):
            app = AppTest.from_file(str(PAGE)).run()
            self.assertFalse(app.exception)
            self.assertIn("Unable to load sensors", app.error[0].value)


if __name__ == "__main__":
    unittest.main()

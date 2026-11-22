from pathlib import Path
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[1] / "views" / "sensors.py"

SENSORS = [
    {"id": "s1", "name": "Good", "hardware_id": "h1", "status": "active"},
    {"id": "s2", "name": "Old", "hardware_id": "h2", "status": "active"},
    {"id": "s3", "name": "Silent", "hardware_id": "h3", "status": "active"},
    {"id": "s4", "hardware_id": "h4", "status": "pending"},
]
HEALTH = [
    {"id": "s1", "name": "Good", "status": "healthy", "stale": False, "low_battery": False,
     "battery": 80, "last_seen": "2026-11-15T12:00:00+00:00"},
    {"id": "s2", "name": "Old", "status": "warning", "stale": True, "low_battery": True,
     "battery": 10, "last_seen": "2026-11-14T12:00:00+00:00"},
    {"id": "s3", "name": "Silent", "status": "unknown", "stale": False, "low_battery": False,
     "battery": None, "last_seen": None},
    {"id": "s4", "name": "h4", "status": "unknown", "stale": False, "low_battery": False,
     "battery": None, "last_seen": None},
]


class Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def fake_get(health_error=False):
    def get(url, **kwargs):
        if url.endswith("/sensors/health"):
            if health_error:
                raise requests.ConnectionError("down")
            return Response({"sensors": HEALTH})
        if url.endswith("/sensors"):
            return Response({"sensors": SENSORS})
        if url.endswith("/zones"):
            return Response({"zones": []})
        if "/sensor_data/" in url:
            return Response({"sensor_data": []})
        raise AssertionError(f"unexpected GET {url}")
    return get


class SensorHealthSectionTests(unittest.TestCase):
    def test_counts_skip_pending_sensors(self):
        with patch("requests.get", side_effect=fake_get()):
            app = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(app.exception)
        metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(metrics["Healthy"], "1")
        self.assertEqual(metrics["Warning"], "1")
        self.assertEqual(metrics["Unknown"], "1")

    def test_table_lists_only_affected_sensors_warnings_first(self):
        with patch("requests.get", side_effect=fake_get()):
            app = AppTest.from_file(str(PAGE)).run()
        table = app.dataframe[0].value
        self.assertEqual(list(table["Sensor"]), ["Old", "Silent"])
        self.assertEqual(list(table["Problem"]), ["Stale, Low battery", "No readings yet"])
        self.assertEqual(list(table["Battery"]), ["10%", "—"])
        self.assertEqual(table["Last reading"].iloc[1], "—")

    def test_health_error_shows_message(self):
        with patch("requests.get", side_effect=fake_get(health_error=True)):
            app = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(app.exception)
        self.assertIn("Could not load sensor health.", [e.value for e in app.error])


if __name__ == "__main__":
    unittest.main()

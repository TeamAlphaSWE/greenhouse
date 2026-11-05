"""Run: python -m unittest discover -s frontend/tests -p test_activate_sensor.py."""
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[1] / "views" / "activate_sensor.py"

SENSOR = {
    "id": "s1", "hardware_id": "shellyhtg3-e4b3233085e8",
    "status": "pending", "created_at": "2026-11-01T10:00:00Z",
}
ZONES = [
    {"id": "z1", "name": "Zone A", "areas": [
        {"id": "a1", "name": "Area A1",
         "target_conditions": {"temperature": {"min": 18, "max": 26}, "humidity": {"min": 40, "max": 60}}},
        {"id": "a2", "name": "Area A2",
         "target_conditions": {"temperature": {"min": 15, "max": 20}, "humidity": {"min": 40, "max": 60}}},
    ]},
    {"id": "z2", "name": "Zone B", "areas": [
        {"id": "b1", "name": "Area B1",
         "target_conditions": {"temperature": {"min": 10, "max": 15}, "humidity": {"min": 30, "max": 50}}},
    ]},
]


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise __import__("requests").HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


def get(url, **kwargs):
    if url.endswith("/sensors"):
        return Response(payload={"sensors": [SENSOR]})
    if url.endswith("/zones"):
        return Response(payload={"zones": ZONES})
    if url.endswith("/latest"):
        return Response(status_code=404)
    raise AssertionError(f"unexpected GET {url}")


class ActivateSensorTests(unittest.TestCase):
    def run_app(self):
        app = AppTest.from_file(str(PAGE))
        app.session_state["activating_sensor_id"] = SENSOR["id"]
        return app.run()

    def test_no_sensor_selected_prompts_to_pick_one(self):
        with patch("requests.get", side_effect=get), patch("streamlit.page_link"):
            app = AppTest.from_file(str(PAGE)).run()
        self.assertFalse(app.exception)
        self.assertIn("Select a sensor", app.info[0].value)

    def test_zone_selection_narrows_area_options(self):
        with patch("requests.get", side_effect=get):
            app = self.run_app()
            self.assertFalse(app.exception)
            areas = [s for s in app.selectbox if s.label == "Area"][0]
            self.assertEqual(list(areas.options), ["Area A1", "Area A2"])

            zone_select = [s for s in app.selectbox if s.label == "Zone"][0]
            zone_select.set_value("z2").run()
            self.assertFalse(app.exception)
            areas = [s for s in app.selectbox if s.label == "Area"][0]
            self.assertEqual(list(areas.options), ["Area B1"])

    def test_submit_patches_name_and_area_id_only(self):
        with patch("requests.get", side_effect=get), \
             patch("requests.patch", return_value=Response(payload={"sensor": {"id": "s1"}})) as mock_patch, \
             patch("streamlit.switch_page") as mock_switch:
            app = self.run_app()
            name_input = [t for t in app.text_input if t.label == "Sensor name"][0]
            name_input.set_value("Greenhouse East").run()
            self.assertFalse(app.exception)

            button = [b for b in app.button if b.label == "Activate sensor"][0]
            button.click().run()

        self.assertFalse(app.exception)
        mock_patch.assert_called_once()
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["json"], {"name": "Greenhouse East", "area_id": "a1"})
        self.assertNotIn("zone_id", kwargs["json"])
        mock_switch.assert_called_once_with("views/sensors.py")


if __name__ == "__main__":
    unittest.main()

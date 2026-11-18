from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from units import CELSIUS, FAHRENHEIT, c_to_f, to_display, to_local, viewer_timezone


def test_c_to_f():
    assert c_to_f(0) == 32
    assert c_to_f(100) == 212
    assert c_to_f(-40) == -40


def test_to_display_celsius_unchanged():
    assert to_display(23.4, CELSIUS) == 23.4


def test_to_display_fahrenheit_converts():
    assert to_display(25, FAHRENHEIT) == 77


def test_to_display_none_stays_none():
    assert to_display(None, FAHRENHEIT) is None


def test_to_display_series():
    result = to_display(pd.Series([0.0, 100.0]), FAHRENHEIT)
    assert list(result) == [32.0, 212.0]


def test_viewer_timezone_defaults_to_utc_outside_a_browser_session():
    assert viewer_timezone() == "UTC"


def test_viewer_timezone_uses_browser_context():
    with patch("streamlit.context") as context:
        context.timezone = "America/New_York"
        assert viewer_timezone() == "America/New_York"


def test_to_local_converts_utc_to_viewer_timezone():
    dt = datetime(2026, 11, 5, 19, 42, tzinfo=timezone.utc)
    with patch("units.viewer_timezone", return_value="America/New_York"):
        local = to_local(dt)
    assert local.strftime("%Y-%m-%d %H:%M %Z") == "2026-11-05 14:42 EST"


def test_to_local_none_stays_none():
    assert to_local(None) is None

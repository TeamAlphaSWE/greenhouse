import pandas as pd

from units import CELSIUS, FAHRENHEIT, c_to_f, to_display


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

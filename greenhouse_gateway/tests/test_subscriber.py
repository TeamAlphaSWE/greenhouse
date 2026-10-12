# tests/test_subscriber.py
import json
from subscriber import normalize
from pathlib import Path
SAMPLE_DATA = Path(__file__).parent / "mock_shelly_reading.json"
def test_normalize_real_payload():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)
    assert r["sensor_id"] == "shellyhtg3-e4b3233085e8"
    assert r["sensor_name"] == "greenhouse-ht1"
    assert r["temp_c"] == 24.4
    assert r["humidity"] == 45.9
    assert r["battery"] == 66
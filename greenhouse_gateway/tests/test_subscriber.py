# tests/test_subscriber.py
import json
import subscriber
from subscriber import normalize, build_payload
from pathlib import Path
from unittest.mock import MagicMock, patch


SAMPLE_DATA = Path(__file__).parent / "mock_shelly_reading.json"
FAKE_OID = "6ac430e14eb645800db1771f"
FAKE_MAC = "shellyhtg3-e4b3233085e8"
FAKE_SENSOR_IDS = {FAKE_MAC: FAKE_OID}

def test_normalize_real_payload():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)
    assert r["mac"] == "shellyhtg3-e4b3233085e8"
    assert r["temperature"] == 24.4
    assert r["humidity"] == 45.9
    assert r["battery"] == 66

def test_build_payload_normal():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)
    payload = build_payload(r, FAKE_OID)
    assert payload == {
        "sensor_id": FAKE_OID,
        "values": [
            {"type": "temperature", "value": 24.4},
            {"type": "humidity", "value": 45.9},
            {"type": "battery", "value": 66},
        ],  
    }

    r2 = {"temperature": 0, "humidity": 0, "battery": 0}
    payload2 = build_payload(r2, FAKE_OID)
    assert payload2 == {
        "sensor_id": FAKE_OID,
        "values": [
            {"type": "temperature", "value": 0},
            {"type": "humidity", "value": 0},
            {"type": "battery", "value": 0},
        ],  
    } 


def test_build_payload_empty():
    r1 = {}
    payload = build_payload(r1, FAKE_OID)
    assert payload is None

    r2 = {"temperature": None, "humidity": None, "battery": None}
    payload2 = build_payload(r2, FAKE_OID)
    assert payload2 is None


def test_build_payload_partial():
    r1 = {"temperature": None, "humidity": 45.9, "battery": None}
    payload = build_payload(r1, FAKE_OID)
    assert payload == {
        "sensor_id": FAKE_OID,
        "values": [{"type": "humidity", "value": 45.9}],
    }

    r2 = {"temperature": None, "humidity": 45.9, "battery": 66}
    payload2 = build_payload(r2, FAKE_OID)
    assert payload2 == {
        "sensor_id": FAKE_OID,
        "values": [{"type": "humidity", "value": 45.9}, {"type": "battery", "value": 66}],
    }


def test_post_reading_success(monkeypatch):
    monkeypatch.setattr(subscriber, "SENSOR_IDS", FAKE_SENSOR_IDS)
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)

    response = MagicMock(status_code=201)
    response.json.return_value = {"sensor_data": {"id": "abc123"}}
    with patch("subscriber.requests.post", return_value=response) as mock_post:
        subscriber.post_reading(r)

    mock_post.asser_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == f"{subscriber.BACKEND_URL}/api/v1/sensor_data"
    assert kwargs["json"] == build_payload(r, FAKE_OID)
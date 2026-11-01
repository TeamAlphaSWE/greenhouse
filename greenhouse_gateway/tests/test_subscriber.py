# tests/test_subscriber.py
import json
import subscriber
from subscriber import normalize, build_payload
from pathlib import Path
from unittest.mock import MagicMock, patch
import requests

SAMPLE_DATA = Path(__file__).parent / "mock_shelly_reading.json"

def test_normalize_real_payload():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)
    assert r["hardware_id"] == "shellyhtg3-e4b3233085e8"
    assert r["temperature"] == 24.4
    assert r["humidity"] == 45.9
    assert r["battery"] == 66

def test_build_payload_normal():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)
    payload = build_payload(r)
    assert payload == {
        "hardware_id": r["hardware_id"],
        "values": [
            {"type": "temperature", "value": 24.4},
            {"type": "humidity", "value": 45.9},
            {"type": "battery", "value": 66},
        ],  
    }

    r2 = {"hardware_id": "shellyhtg3-e4b3233085e8", "temperature": 0, "humidity": 0, "battery": 0}
    payload2 = build_payload(r2)
    assert payload2 == {
        "hardware_id": "shellyhtg3-e4b3233085e8",
        "values": [
            {"type": "temperature", "value": 0},
            {"type": "humidity", "value": 0},
            {"type": "battery", "value": 0},
        ],  
    } 


def test_build_payload_empty():
    r1 = {}
    payload = build_payload(r1)
    assert payload is None

    r2 = {"hardware_id": None, "temperature": None, "humidity": None, "battery": None}
    payload2 = build_payload(r2)
    assert payload2 is None


def test_build_payload_partial():
    r1 = {"hardware_id": "shellyhtg3-e4b3233085e8", "temperature": None, "humidity": 45.9, "battery": None}
    payload = build_payload(r1)
    assert payload == {
        "hardware_id": "shellyhtg3-e4b3233085e8",
        "values": [{"type": "humidity", "value": 45.9}],
    }

    r2 = {"hardware_id": "shellyhtg3-e4b3233085e8", "temperature": None, "humidity": 45.9, "battery": 66}
    payload2 = build_payload(r2)
    assert payload2 == {
        "hardware_id": "shellyhtg3-e4b3233085e8",
        "values": [{"type": "humidity", "value": 45.9}, {"type": "battery", "value": 66}],
    }


def test_post_reading_success():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)

    response = MagicMock(status_code=201)
    response.json.return_value = {"sensor_data": {"id": "abc123"}}
    with patch("subscriber.requests.post", return_value=response) as mock_post:
        subscriber.post_reading(r)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == f"{subscriber.BACKEND_URL}/api/v1/sensor_data"
    assert kwargs["json"] == build_payload(r)

def test_post_reading_network_error_does_not_crash():
    data = json.load(open(SAMPLE_DATA))
    r = normalize(data)

    with patch("subscriber.requests.post", side_effect=requests.ConnectionError("backend down")):
        subscriber.post_reading(r)   

#tests subscriber functions full pipeline together
def test_on_message_posts_reading():
    msg = MagicMock(payload=SAMPLE_DATA.read_bytes(), topic="shellyhtg3-e4b3233085e8/events/rpc")

    response = MagicMock(status_code=201)
    response.json.return_value = {"sensor_data": {"id": "abc123"}}
    with patch("subscriber.requests.post", return_value=response) as mock_post:
        subscriber.on_message(None, None, msg)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    args, kwargs = mock_post.call_args
    assert args[0] == f"{subscriber.BACKEND_URL}/api/v1/sensor_data"    
    assert kwargs["json"] == {
        "hardware_id": "shellyhtg3-e4b3233085e8",
        "values": [
            {"type": "temperature", "value": 24.4},
            {"type": "humidity", "value": 45.9},
            {"type": "battery", "value": 66},
        ],
    }


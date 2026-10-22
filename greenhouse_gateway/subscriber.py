# greenhouse_gateway/subscriber.py
#
# WHAT THIS FILE DOES:
#   Shelly sensors send their readings to Mosquitto (the MQTT broker running on greenhouse MacBook).
#   This script connects to Mosquitto, listens for those readings, pulls out the values we
#   care about, and prints each reading.

from config import MQTT_HOST, MQTT_PORT, BACKEND_URL, SENSOR_IDS
import json
from datetime import datetime, timezone       
import paho.mqtt.client as mqtt             # type: ignore
import requests
import logging

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5
MEASUREMENTS = ("temperature", "humidity", "battery")

#input -> dict returned by normalize() 
def build_payload(reading, sensor_oid):
    values = []
    for key in MEASUREMENTS:
        value = reading.get(key)
        #skips adding anything with incorrect types or no value 
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        values.append({"type":key, "value": value})

    #skips empty readings from building payload
    if not values:
        return None
    
    return {
        "sensor_id": sensor_oid,
        "values": values,
    }

def resolve_sensor_id(mac):
    sensor_oid = SENSOR_IDS.get(mac)
    if sensor_oid is None:
        logger.warning("No sensor registered for %s", mac)
    return sensor_oid
    
def post_reading(reading):
    sensor_oid = resolve_sensor_id(reading["mac"])
    if sensor_oid is None:
        return #sensor object id not logged in greenhouse_gateway/config.py
    
    payload = build_payload(reading, sensor_oid)
    if payload is None:
        logger.warning("No usable values in reading from %s", reading["mac"])
        return
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/sensor_data", json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logger.error("POST to backend failed: %s", e)
        return
    
    if response.status_code == 201:
        logger.info("Saved reading %s for sensor %s",
                    response.json()["sensor_data"]["id"], sensor_oid)
    elif response.status_code == 400:
        logger.error("Backend rejected payload %s: %s", payload, response.text)
    else:
        logger.error("Backend error %s: %s", response.status_code, response.text)

def normalize(data):
    # All the sensor values live under "params"
    p = data["params"]
    return {
        "mac": data["src"], #based on device MAC address -> guaranteed to be unique
        "temperature": p.get("temperature:0", {}).get("tC"),
        "humidity": p.get("humidity:0", {}).get("rh"),
        "battery": p.get("devicepower:0", {}).get("battery", {}).get("percent"),
    }


# ---------------------------------------------------------------------------------------------
# CALLBACK 1: runs automatically every time we connect (or reconnect) to the broker.
#
# You never call this function yourself. paho calls it for you and always passes these 5 values:
#   client              - the MQTT client object
#   userdata(unused)    - optional custom data you can attach to the client
#   flags(unused)       - extra details about the connection
#   reason_code(unused) - whether the connection succeeded (0 / "Success") or why it failed
#   properties(unused ) - extra MQTT v5 info
#
# paho requires all 5 parameters to be listed, even the ones we ignore.
# ---------------------------------------------------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties):
    # Tell the broker which messages we want. 
    # "+" is a wildcard that matches any single word -> catches every Shelly device.
    # function runs on every reconnect so our subscription never gets dropped.
    client.subscribe("+/events/rpc")


# ---------------------------------------------------------------------------------------------
# CALLBACK 2: runs automatically every time a message arrives on a topic we subscribed to.
#
#   client   - the MQTT client object
#   userdata (unused) - reaches state without global variable
#   msg      - the message itself. The two parts we care about:
#                msg.topic   -> which topic it came from, e.g. "shellyhtg3-a1b2c3/events/rpc"
#                msg.payload -> the message content, as raw bytes of JSON text
#
# paho requires all 3 parameters to be listed, even the ones we ignore.
# ---------------------------------------------------------------------------------------------
def on_message(client, userdata, msg):
    try:
        # Convert the raw JSON bytes into a Python dictionary we can read with data["key"].
        data = json.loads(msg.payload)
        
        # Shelly sends several kinds of messages. "method" says which kind this one is.
        # "NotifyFullStatus" is the complete report the sensor sends each time it wakes up,
        # return here means that the method is not NotifyFullStatus so we will ignore those messages
        if data.get("method") != "NotifyFullStatus":
            return        
        
        # Build reading into a data shape in normalize() function
        # reading variable below will eventually be sent to api
        reading = normalize(data)
        post_reading(reading)
        print(reading)

    # Exception catches any error and then prints out error message
    except Exception as e:
        print("skipped:", e)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Create the MQTT client.
    # It must be unique: if two clients use the same ID, the broker kicks older one off.
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenhouse-gateway")

    # Tell the client which of our functions to call for each event
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to the broker.
    client.connect(MQTT_HOST, MQTT_PORT)

    # Run forever: wait for messages, call on_message for each one, and reconnect automatically
    # if the connection drops the script stays on this line until you press Ctrl+C.
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        #exit gracefully
        client.disconnect()
import os

# broker connection settings / read from env variables 
# for remote development over the SSH tunnel use this command: MQTT_PORT=1884 python subscriber.py 
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")

SENSOR_IDS = {
    "shellyhtg3-e4b3233085e8": "6ac430e14eb645800db1771f",
}
import os

# broker connection settings / read from env variables 
# for remote development over the SSH tunnel use this command: MQTT_PORT=1884 python subscriber.py 
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

import requests 

# Testing the Endpoints of the API

# ---- Request for Zones -----

BASE_URL1 = "https://greenhouse.kentcs.org/api/v1/zones"    # Endpoint for fetching zone information
response_zones = requests.get(BASE_URL1)                    # Make a GET request to fetch zone info
response_zones.raise_for_status()                           # Raises an error if the request was unsuccessful
zones_data = response_zones.json()                          # Converts the JSON into Python Data
print(zones_data)                                           # Prints the fetched data to the console

# ----- Request for Available Sensors --------

BASE_URL2 = "https://greenhouse.kentcs.org/api/v1/sensors"    
response_sensor = requests.get(BASE_URL2)
response_sensor.raise_for_status()
sensor_available = response_sensor.json()

print(sensor_available)

# ----- Request for Available Sensors DATA --------

BASE_URL3 = "https://greenhouse.kentcs.org/api/v1/sensor_data/6ac430e14eb645800db1771f"
response_sensor_data = requests.get(BASE_URL3)
response_sensor_data.raise_for_status()
sensor_data = response_sensor_data.json()

print(sensor_data)

# Make sure you are in your virtual environment for backend before running this script...
# You should see the fetched data in the Console for now... "python test_api.py"
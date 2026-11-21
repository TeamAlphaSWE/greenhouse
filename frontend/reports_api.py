"""Report takes key values for parameters to generate reports later"""
import os
import pandas as pd
import requests

#-------------NOT FINISHED-------------#
BACKEND_URL = os.environ.get("BACKEND_URL", "https://greenhouse.kentcs.org").rstrip("/")
TIMEOUT_SECONDS = 10

"""Takes date (start & end range) and zone/sensor as input for AI to generate summary with and grab data using respective filter options"""
def print_report(start = None, end = None, zone = None, sensor = None):
    data = {
        "start": start.isoformat(),
        "end": end.isoformat()
    }

    """select depending on what user selected in zone/sensor filter"""
    if zone:
        data['zone'] = zone
    if sensor:
        data['sensor'] = sensor

    response = requests.post(f"{BACKEND_URL}/report", json = data, timeout = TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
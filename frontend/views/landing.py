import streamlit as st
import pandas as pd    # for data manipulation and analysis
import numpy as np     # for numerical operations
import requests        # for making HTTP requests to the Flask local server



# Pandas and Numpy are a packaged deal since Pandas relies on Numpy for numerical operations!!
# let work on a dashboard!

# -------------------- Multi Selection for Different Zones -------------------



# This is a home page.Will have one line graph with temp and humidity in the middle 
# Buttons that will change the graph based on what zone the user wants to see.



st.title("Greenhouse Dashboard")
st.write("-----------------------------------------------")

#-------------------- Handling Real-Time Update Functionality --------------------

BACKEND_URL = "https://greenhouse.kentcs.org"


@st.fragment(run_every = "10s")     #refresh the dashboard every 10 seconds
def update_dashboard():

    sensors_response = requests.get(f"{BACKEND_URL}/api/v1/sensors")
    sensors_response.raise_for_status()
    sensors = sensors_response.json().get("sensors", [])

    if not sensors:
        st.write("No sensors available.")
        return

    sensor_options = {s["id"]: s.get("name") or s["hardware_id"] for s in sensors}

    selected_id = st.segmented_control(
        "Select a sensor",
        options = list(sensor_options.keys()),
        format_func = lambda sensor_id: sensor_options[sensor_id],
        selection_mode = "single",
        default = next(iter(sensor_options)),
    )

    if selected_id is None:
        st.write("Select a sensor to view its data.")
        return

    response_sensor_data = requests.get(f"{BACKEND_URL}/api/v1/sensor_data/{selected_id}")
    response_sensor_data.raise_for_status()
    sensor_data = response_sensor_data.json()
    record = sensor_data.get("sensor_data", [])      # Getting the all the records of sensor data from the response
    chart_rows = []                                  # To store the previous data points for the chart

    # Storing the data into a dict for easier access and manipulation
    for records in record:
        dictionary = {}
        timestamp = records.get("timestamp")  # getting the timestamp inside the for loop

        for id in records.get("values", []):
            dictionary[id["type"]] = id["value"] # for the id var in dictionary, store the value based on the word type defined in the sensor_data response

        temperature_data = dictionary.get("temperature")  # Getting the values of the response for temperature
        humidity_data = dictionary.get("humidity")        # Gettting the value for the response for humidity

        # Making a row for the chart data to visualize and connect points after updating

        chart_rows.append({
            "Temperature": temperature_data,
            "Humidity": humidity_data,
            "Date": timestamp
        })

    chart_data = pd.DataFrame(chart_rows) #converting rows in Dataframe to manipulate

    if chart_data.empty:
        st.write("No sensor data available.")
        return

    chart_data["Date"] = pd.to_datetime(chart_data["Date"])# turning the JSON timestamp into a datetime object
    chart_data = chart_data.sort_values(by="Date")         # Sorting the chart data by Time for proper visualization

#-------------- Line chart Displaying Temperature & Humidity for the selected sensor -------------------

    st.subheader("Temperature & Humidity Over Time")
    st.line_chart(chart_data, x="Date", y=["Temperature", "Humidity"])


update_dashboard()

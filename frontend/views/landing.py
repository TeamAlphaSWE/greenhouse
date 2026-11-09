import streamlit as st
import pandas as pd    # for data manipulation and analysis
import numpy as np     # for numerical operations
import requests





   



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
    sensors = sensors_response.json().get("sensors", []) #Grabbing sensors names

    if not sensors:
        st.write("No sensors available.")
        return

    pending_count = sum(1 for s in sensors if s.get("status") == "pending")
    if pending_count:
        noun = "sensor is" if pending_count == 1 else "sensors are"
        st.markdown("""
        <style>
        .st-key-activation_banner {
            background-color: #fff3cd;
            border: 1px solid #ffe69c;
            border-radius: 8px;
            padding: 12px 16px;
        }
        .st-key-activation_banner p {
            color: #664d03;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container(key="activation_banner"):
            message_col, action_col = st.columns(
                [4, 1], vertical_alignment="center"
            )

            with message_col:
                st.write(f"⚠️ {pending_count} {noun} pending activation.")

            with action_col:
                with st.container(horizontal=True, horizontal_alignment="right"):
                    st.page_link("views/sensors.py", label="Review")

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

    chart_data["Date"] = pd.to_datetime(chart_data["Date"], format = "mixed", utc=True)# turning the JSON timestamp into a datetime object
    chart_data = chart_data.sort_values(by="Date")         # Sorting the chart data by Time for proper visualization

#-------------- Line chart Displaying Temperature & Humidity for the selectexd sensor -------------------

    st.subheader("Temperature & Humidity Over Time")
    st.line_chart(chart_data, x="Date", y=["Temperature", "Humidity"])


 # Customization for sensor display cards and expandable sections
    st.subheader("Sensor Display")

 #Getting hardware ids / sensor identifiers from the backend
    response = requests.get(f"{BACKEND_URL}/api/v1/sensors")
    response.raise_for_status()
    sensors = response.json().get("sensors", [])
    sensor_id = [sensor["id"] for sensor in sensors]

    
# Overwriting the sensor IDs with custom names for display purposes!!!
    

#Getting the list of assigned zones...
    response = requests.get(f"{BACKEND_URL}/api/v1/zones")
    response.raise_for_status()
    zones = response.json().get("zones", [])

    area_names = {
        area["id"]: area["name"]
        for zone in zones
        for area in zone.get("areas", [])
    }
    zone_names = {
        zone["id"]: zone["name"]
        for zone in zones
    }

#Getting the latest temperature, humidity, and battery data for each sensor

# Creating four empty dictionaries  using the sensor ID as a key
    temp_id = {}
    humidity_id = {}
    battery_id = {}
    timestamp = {}
    

    # Loops through every sensor ID
    for sensor_name in sensor_id:
        sensor_response = requests.get(f"{BACKEND_URL}/api/v1/sensor_data/{sensor_name}")
        sensor_response.raise_for_status()
        sensor_data = sensor_response.json().get("sensor_data", [])
        latest = sensor_data[-1] if sensor_data else {}
        values = latest.get("values", [])

        latest_timestamp = latest.get("timestamp")
        #Converting timestamp into something more readable
        timestamp[sensor_name] = (
            pd.to_datetime(latest_timestamp).strftime("%Y-%m-%d %I:%M %p")
            if latest_timestamp
            else "N/A"
        )

        for value in values:
            value_type = value.get("type")
            value_data = value.get("value")

            if value_type == "temperature":
                temp_id[sensor_name] = value_data
            elif value_type == "humidity":
                humidity_id[sensor_name] = value_data
            elif value_type == "battery":
                battery_id[sensor_name] = value_data

        
# Dynmaically adding expanders for each sensors added!
# Displaying zone details for the first three sensors
    for index, sensor_name in enumerate(sensor_id): # This class functions like an iterator...starting num is 0 and increases index!
        sensor = next(sensor for sensor in sensors if sensor["id"] == sensor_name)
        area_name = area_names.get(sensor.get("area_id"), "Unassigned")

        with st.expander(f"Sensor {index + 1}"): # makes new expanders!
            st.write(f"Sensor Name: {sensor_name} ")
            st.write(f"Zone: {zone_names.get(sensor.get('zone_id'), 'Unassigned')}")
            st.write(f"Area: {area_names.get(sensor.get('area_id'), 'Unassigned')}")
            st.write(f"Latest Temperature: {temp_id.get(sensor_name, 'N/A')}")
            st.write(f"Latest Humidity: {humidity_id.get(sensor_name, 'N/A')}")
            st.write(f"Battery Percentage: {battery_id.get(sensor_name, 'N/A')}")
            st.write(f"Last Reported Timestamp: {timestamp.get(sensor_name, 'N/A')}")

    

#-------------- Line chart Displaying Historical Data for specific sensor -------------------

    st.subheader("Historical Sensor Data")
    oldest_date = chart_data["Date"].min().date() # min is the oldest date data was collected
    recent_date = chart_data["Date"].max().date() # max is the most recent date data was collected
    timerange_id = st.date_input(
        "Enter time range to filter data",
        value = (oldest_date, recent_date),
        min_value = oldest_date,
        max_value = recent_date
        )

    if len(timerange_id) == 2:
        start_date, end_date = timerange_id
        range_filter = chart_data[
            (chart_data["Date"].dt.date >= start_date) &
            (chart_data["Date"].dt.date <= end_date)
        ]

        if range_filter.empty:
            st.write("No sensor data available for this range.")
        else:
            st.line_chart(range_filter, x="Date", y=["Temperature", "Humidity"]) # this can collect the week's data and graph it

update_dashboard()

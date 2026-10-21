import streamlit as st
import pandas as pd    # for data manipulation and analysis
import numpy as np     # for numerical operations
import requests        # for making HTTP requests to the Flask local server



# Pandas and Numpy are a packaged deal since Pandas relies on Numpy for numerical operations!!
# let work on a dashboard!

# -------------------- Multi Selection for Different Zones -------------------



# This is a home page.Will have one line graph with temp and humidity in the middle 
# Buttons that will change the graph based on what zone the user wants to see.

st.page_link("views/dashboard.py", label="Go to Dashboard")
st.page_link("views/alert.py", label="Go to Alerts")
st.page_link("views/settings.py", label="Go to Settings")


st.title("Greenhouse Dashboard")
st.write("-----------------------------------------------")

#-------------------- Handling Real-Time Update Functionality --------------------

@st.fragment(run_every = "10s")     #refresh the dashboard every 10 seconds
def update_dashboard():

# INFO we are only pulling from the first sensor.... I need to undo the hardcoding for this laterrrrrr....next PR
    BASE_URL3 = "https://greenhouse.kentcs.org/api/v1/sensor_data/6ac430e14eb645800db1771f"
    response_sensor_data = requests.get(BASE_URL3)
    response_sensor_data.raise_for_status()
    sensor_data = response_sensor_data.json()
    record = sensor_data.get("sensor_data", [])      # Getting the all the records of sensor data from the response    # getting the time stamp outside of value array base don JSON 
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

    chart_data["Date"] = pd.to_datetime(chart_data["Date"])# turning the JSON timestamp into a datetime object
    chart_data = chart_data.sort_values(by="Date")         # Sorting the chart data by Time for proper visualization

    
        

#-------------- Line chart Displaying Temperature & Humidity for different Zones -------------------

    option_map = {
        0: "Zone 1",
        1: "Zone 2",
        2: "Zone 3",
        3: "Zone 4",
    }

    selection = st.segmented_control(
        "Select a zone",
        options = option_map.keys(),
        format_func = lambda option: option_map[option],
        selection_mode="single",
    )
    st.write(
        
        f"{None if selection is None else option_map[selection]}"
    )

    st.subheader("Temperature & Humidity Over Time")

    if selection is not None and option_map[selection] == "Zone 1" or selection is None:
        st.line_chart(chart_data, x="Date", y=["Temperature", "Humidity"])
    else:
        if selection is None and option_map[0] != "Zone 1" or selection is not None and option_map[selection] != "Zone 1":
            st.write("No data available for the selected zone")

        
        
update_dashboard()

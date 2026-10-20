#################
# NOT DONE YET. #
#################

import streamlit as st
import pandas as pd    # for data manipulation and analysis
import numpy as np     # for numerical operations
import requests        # for making HTTP requests to the Flask local server

# Pandas and Numpy are a packaged deal since Pandas relies on Numpy for numerical operations!!
# let work on a dashboard!

# -------------------- Multi Selection for Different Zones -------------------

# Mapping of option keys to zone names

option_map = { 
    0: "One",
    1: "Two",
    2: "Three",
    3: "Four",
}

# Segmented control for zone selection

selection = st.segmented_control(
    "Zones",
    options = option_map.keys(),        
    format_func = lambda option: option_map[option], # Function to display the zone names instead of keys
    selection_mode = "single",
)
st.write(
    "Your selected zone: "
    f"{None if selection is None else option_map[selection]}"
)

#-------------- Line chart Displaying Temperature & Humidity -------------------

# This is just an example of how I want to display the data for different zones

data = pd.DataFrame({
    'x': np.arange(0, 10, 1),
    'y': np.random.randn(10)
})


if selection is not None and option_map[selection] == "One":
    st.line_chart(data)
else:
    st.write("No data available for display")

#-------------------- Handling HTTP Requests to the API --------------------



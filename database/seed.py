#########################
# Still working on this #
#########################

from pymongo import MongoClient # to be able to connect to MongoDB and our database
from datetime import datetime # used for timestamps and created/updated at times

client = MongoClient("mongodb://localhost:27017")
db = client["year2_greenhouse_db"]

sensor_data_collection = db["sensor_data"]
sensors_collection = db["sensors"]
zones_collection = db["zones"]
users_collection = db["users"]

# very important since database must be cleared of redundant data per run
# sensor_data_collection.delete_many({})
# sensors_collection.delete_many({})
# zones_collection.delete_many({})
# users_collection.delete_many({})

sensor_data_collection = {
    "values":{
        "0":{
            "type": "temperature",
            "value": "24.5"
        },
        "1":{
            "type": "humidity",
            "value": 56
        },
        "2":{
            "type": "battery",
            "value": 90
        }
    },

    "timestamp": datetime.now()
}

sensors_collection = {
    "name": "Sensor Three",
    "brand": "Shelly",
    "model": "H&T",
    "type":{
        "0": "humidity",
        "1": "temperature"
    },

    "created_at": datetime.now(),
    "updated at": datetime.now()
}

zones_collection = {
    "name": "Zone 2",
    "description": "yellow and red tulips",
    "status": "active",
    "areas":{
        "name": "Area 2 - Flowers",
        "status": "active",
        "target_conditions":{
            "temperature":{
                "min": 21,
                "max": 27
            },
            "humidity":{
                "min": 62,
                "max": 77
            }
        }
    },

    "created_at": datetime.now(),
    "updated at": datetime.now()
}

users_collection = {
    "username": "beta",
    "password_hash": "test2",
    "admin": False,
    "created_at": datetime.now(),
    "updated at": datetime.now()
}

db.sensor_data.insert_one("sensor_data_collection")
db.sensors.insert_one("sensors_collection")
db.zones.insert_one("zones.collection")
db.users.insert_one("users_collection")
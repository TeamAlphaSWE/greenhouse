###################################################
# Seed script to populate database with mock data #
###################################################

from pymongo import MongoClient # to be able to connect to MongoDB and our database
from datetime import datetime # used for timestamps and created/updated at times
from bson import ObjectId # get data from database
import os
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "year2_greenhouse_db")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
zone_id = ObjectId()
area_id = ObjectId()
sensor_id = ObjectId()
map_id = ObjectId()
region_id = ObjectId()

sensor_data_collection = db["sensor_data"]
sensors_collection = db["sensors"]
zones_collection = db["zones"]
users_collection = db["users"]
maps_collection = db["maps"]

# very important since database must be cleared of redundant data per run
sensor_data_collection.delete_many({})
sensors_collection.delete_many({})
zones_collection.delete_many({})
users_collection.delete_many({})
maps_collection.delete_many({})

sensor_data_collection = {
    "sensor_id": sensor_id,
    "values":[
        {
            "type": "temperature",
            "value": "24.5"
        },
        {
            "type": "humidity",
            "value": 56
        },
        {
            "type": "battery",
            "value": 90
        }
    ],

    "timestamp": datetime.now(),
}

sensors_collection = {
    "name": "Sensor Three",
    "zone_id": zone_id,
    "area_id": area_id,
    "brand": "Shelly",
    "model": "H&T",
    "type":{
        "0": "humidity",
        "1": "temperature"
    },

    "created_at": datetime.now(),
    "updated at": datetime.now(),
}

zones_collection = {
    "_id": zone_id,
    "name": "Zone 2",
    "description": "yellow and red tulips",
    "status": "active",
    "map_id": map_id,
    "areas":[{
        "id": area_id,
        "name": "Area 2 - Flowers",
        "status": "active",
        "region_id": region_id,
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
    }],

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

maps_collection = {
    "_id": map_id,
    "name": "Greenhouse Floor 1",
    "image_path": "/maps/greenhouse-floor-1.png",
    "regions": [
        {
            "id": region_id,
            "x": 0.1,
            "y": 0.15,
            "w": 0.2,
            "h": 0.25
        },
        {
            "x": 0.5,
            "y": 0.02,
            "w": 0.3,
            "h": 0.05,
            "text": "Office"
        }
    ],
    "created_at": datetime.now(),
    "updated_at": datetime.now()
}

db.sensor_data.insert_one(sensor_data_collection)
db.sensors.insert_one(sensors_collection)
db.zones.insert_one(zones_collection)
db.users.insert_one(users_collection)
db.maps.insert_one(maps_collection)
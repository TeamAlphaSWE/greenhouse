from pymongo import MongoClient
from datetime import datetime

connection_string=("mongodb+srv://rcoulson_db_user:7q6kDfRuldzW2COa@greenhouse-clouster.n6uuf84.mongodb.net/year2_greenhouse_db?retryWrites=true&w=majority&appName=greenhouse-clouster")
client = MongoClient(
    connection_string,
    serverSelectionTimeoutMS=10000
)


try:
    client.admin.command("ping")
    print("MongoDB connection successful!")

    db = client["year2_greenhouse_db"]

    collections = db.list_collection_names()

    print("Existing collections:")

    for collection in collections:
        print(collection)

except Exception as e:
    print("MongoDB connection failed:")
    print(e)



required_collections = [
    "sensor_data",
    "sensors",
    "zones",
    "users"
]

existing_collections = db.list_collection_names()

for collection in required_collections:
    if collection not in existing_collections:
        db.create_collection(collection)
        print(f"Created collection: {collection}")
    else:
        print(f"Collection already exists: {collection}")

for collection in db.list_collection_names():
    print(f"collection name: {collection}")
    print(db[collection].find_one())


zone = {
    "name": "Zone Test",
    "description": "test",
    "status": "active",
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    "areas": [
       {
            "name": "Area Test",
            "status": "active",
            "target_conditions": {
                "temperature": {
                    "min": 60,
                    "max": 120
                },
                "humidity": {
                    "min": 50,
                    "max": 70
                }
            }
        }
    ]
}  


existing_zone = db["zones"].find_one({"name": "Zone Test"})
if existing_zone:
    print("zone collection populated with test zone all ready")
else:
    result = db["zones"].insert_one(zone)
    print(result.inserted_id)
    print ("zone created")

existing_zone = db["zones"].find_one({"name": "Zone Test"})
zone_id=existing_zone["_id"]
area_id=existing_zone["areas"][0]

sensor = {
    "name": "Sensor Test",
    "brand": "Shelly",
    "model": "H&T",
    "zone_id": zone_id,
    "area_id": area_id,
    "hardware":"test",
    "type": ["humidity", "temperature"],
    "created_at": datetime.now(),
    "updated_at": datetime.now()
}

existing_sensors = db["sensors"].find_one({"name": "Sensor Test"})
if existing_sensors:
    print("sensors collection populated with test sensor all ready")
else:
    result = db["sensors"].insert_one(sensor)
    print(result.inserted_id)
    print ("sensor created")

sensor_id = existing_sensors["_id"]

sensor_data = {
    "timestamp": datetime.now(),
    "sensor_id": sensor_id,
    "values": [
        {
            "type": "temperature",
            "value": 23.4
        },
        {
            "type": "humidity",
            "value": 50
        },
        {
            "type": "battery",
            "value": 82
        }
    ]
}

existing_data = db["sensor_data"].find_one({"sensor_id": sensor_id})

if existing_data:
    print("Sensor data already exists")
else:
    result = db["sensor_data"].insert_one(sensor_data)
    print("Sensor data created")

user = {
    "username": "user Test",
    "password_hash": "test",
    "admin":True,
    "created_at": datetime.now(),
    "updated_at": datetime.now()
}

existing_user = db["users"].find_one({"username":"user Test"})

if existing_user:
    print("user already exists")
else:
    result = db["users"].insert_one(user)
    print("user created")

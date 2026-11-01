from pymongo import MongoClient # to be able to connect to MongoDB and our database
from datetime import datetime # used for timestamps and created/updated at times
from bson import ObjectId # get data from database
import os
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "year2_greenhouse_db")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]


try:
    # Test the MongoDB connection
    client.admin.command("ping")
    print("MongoDB connection successful!")

    # Schema validator for sensors
    SENSORS_VALIDATOR = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "_id",
                "hardware_id",
                "status",
                "created_at",
                "updated_at"
            ],
            "properties": {
                "hardware_id": {
                    "bsonType": "string"
                },
                "status": {
                    "enum": ["pending", "active"]
                },
                "zone_id": {
                    "bsonType": "objectId"
                },
                "area_id": {
                    "bsonType": "objectId"
                },
                "type": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "string"
                    }
                }
            }
        }
    }

    # Schema validator for zones
    ZONES_VALIDATOR = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "name",
                "description",
                "status",
                "created_at",
                "updated_at",
                "areas"
            ],
            "properties": {
                "name": {
                    "bsonType": "string"
                },
                "description": {
                    "bsonType": "string"
                },
                "status": {
                    "enum": ["active", "inactive"]
                },
                "created_at": {
                    "bsonType": "date"
                },
                "updated_at": {
                    "bsonType": "date"
                },
                "areas": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": [
                            "name",
                            "status",
                            "target_conditions"
                        ],
                        "properties": {
                            "name": {
                                "bsonType": "string"
                            },
                            "status": {
                                "enum": ["active", "inactive"]
                            },
                            "target_conditions": {
                                "bsonType": "object"
                            }
                        }
                    }
                }
            }
        }
    }

    # Schema validator for sensor_data
    SENSOR_DATA_VALIDATOR = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "timestamp",
                "sensor_id",
                "values"
            ],
            "properties": {
                "timestamp": {
                    "bsonType": "date"
                },
                "sensor_id": {
                    "bsonType": "objectId"
                },
                "values": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": [
                            "type",
                            "value"
                        ],
                        "properties": {
                            "type": {
                                "bsonType": "string"
                            },
                            "value": {
                                "bsonType": [
                                    "double",
                                    "int",
                                    "long",
                                    "decimal"
                                ]
                            }
                        }
                    }
                }
            }
        }
    }

    # Schema validator for users
    USERS_VALIDATOR = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "username",
                "password_hash",
                "admin",
                "created_at",
                "updated_at"
            ],
            "properties": {
                "username": {
                    "bsonType": "string"
                },
                "password_hash": {
                    "bsonType": "string"
                },
                "admin": {
                    "bsonType": "bool"
                },
                "created_at": {
                    "bsonType": "date"
                },
                "updated_at": {
                    "bsonType": "date"
                }
            }
        }
    }

    # Store all collection names and their validators together.
    COLLECTIONS = {
        "sensors": SENSORS_VALIDATOR,
        "zones": ZONES_VALIDATOR,
        "sensor_data": SENSOR_DATA_VALIDATOR,
        "users": USERS_VALIDATOR
    }

    # Create collections with schema validation.
    # Existing collections are skipped.
    for name, validator in COLLECTIONS.items():

        if name in db.list_collection_names():
            print(f"{name} already exists, skipping")
            continue

        db.create_collection(
            name,
            validator=validator
        )

        print(f"Created {name} with schema validation")

    # Display the collections that currently exist.
    print("\nExisting collections:")

    for collection in db.list_collection_names():
        print(collection)

    # Display one existing document from each collection.
    # This only reads data. It does NOT create test data.
    print("\nChecking existing documents:")

    for collection in COLLECTIONS:
        print(f"\nCollection: {collection}")
        print(db[collection].find_one())

    print("\nDatabase initialization complete!")

except Exception as e:
    print("MongoDB connection or initialization failed:")
    print(e)

finally:
    client.close()

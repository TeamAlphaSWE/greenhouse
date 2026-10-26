import os


class Config:
    """Default configuration, read from environment variables.

    Values can be overridden per app instance by passing a mapping to
    `create_app()` (useful in tests).
    """

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "year2_greenhouse_db")
    MONGO_SERVER_SELECTION_TIMEOUT_MS = int(
        os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")
    )
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    
    # Sensor health: a sensor is stale when its last reading is older than
    # STALE_FACTOR * its expected reporting interval.
    SENSOR_REPORT_INTERVAL_MINUTES = int(os.environ.get("SENSOR_REPORT_INTERVAL_MINUTES", "120"))
    SENSOR_STALE_FACTOR = float(os.environ.get("SENSOR_STALE_FACTOR", "2"))
    LOW_BATTERY_PERCENT = int(os.environ.get("LOW_BATTERY_PERCENT", "20"))

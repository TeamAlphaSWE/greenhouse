import os


class Config:
    """Default configuration, read from environment variables.

    Values can be overridden per app instance by passing a mapping to
    `create_app()` (useful in tests).
    """

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "greenhouse")
    MONGO_SERVER_SELECTION_TIMEOUT_MS = int(
        os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")
    )

from flask import Flask

from app.config import Config
from app.db import init_db
from app.json import MongoJSONProvider


def create_app(config=None):
    app = Flask(__name__)
    app.json = MongoJSONProvider(app)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)

    init_db(app)

    from app.routes.health import health
    app.register_blueprint(health)

    from app.routes.zones import zones
    app.register_blueprint(zones)

    from app.routes.sensors import sensors
    app.register_blueprint(sensors)

    from app.routes.sensor_data import sensor_data
    app.register_blueprint(sensor_data)

    return app

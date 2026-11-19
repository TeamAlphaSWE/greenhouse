from flask import Flask

from app.config import Config
from app.db import init_db
from app.json import MongoJSONProvider
from app.services.email_service import EmailService


def create_app(config=None):
    app = Flask(__name__)
    app.json = MongoJSONProvider(app)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)

    email_settings = [
        app.config.get("SMTP_HOST"),
        app.config.get("SMTP_USER"),
        app.config.get("SMTP_PASSWORD"),
    ]
    if all(email_settings):
        app.extensions["email_service"] = EmailService(app.config)
    else:
        app.extensions["email_service"] = None

    init_db(app)

    from app.routes.health import health
    app.register_blueprint(health)

    from app.routes.auth import auth
    app.register_blueprint(auth)

    from app.routes.zones import zones
    app.register_blueprint(zones)

    from app.routes.areas import areas
    app.register_blueprint(areas)

    from app.routes.sensors import sensors
    app.register_blueprint(sensors)

    from app.routes.sensor_data import sensor_data
    app.register_blueprint(sensor_data)
    
    from app.routes.alerts import alerts
    app.register_blueprint(alerts)

    from app.routes.maps import maps
    app.register_blueprint(maps)

    from app.routes.settings import settings
    app.register_blueprint(settings)

    return app

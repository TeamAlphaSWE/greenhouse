from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from app.config import Config
from app.db import init_db
from app.json import MongoJSONProvider

from app.services.ai_service import AIService


def create_app(config=None):
    app = Flask(__name__)
    app.json = MongoJSONProvider(app)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)

    ai_settings = [
        app.config.get("AI_BASE_URL"),
        app.config.get("AI_API_KEY"),
        app.config.get("AI_MODEL"),
    ]

    if all(ai_settings):
        app.extensions["ai_service"] = AIService(app.config)
    else:
        app.extensions["ai_service"] = None

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

    from app.routes.ai import ai
    app.register_blueprint(ai)

    return app

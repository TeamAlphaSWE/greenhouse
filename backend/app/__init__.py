from flask import Flask

from app.config import Config
from app.db import init_db


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)

    init_db(app)

    from app.routes.health import health
    app.register_blueprint(health)

    return app

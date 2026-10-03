from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes.health import health
    app.register_blueprint(health)

    return app
from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash

from app.auth import issue_token
from app.repositories.users import users as user_repository

auth = Blueprint("auth", __name__, url_prefix="/api/v1")


@auth.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "username and password are required"}), 400

    try:
        user = user_repository.find_by_username(username)
    except PyMongoError:
        current_app.logger.exception("Failed to load user")
        return jsonify({"error": "Unexpected server error"}), 500

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    return jsonify({"token": issue_token(current_app, user["id"])})

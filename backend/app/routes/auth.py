from flask import Blueprint, current_app, g, jsonify, request
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth import issue_token, require_auth
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


@auth.post("/change-password")
@require_auth
def change_password():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    old_password = data.get("old_password")
    new_password = data.get("new_password")
    if not isinstance(old_password, str) or not isinstance(new_password, str) or not new_password:
        return jsonify({"error": "old_password and new_password are required"}), 400

    if not check_password_hash(g.user["password_hash"], old_password):
        return jsonify({"error": "old_password is incorrect"}), 400

    # Pinned: werkzeug's default (scrypt) isn't available in every Python build's hashlib.
    new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")

    try:
        user_repository.set_password_hash(g.user["id"], new_hash)
    except PyMongoError:
        current_app.logger.exception("Failed to change password")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"message": "Password changed"})


@auth.post("/admin/reset-password")
@require_auth
def admin_reset_password():
    if g.user.get("admin") is not True:
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username")
    new_password = data.get("new_password")
    if not isinstance(username, str) or not username or not isinstance(new_password, str) or not new_password:
        return jsonify({"error": "username and new_password are required"}), 400

    # Pinned: werkzeug's default (scrypt) isn't available in every Python build's hashlib.
    new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")

    try:
        user = user_repository.find_by_username(username)
        if user is None:
            return jsonify({"error": "User not found"}), 404
        user_repository.set_password_hash(user["id"], new_hash)
    except PyMongoError:
        current_app.logger.exception("Failed to reset password")
        return jsonify({"error": "Unexpected server error"}), 500

    return jsonify({"message": "Password reset"})

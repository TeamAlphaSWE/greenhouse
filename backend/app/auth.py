"""Token issuance and the `require_auth` decorator.

Tokens are signed, not encrypted, and carry no expiry: they're valid until
the server's SECRET_KEY changes. A valid token also loads the user it
belongs to and stashes it on `flask.g.user` for the view to use.
"""
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, URLSafeSerializer

from app.repositories.users import users as user_repository

_SALT = "auth-token"


def _serializer(app):
    return URLSafeSerializer(app.config["SECRET_KEY"], salt=_SALT)


def issue_token(app, user_id: str) -> str:
    return _serializer(app).dumps({"user_id": user_id})


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = header[len("Bearer "):]
        try:
            payload = _serializer(current_app).loads(token)
        except BadSignature:
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        user = user_repository.get(payload.get("user_id", ""))
        if user is None:
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        g.user = user
        return view(*args, **kwargs)

    return wrapped

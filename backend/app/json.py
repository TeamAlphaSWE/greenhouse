from bson import ObjectId
from datetime import datetime
from flask.json.provider import DefaultJSONProvider


class MongoJSONProvider(DefaultJSONProvider):
    """JSON provider that also serializes BSON types, so `jsonify` accepts
    MongoDB documents (e.g. ObjectId references) without manual conversion."""

    @staticmethod
    def default(o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return DefaultJSONProvider.default(o)
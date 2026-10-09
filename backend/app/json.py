from bson import ObjectId
from flask.json.provider import DefaultJSONProvider


class MongoJSONProvider(DefaultJSONProvider):
    """JSON provider that also serializes BSON types, so `jsonify` accepts
    MongoDB documents (e.g. ObjectId references) without manual conversion."""

    @staticmethod
    def default(o):
        if isinstance(o, ObjectId):
            return str(o)
        return DefaultJSONProvider.default(o)

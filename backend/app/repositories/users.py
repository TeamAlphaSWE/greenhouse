from datetime import datetime, timezone

from app.repository import Repository


class UserRepository(Repository):
    collection_name = "users"

    def find_by_username(self, username):
        return self.find_one({"username": username})

    def set_password_hash(self, user_id, password_hash):
        return self.update(user_id, {
            "password_hash": password_hash,
            "updated_at": datetime.now(timezone.utc),
        })

    def all_alerts_disabled(self):
        if self.find_one({"settings.alerts_enabled": False}) is None:
            return False
        return self.find_one({"settings.alerts_enabled": {"$ne": False}}) is None


users = UserRepository()
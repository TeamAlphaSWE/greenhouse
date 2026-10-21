from app.repository import Repository


class UserRepository(Repository):
    collection_name = "users"

    def find_by_username(self, username):
        return self.find_one({"username": username})


users = UserRepository()

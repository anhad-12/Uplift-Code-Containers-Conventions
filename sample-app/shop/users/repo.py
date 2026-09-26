from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


_USERS = {
    1: User(1, "Asha Rao", "asha@example.com"),
    2: User(2, "Ben Ito", "ben@example.com"),
}


def find_user(user_id: int):
    return _USERS.get(user_id)


def all_users():
    return list(_USERS.values())

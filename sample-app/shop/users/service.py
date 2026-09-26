from shop.errors import NotFoundError
from shop.users import repo


def get_user(user_id: int) -> repo.User:
    user = repo.find_user(user_id)
    if user is None:
        raise NotFoundError("user", user_id)
    return user


def list_users() -> list:
    return repo.all_users()

from shop.users import repo


def get_user(user_id: int) -> repo.User:
    return repo.find_user(user_id)


def list_users() -> list:
    return repo.all_users()

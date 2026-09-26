from shop.users import repo


def test_find_user_returns_user():
    user = repo.find_user(1)
    assert user is not None
    assert user.name == "Asha Rao"


def test_find_user_unknown_returns_none():
    assert repo.find_user(0) is None


def test_all_users_returns_two():
    assert len(repo.all_users()) == 2

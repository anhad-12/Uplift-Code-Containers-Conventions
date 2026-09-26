from shop.users.service import get_user, list_users


def test_get_user_returns_user():
    assert get_user(1).name == "Asha Rao"


def test_get_user_missing_returns_none():
    assert get_user(999) is None


def test_list_users():
    assert len(list_users()) == 2

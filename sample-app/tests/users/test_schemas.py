from shop.users.repo import User
from shop.users.schemas import UserOut


def test_user_out_from_orm():
    user = User(id=1, name="Asha Rao", email="asha@example.com")
    out = UserOut.from_orm(user)
    assert out.id == 1
    assert out.email == "asha@example.com"

from tests.conftest import make_client
from shop.users.routes import router

client = make_client(router)


def test_get_user_route_ok():
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["email"] == "asha@example.com"


def test_list_users_route():
    assert len(client.get("/users").json()) == 2


def test_list_users_route_returns_both():
    users = client.get("/users").json()
    names = {u["name"] for u in users}
    assert names == {"Asha Rao", "Ben Ito"}


def test_get_known_user_returns_id_and_name():
    data = client.get("/users/2").json()
    assert data["id"] == 2
    assert data["name"] == "Ben Ito"

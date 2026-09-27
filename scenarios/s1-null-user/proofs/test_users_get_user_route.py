# uplift:item shop/users/routes.py#get_user_route
from tests.conftest import make_client
from shop.users.routes import router


def test_get_user_route_unknown_returns_404():
    """OLD contract: GET /users/999 for an unknown user returns 404."""
    client = make_client(router)
    response = client.get("/users/999")
    assert response.status_code == 404

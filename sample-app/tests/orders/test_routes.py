from tests.conftest import make_client
from shop.orders.routes import router

client = make_client(router)


def test_post_order_ok():
    response = client.post("/orders", json={"user_id": 1, "items": [5, 5]})
    assert response.status_code == 200
    assert response.json()["total"] == 10


def test_get_order_route_ok():
    post = client.post("/orders", json={"user_id": 1, "items": [3.0, 7.0]})
    order_id = post.json()["id"]
    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["total"] == 10.0


def test_get_missing_order_route_is_404():
    response = client.get("/orders/9999")
    assert response.status_code == 404

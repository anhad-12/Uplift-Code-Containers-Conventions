from tests.conftest import make_client
from shop.payments.routes import router

client = make_client(router)


def test_post_payment_ok():
    body = {"user_id": 1, "amount": 100, "card": "4242424242424242"}
    assert client.post("/payments", json=body).json()["amount"] == 103.2

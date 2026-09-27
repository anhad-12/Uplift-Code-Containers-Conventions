# uplift:item shop/payments/routes.py#post_payment
import pytest
from shop.payments.routes import router
from tests.conftest import make_client


def test_api_preserves_dollar_contract():
    response = make_client(router).post('/payments', json={"user_id": 1, "amount": 100, "card": "4242424242424242"})
    assert response.status_code == 200
    assert response.json()["amount"] == pytest.approx(103.2)

# uplift:item shop/orders/service.py#create_order
import pytest

from shop.errors import ValidationError
from shop.orders.schemas import OrderIn
from shop.orders.service import create_order


def test_create_order_rejects_unknown_user():
    """OLD contract: an order for a user that does not exist is rejected with ValidationError."""
    with pytest.raises(ValidationError):
        create_order(OrderIn(user_id=999, items=[1.0], note=None))

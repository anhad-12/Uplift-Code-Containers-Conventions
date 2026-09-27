# uplift:item shop/orders/service.py#create_order
import pytest
from shop.errors import NotFoundError, ValidationError
from shop.orders.schemas import OrderIn
from shop.orders.service import create_order


def test_create_order_rejects_unknown_user():
    """Base: create_order raises ValidationError (wrapping NotFoundError) for unknown user_id.
    Head (s1-null-user): get_user returns None — the except NotFoundError guard never fires,
    unknown users silently create orders."""
    with pytest.raises((NotFoundError, ValidationError)):
        create_order(OrderIn(user_id=99999, items=[9.99]))

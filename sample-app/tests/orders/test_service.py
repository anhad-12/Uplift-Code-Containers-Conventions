from shop.orders.schemas import OrderIn
from shop.orders.service import create_order, get_order


def make_input(user_id=1):
    return OrderIn(user_id=user_id, items=[10.0, 5.5])


def test_create_order_totals_items():
    assert create_order(make_input()).total == 15.5


def test_get_order_roundtrip():
    order = create_order(make_input())
    assert get_order(order.id).user_id == 1


import pytest

from shop.errors import NotFoundError


def test_create_order_empty_items_totals_zero():
    order = create_order(OrderIn(user_id=1, items=[]))
    assert order.total == 0


def test_get_order_missing_raises_not_found():
    with pytest.raises(NotFoundError) as exc_info:
        get_order(9999)
    assert exc_info.value.resource == "order"

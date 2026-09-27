# uplift:item shop/orders/invoice.py#build_invoice
import pytest

from shop.errors import NotFoundError
from shop.orders.invoice import build_invoice
from shop.orders.repo import Order


def test_build_invoice_unknown_user_raises():
    """OLD contract: build_invoice for an order with an unknown user_id raises NotFoundError."""
    order = Order(id=1, user_id=999, total=50.0)
    with pytest.raises(NotFoundError):
        build_invoice(order)

# uplift:item shop/payments/receipt.py#render_receipt
import pytest

from shop.errors import NotFoundError
from shop.payments.charge import Payment
from shop.payments.receipt import render_receipt


def test_render_receipt_unknown_user_raises():
    """OLD contract: render_receipt for an unknown user_id raises NotFoundError."""
    payment = Payment(user_id=999, amount=10.0)
    with pytest.raises(NotFoundError):
        render_receipt(payment)

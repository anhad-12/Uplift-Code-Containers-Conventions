# uplift:item shop/orders/invoice.py#payment_line
import pytest
from shop.payments.charge import charge
from shop.orders.invoice import payment_line


def test_invoice_preserves_dollar_contract():
    assert payment_line(charge(1, 100.0))["amount"] == pytest.approx(103.2)

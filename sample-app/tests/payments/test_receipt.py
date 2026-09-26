from shop.payments.charge import Payment
from shop.payments.receipt import render_receipt


def test_receipt_shows_dollars():
    assert render_receipt(Payment(1, 103.2)) == "Receipt for Asha Rao: $103.20"

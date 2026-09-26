from shop.payments.charge import Payment
from shop.payments.receipt import render_receipt


def test_receipt_for_user_two():
    assert render_receipt(Payment(2, 50.0)) == "Receipt for Ben Ito: $50.00"


def test_receipt_formats_zero_cents():
    assert render_receipt(Payment(1, 10.0)) == "Receipt for Asha Rao: $10.00"


def test_receipt_formats_large_amount():
    assert render_receipt(Payment(1, 1000.0)) == "Receipt for Asha Rao: $1000.00"

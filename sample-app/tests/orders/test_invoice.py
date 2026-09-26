from shop.orders.invoice import build_invoice, payment_line
from shop.orders.repo import Order
from shop.payments.charge import Payment


def test_payment_line_uses_the_payment_amount():
    assert payment_line(Payment(1, 103.2)) == {"label": "payment", "amount": 103.2}


def test_invoice_addresses_the_user():
    invoice = build_invoice(Order(1, 1, 20.0))
    assert invoice["to"] == "asha@example.com"
    assert invoice["total"] == 20.0


def test_invoice_total_equals_order_total():
    from shop.orders.repo import Order
    order = Order(id=2, user_id=1, total=42.5)
    invoice = build_invoice(order)
    assert invoice["total"] == order.total

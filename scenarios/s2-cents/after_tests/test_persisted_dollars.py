"""Regression for consumers of dollar-denominated persisted payments."""
from shop.payments import repo
from shop.payments.charge import charge
from shop.payments.receipt import render_receipt
from shop.orders.invoice import payment_line
from shop.notifications.email import send_receipt_email
from shop.admin.reports import revenue_total


def test_persisted_dollars_are_not_converted_twice():
    charged = charge(1, 100.0)
    assert charged.amount == 10320
    stored = repo.save_payment(charged)
    stored_again = repo.save_payment(stored)
    assert stored.amount == stored_again.amount == 103.2
    for payment in (charged, stored, stored_again):
        assert render_receipt(payment) == 'Receipt for Asha Rao: $103.20'
        assert payment_line(payment)['amount'] == 103.2
        assert send_receipt_email(payment) == 'Thanks! We charged $103.20'
        assert revenue_total([payment]) == 103.2

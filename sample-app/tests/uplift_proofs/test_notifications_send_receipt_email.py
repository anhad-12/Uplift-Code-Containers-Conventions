# uplift:item shop/notifications/email.py#send_receipt_email
from shop.payments.charge import charge
from shop.notifications.email import send_receipt_email


def test_send_receipt_email_formats_amount_as_dollars():
    """OLD contract: send_receipt_email formats the amount produced by charge() as dollars (e.g. $103.20)."""
    payment = charge(1, 100.0)
    result = send_receipt_email(payment)
    assert result == "Thanks! We charged $103.20"

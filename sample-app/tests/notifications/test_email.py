from shop.notifications.email import send_receipt_email, send_welcome
from shop.payments.charge import Payment


def test_send_welcome():
    assert send_welcome(1) is True


def test_receipt_email_mentions_the_amount():
    assert send_receipt_email(Payment(1, 103.2)) == "Thanks! We charged $103.20"


def test_send_welcome_user_two():
    assert send_welcome(2) is True

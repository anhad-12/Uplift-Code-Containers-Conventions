import pytest

from pydantic import ValidationError as PydanticValidationError

from shop.payments.schemas import PaymentIn


def test_payment_in_accepts_16_digit_card():
    p = PaymentIn(user_id=1, amount=10.0, card="1234567890123456")
    assert p.card == "1234567890123456"


def test_payment_in_rejects_short_card():
    with pytest.raises(PydanticValidationError):
        PaymentIn(user_id=1, amount=10.0, card="123456")

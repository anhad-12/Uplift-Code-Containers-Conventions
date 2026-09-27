# uplift:item shop/payments/repo.py#save_payment
import pytest
from shop.payments.charge import charge
from shop.payments import repo


def test_repository_preserves_dollar_contract():
    payment = charge(1, 100.0)
    saved = repo.save_payment(payment)
    assert saved.amount == pytest.approx(103.2)
    assert repo.all_payments()[0].amount == pytest.approx(103.2)

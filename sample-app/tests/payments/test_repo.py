from shop.payments import repo
from shop.payments.charge import Payment


def test_save_and_list_payments():
    repo.save_payment(Payment(1, 10.0))
    assert [p.user_id for p in repo.all_payments()] == [1]


def test_all_payments_returns_all():
    repo.save_payment(Payment(1, 10.0))
    repo.save_payment(Payment(2, 20.0))
    assert len(repo.all_payments()) == 2


def test_reset_clears_payments():
    repo.save_payment(Payment(1, 5.0))
    repo.reset()
    assert repo.all_payments() == []

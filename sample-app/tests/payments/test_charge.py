from shop.payments.charge import charge


def test_charge_adds_fee_in_dollars():
    assert charge(1, 100.0).amount == 103.2

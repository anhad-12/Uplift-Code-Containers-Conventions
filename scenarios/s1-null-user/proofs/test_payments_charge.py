# uplift:item shop/payments/charge.py#charge
import pytest

from shop.errors import NotFoundError
from shop.payments.charge import charge


def test_charge_unknown_user_raises():
    """OLD contract: charge for a non-existent user_id raises NotFoundError."""
    with pytest.raises(NotFoundError):
        charge(user_id=999, amount=20.0)

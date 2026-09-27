# uplift:item shop/payments/charge.py#charge
import pytest
from shop.errors import NotFoundError
from shop.payments.charge import charge


def test_charge_rejects_unknown_user():
    """Base: charge() calls get_user which raises NotFoundError for unknown user_id.
    Head (s1-null-user): get_user returns None — charge() proceeds and returns a
    Payment for a non-existent user with no error."""
    with pytest.raises(NotFoundError):
        charge(user_id=99999, amount=10.0)

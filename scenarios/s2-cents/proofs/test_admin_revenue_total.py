# uplift:item shop/admin/reports.py#revenue_total
import pytest

from shop.payments.charge import charge
from shop.admin.reports import revenue_total


def test_revenue_total_returns_dollar_scale():
    """OLD contract: revenue_total sums payment amounts as dollars (charge(1, 100.0) -> ~103.2, not ~10320)."""
    payment = charge(1, 100.0)
    result = revenue_total([payment])
    assert result == pytest.approx(103.2)

# uplift:item shop/admin/reports.py#user_spend_report
import pytest

from shop.errors import NotFoundError
from shop.orders import repo as order_repo
from shop.admin.reports import user_spend_report


def test_user_spend_report_unknown_user_raises():
    """OLD contract: user_spend_report raises NotFoundError when an order references an unknown user_id."""
    order_repo.save_order(user_id=999, total=42.0)
    with pytest.raises(NotFoundError):
        user_spend_report()

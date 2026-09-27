from typing import List

from shop.errors import NotFoundError
from shop.orders import repo as order_repo
from shop.payments.charge import Payment
from shop.users.service import get_user


def user_spend_report() -> list:
    rows = []
    for order in order_repo.all_orders():
        user = get_user(order.user_id)
        if user is None:
            raise NotFoundError("user", order.user_id)
        rows.append({"user": user.name, "total": order.total})
    return rows


def revenue_total(payments: List[Payment]) -> float:
    return round(sum(p.amount for p in payments) / 100, 2)

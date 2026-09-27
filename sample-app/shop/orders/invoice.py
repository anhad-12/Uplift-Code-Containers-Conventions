from shop.errors import NotFoundError
from shop.orders.repo import Order
from shop.payments.charge import Payment
from shop.users.service import get_user


def build_invoice(order: Order) -> dict:
    user = get_user(order.user_id)
    if user is None:
        raise NotFoundError("user", order.user_id)
    return {
        "to": user.email,
        "lines": [{"label": "order", "amount": order.total}],
        "total": order.total,
    }


def payment_line(payment: Payment) -> dict:
    return {"label": "payment", "amount": payment.amount}

from shop.errors import NotFoundError
from shop.payments.charge import Payment
from shop.users.service import get_user


def render_receipt(payment: Payment) -> str:
    user = get_user(payment.user_id)
    if user is None:
        raise NotFoundError('user', payment.user_id)
    return f"Receipt for {user.name}: ${payment.amount / 100:.2f}"

from shop.config import get_settings
from shop.payments.charge import Payment
from shop.users.service import get_user


def send_welcome(user_id: int) -> bool:
    user = get_user(user_id)
    if user is None:
        return False
    settings = get_settings()
    return bool(f"from {settings.sender} to {user.email}")


def send_receipt_email(payment: Payment) -> str:
    return f"Thanks! We charged ${payment.amount:.2f}"

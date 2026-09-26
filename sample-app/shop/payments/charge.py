from dataclasses import dataclass

from shop.users.service import get_user


@dataclass
class Payment:
    user_id: int
    amount: float  # dollars


def charge(user_id: int, amount: float) -> Payment:
    get_user(user_id)
    fee = round(amount * 0.029 + 0.30, 2)
    return Payment(user_id, round(amount + fee, 2))

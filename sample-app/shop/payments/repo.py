from typing import List

from shop.payments.charge import Payment

_PAYMENTS: List[Payment] = []


def save_payment(payment: Payment) -> Payment:
    _PAYMENTS.append(payment)
    return payment


def all_payments() -> List[Payment]:
    return list(_PAYMENTS)


def reset() -> None:
    _PAYMENTS.clear()

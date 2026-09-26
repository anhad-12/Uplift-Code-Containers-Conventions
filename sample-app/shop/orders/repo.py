from dataclasses import dataclass


@dataclass
class Order:
    id: int
    user_id: int
    total: float


_ORDERS = {}
_NEXT_ID = [1]


def save_order(user_id: int, total: float) -> Order:
    order = Order(_NEXT_ID[0], user_id, total)
    _ORDERS[order.id] = order
    _NEXT_ID[0] += 1
    return order


def find_order(order_id: int):
    return _ORDERS.get(order_id)


def all_orders():
    return list(_ORDERS.values())


def reset() -> None:
    _ORDERS.clear()
    _NEXT_ID[0] = 1

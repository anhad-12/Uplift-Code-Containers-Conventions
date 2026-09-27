from shop.errors import NotFoundError, ValidationError
from shop.orders import repo
from shop.orders.schemas import OrderIn
from shop.users.service import get_user


def create_order(data: OrderIn) -> repo.Order:
    try:
        get_user(data.user_id)
    except NotFoundError:
        raise ValidationError("unknown user")
    total = sum(data.items)
    return repo.save_order(data.user_id, total)


def get_order(order_id: int) -> repo.Order:
    order = repo.find_order(order_id)
    if order is None:
        raise NotFoundError("order", order_id)
    return order

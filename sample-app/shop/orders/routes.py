from fastapi import APIRouter

from shop.orders import service
from shop.orders.schemas import OrderIn, OrderOut

router = APIRouter(prefix="/orders")


@router.post("", response_model=OrderOut)
def post_order(payload: OrderIn):
    return service.create_order(payload)


@router.get("/{order_id}", response_model=OrderOut)
def get_order_route(order_id: int):
    return service.get_order(order_id)

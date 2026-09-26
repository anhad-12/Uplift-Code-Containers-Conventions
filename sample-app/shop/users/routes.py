from typing import List

from fastapi import APIRouter

from shop.users import service
from shop.users.schemas import UserOut

router = APIRouter(prefix="/users")


@router.get("/{user_id}", response_model=UserOut)
def get_user_route(user_id: int):
    return service.get_user(user_id)


@router.get("", response_model=List[UserOut])
def list_users_route():
    return service.list_users()

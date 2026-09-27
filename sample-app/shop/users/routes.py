from typing import List

from fastapi import APIRouter, HTTPException

from shop.users import service
from shop.users.schemas import UserOut

router = APIRouter(prefix="/users")


@router.get("/{user_id}", response_model=UserOut)
def get_user_route(user_id: int):
    user = service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"user {user_id} not found")
    return user


@router.get("", response_model=List[UserOut])
def list_users_route():
    return service.list_users()

# uplift:item shop/users/routes.py#get_user_route
import pytest
from shop.errors import NotFoundError
from shop.users.service import get_user


def test_get_user_raises_not_found_for_unknown():
    """Base: get_user raises NotFoundError for an unknown id (route returns 404).
    Head (s1-null-user): get_user returns None — FastAPI serialises None as UserOut,
    Pydantic raises ValidationError, route returns 500 instead of 404."""
    with pytest.raises(NotFoundError):
        get_user(99999)

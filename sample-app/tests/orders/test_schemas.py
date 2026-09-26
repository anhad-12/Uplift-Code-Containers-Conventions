import pytest

from pydantic import ValidationError as PydanticValidationError

from shop.orders.schemas import OrderIn


def test_tag_stripping():
    order = OrderIn(user_id=1, items=[1.0], tags=["  food ", " drink"])
    assert order.tags == ["food", "drink"]


def test_tag_empty_stays_empty_string():
    order = OrderIn(user_id=1, items=[1.0], tags=["  "])
    assert order.tags == [""]


def test_note_defaults_to_none():
    order = OrderIn(user_id=1, items=[1.0])
    assert order.note is None


def test_non_numeric_item_rejected():
    with pytest.raises(PydanticValidationError):
        OrderIn(user_id=1, items=["abc"])

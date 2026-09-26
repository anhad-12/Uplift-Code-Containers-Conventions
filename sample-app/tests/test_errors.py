from shop.errors import NotFoundError, ShopError, ValidationError


def test_not_found_error_message():
    err = NotFoundError("user", 42)
    assert str(err) == "user 42 not found"


def test_not_found_error_attributes():
    err = NotFoundError("order", 7)
    assert err.resource == "order"
    assert err.key == 7


def test_validation_error_is_shop_error():
    err = ValidationError("bad input")
    assert isinstance(err, ShopError)

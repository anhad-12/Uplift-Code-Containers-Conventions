from shop.orders import repo


def test_save_returns_order():
    order = repo.save_order(user_id=1, total=9.99)
    assert order.id == 1
    assert order.user_id == 1


def test_find_saved_order():
    saved = repo.save_order(user_id=1, total=5.0)
    found = repo.find_order(saved.id)
    assert found is not None
    assert found.total == 5.0


def test_reset_clears_orders():
    repo.save_order(user_id=1, total=1.0)
    repo.reset()
    assert repo.find_order(1) is None

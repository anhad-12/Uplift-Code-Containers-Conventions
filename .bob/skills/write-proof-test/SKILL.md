---
name: write-proof-test
description: Write a pytest test that proves a predicted break is real. Use after an impact verdict of will_break, to create a test that passes before the change and fails after it.
---

# Write a proof test

A proof test states the OLD contract of the dependent and is expected to PASS on the code before the change and FAIL on the code after the change.

## Rules
1. One file per predicted break, in sample-app/tests/uplift_proofs/, named test_<module>_<slug>.py where <module> is the module of the affected item (users, orders, payments, notifications, admin or core), for example test_orders_create_order_unknown_user.py. Parallel repair workers run only their own module's proofs, so the module prefix is required. The folder has an empty __init__.py.
2. First line of every file: `# uplift:item <candidate id>` (the id from verdicts.json).
3. The test exercises the REAL dependent (the function or the HTTP route through make_client). Never mock the changed function. Never patch or monkeypatch away the changed behaviour.
4. The test asserts the behaviour the dependent had before the change, for the situation that the change alters (for example: an unknown user id is rejected).
5. No sleeps, no randomness, no network, no file writes outside pytest's tmp_path. Use the fake data that already exists in the app.
6. Keep it under 25 lines. A docstring states the OLD contract in one sentence.
7. Never edit production code or any other test. You may only create files in sample-app/tests/uplift_proofs/.

## Template
```python
# uplift:item shop/orders/service.py#create_order
import pytest

from shop.errors import ValidationError
from shop.orders.schemas import OrderIn
from shop.orders.service import create_order


def test_create_order_rejects_unknown_user():
    """OLD contract: an order for a user that does not exist is rejected with ValidationError."""
    with pytest.raises(ValidationError):
        create_order(OrderIn(user_id=999, items=[1.0]))
```
For a route, build the client with `from tests.conftest import make_client` and the route module's router, then assert the HTTP status and body.

## After writing
Run the engine proof runner (MCP tool uplift_proof_run or `uplift proof-run ...`). A proof that does not fail on head is "unconfirmed": report it as such, and do not weaken the test to force a result.

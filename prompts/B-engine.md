# Member B: Engine (demo app, code graph, proof runner, CLI, CI, MCP)

You own everything **deterministic**: what could be affected, what ran, what passed. Bob writes it, you review it. B1 and B2 unblock everyone, so do them first.
Screenshot the task summary after every task (PLAN.md section 11). Log it in `bob_sessions/LOG.md`.

## How to use these prompts

- Paste the whole boxed prompt into a **new Bob task**. Use **Agent mode** (Plan mode first for B3).
- Every prompt gives: goal, exact files, tested reference code, and a **Done when** command. Do not accept "done" from Bob without the command output. If a command fails, paste the failure into the same task and ask Bob to fix it.
- The reference code in these prompts was **run and tested by hand** against the reference demo app. Bob should adapt it, not invent from scratch. If Bob's result differs from the "expected results", the expected results win.
- **Coin figures are guesses.** After your first task check Settings > General and recalibrate. If coins run short, combine: B3+B4, B5+B6, B9+B10. Never skip B1, B2, B4, B7.
- Do not fix core code by hand or with another tool; ask Bob. That keeps the session summaries honest.

## Environment (do this by hand first, 10 minutes)

1. Python **3.11 or 3.12** (`python --version`). Pydantic v1 breaks on 3.13+.
2. Three separate venvs (Pydantic v1 in the demo app conflicts with the `mcp` package):
   `python -m venv engine/.venv`, `python -m venv sample-app/.venv`, `python -m venv dashboard/.venv`.
   On Windows the interpreters are `<folder>/.venv/Scripts/python.exe`.
3. Set `PYTHONUTF8=1` in your terminal (Windows) so console output never fails on encoding.
4. The repo has `.gitattributes` forcing LF line endings. Keep it.

The engine runs the demo app's tests with **the demo app's interpreter** (`--app-python`, default: `sample-app/.venv` python if it exists, else `sys.executable`).

## Two flavours of "the patch"

`--patch <file>` alone: the engine copies the repo to a temp dir and applies the patch there (used by CI on main). `--patch <file> --applied`: the repo already contains the patch (a scenario branch); head is the current tree, base is a temp copy with the patch reverse-applied. Every engine command that takes `--patch` supports both.

---

## B1. Demo app  (about 4 coins, DO FIRST)

The whole demo depends on this app having realistic weaknesses: nobody tests the error path of callers, money is spread across many modules, and a few Pydantic v1-only usages are planted. The reference code below is tested (16 tests pass on the pinned versions). Bob should create it exactly, then extend it.

````text
Read PLAN.md and schema/report.schema.json first.

GOAL: create sample-app/, a small FastAPI shop on Pydantic v1 (Python 3.11/3.12). It is the demo target for Uplift.

RULES (do not deviate):
1. Create EVERY file below with EXACTLY this content. The versions in requirements.txt are tested: fastapi==0.99.1, pydantic==1.10.13, httpx==0.27.2 (httpx 0.28 breaks Starlette's TestClient), pytest==8.3.3. Do not change them.
2. The planted Pydantic v1-only usages must stay exactly as written: BaseSettings (shop/config.py), Config.orm_mode, @validator(..., each_item=True), Optional[str] without a default, Field(regex=...), constr(regex=...).
3. Do NOT add any test that calls get_user (directly or indirectly) with an unknown user id, EXCEPT inside tests/users/test_service.py. Do NOT add tests for shop/admin/reports.py. Do NOT import shop.app in any test; route tests must use make_client(router) from tests/conftest.py. Real codebases do not test every caller's error path, and the demo depends on that.
3b. The scenario patches (task B2) edit three existing test files with exact-text replacements. So do NOT add tests to, or otherwise edit, tests/users/test_service.py, tests/payments/test_charge.py or tests/payments/test_routes.py. Put extra tests for those areas in NEW files (for example tests/users/test_repo.py, tests/users/test_schemas.py, tests/payments/test_schemas.py).
3c. No test anywhere may assert the amount value that charge() returns, or any value derived from it, except the existing tests in test_charge.py and test_routes.py and the receipt/email/invoice tests that build a Payment object directly (as in the reference tests). Scenario S2 changes that unit and must stay invisible to the whole suite.
4. Conventions (a later tool reads them, so be consistent in ALL files): snake_case functions and variables, PascalCase classes, absolute imports only (from shop.x import y, never relative imports), errors are raised as typed exceptions from shop/errors.py (never return None for "not found"), one concern per module, tests mirror shop/ under tests/.
5. No comments, docstrings or docs that hint at scenarios, planted issues, or migrations.

STEPS:
1. Create the files listed below (all of them, including the empty __init__.py files in every package folder under shop/ and tests/).
2. Create the venv and install: `python -m venv sample-app/.venv` then `sample-app/.venv/Scripts/python -m pip install -r sample-app/requirements.txt`.
3. Run `cd sample-app && .venv/Scripts/python -m pytest -q`. Expect 16 passed.
4. Extend the tests to AT LEAST 45 test functions in the same style, following the plan in "EXTRA TESTS". Keep everything green.
5. Write sample-app/README.md (how to create the venv, run the tests). Do not describe any scenario.

EXTRA TESTS (add these, all must pass on the baseline):
- users (new files only: tests/users/test_repo.py, tests/users/test_schemas.py, plus extra functions in tests/users/test_routes.py): repo find/all (3), UserOut schema from a dataclass instance via orm_mode (1), list route returns both users (1), get known user route returns id and name (1).
- orders: OrderIn tag stripping (2), OrderIn note defaults to None when omitted (1), OrderIn rejects a non-numeric item (1), create_order totals an empty items list as 0 (1), get_order of a missing ORDER raises NotFoundError (order, not user) (1), repo save/find/reset (3), invoice total equals order total (1), post/get order routes happy path (2), GET missing order route is 404 (1).
- payments (new files only: tests/payments/test_schemas.py, tests/payments/test_repo.py, tests/payments/test_receipt_more.py): receipt formatting with Payment objects built directly (3), repo save/all/reset (2), PaymentIn accepts a 16-digit card and rejects a short one (2).
- notifications and config: send_welcome for user 2 (1), send_receipt_email formatting (1), get_settings defaults (1).
- errors: NotFoundError message and attributes (2), ValidationError is a ShopError (1).

DONE WHEN:
- `cd sample-app && .venv/Scripts/python -m pytest -q` shows 45 or more passed, 0 failed.
- `grep -rn "999" sample-app/tests` shows the unknown-user id only in tests/users/test_service.py (and order ids in orders tests, which are fine).
- No file outside sample-app/ was changed.
- `git diff --stat` shows tests/users/test_service.py, tests/payments/test_charge.py and tests/payments/test_routes.py exactly as in the reference (unchanged).
Commit: [bob B1] sample shop app

FILES (create exactly):

**`sample-app/requirements.txt`**

```text
fastapi==0.99.1
pydantic==1.10.13
httpx==0.27.2
pytest==8.3.3
```

**`sample-app/pytest.ini`**

```text
[pytest]
testpaths = tests
pythonpath = .
```

**`sample-app/shop/errors.py`**

```python
class ShopError(Exception):
    """Base class for all domain errors."""


class NotFoundError(ShopError):
    def __init__(self, resource: str, key) -> None:
        super().__init__(f"{resource} {key} not found")
        self.resource = resource
        self.key = key


class ValidationError(ShopError):
    pass
```

**`sample-app/shop/config.py`**

```python
from pydantic import BaseSettings


class Settings(BaseSettings):
    sender: str = "shop@example.com"
    smtp_host: str = "localhost"


def get_settings() -> Settings:
    return Settings()
```

**`sample-app/shop/users/repo.py`**

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


_USERS = {
    1: User(1, "Asha Rao", "asha@example.com"),
    2: User(2, "Ben Ito", "ben@example.com"),
}


def find_user(user_id: int):
    return _USERS.get(user_id)


def all_users():
    return list(_USERS.values())
```

**`sample-app/shop/users/schemas.py`**

```python
from pydantic import BaseModel, constr


class UserOut(BaseModel):
    id: int
    name: str
    email: constr(regex=r"^[^@]+@[^@]+$")

    class Config:
        orm_mode = True
```

**`sample-app/shop/users/service.py`**

```python
from shop.errors import NotFoundError
from shop.users import repo


def get_user(user_id: int) -> repo.User:
    user = repo.find_user(user_id)
    if user is None:
        raise NotFoundError("user", user_id)
    return user


def list_users() -> list:
    return repo.all_users()
```

**`sample-app/shop/users/routes.py`**

```python
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
```

**`sample-app/shop/orders/schemas.py`**

```python
from typing import List, Optional

from pydantic import BaseModel, validator


class OrderIn(BaseModel):
    user_id: int
    items: List[float]
    note: Optional[str]
    tags: List[str] = []

    @validator("tags", each_item=True)
    def strip_tag(cls, value):
        return value.strip()


class OrderOut(BaseModel):
    id: int
    user_id: int
    total: float

    class Config:
        orm_mode = True
```

**`sample-app/shop/orders/repo.py`**

```python
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
```

**`sample-app/shop/orders/service.py`**

```python
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
```

**`sample-app/shop/orders/invoice.py`**

```python
from shop.orders.repo import Order
from shop.payments.charge import Payment
from shop.users.service import get_user


def build_invoice(order: Order) -> dict:
    user = get_user(order.user_id)
    return {
        "to": user.email,
        "lines": [{"label": "order", "amount": order.total}],
        "total": order.total,
    }


def payment_line(payment: Payment) -> dict:
    return {"label": "payment", "amount": payment.amount}
```

**`sample-app/shop/orders/routes.py`**

```python
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
```

**`sample-app/shop/payments/schemas.py`**

```python
from pydantic import BaseModel, Field


class PaymentIn(BaseModel):
    user_id: int
    amount: float
    card: str = Field(..., regex=r"^\d{16}$")
```

**`sample-app/shop/payments/charge.py`**

```python
from dataclasses import dataclass

from shop.users.service import get_user


@dataclass
class Payment:
    user_id: int
    amount: float  # dollars


def charge(user_id: int, amount: float) -> Payment:
    get_user(user_id)
    fee = round(amount * 0.029 + 0.30, 2)
    return Payment(user_id, round(amount + fee, 2))
```

**`sample-app/shop/payments/receipt.py`**

```python
from shop.payments.charge import Payment
from shop.users.service import get_user


def render_receipt(payment: Payment) -> str:
    user = get_user(payment.user_id)
    return f"Receipt for {user.name}: ${payment.amount:.2f}"
```

**`sample-app/shop/payments/repo.py`**

```python
from typing import List

from shop.payments.charge import Payment

_PAYMENTS: List[Payment] = []


def save_payment(payment: Payment) -> Payment:
    _PAYMENTS.append(payment)
    return payment


def all_payments() -> List[Payment]:
    return list(_PAYMENTS)


def reset() -> None:
    _PAYMENTS.clear()
```

**`sample-app/shop/payments/routes.py`**

```python
from fastapi import APIRouter

from shop.payments import charge, repo
from shop.payments.schemas import PaymentIn

router = APIRouter(prefix="/payments")


@router.post("")
def post_payment(payload: PaymentIn):
    payment = repo.save_payment(charge.charge(payload.user_id, payload.amount))
    return {"user_id": payment.user_id, "amount": payment.amount}
```

**`sample-app/shop/notifications/email.py`**

```python
from shop.config import get_settings
from shop.payments.charge import Payment
from shop.users.service import get_user


def send_welcome(user_id: int) -> bool:
    user = get_user(user_id)
    if user is None:
        return False
    settings = get_settings()
    return bool(f"from {settings.sender} to {user.email}")


def send_receipt_email(payment: Payment) -> str:
    return f"Thanks! We charged ${payment.amount:.2f}"
```

**`sample-app/shop/admin/reports.py`**

```python
from typing import List

from shop.orders import repo as order_repo
from shop.payments.charge import Payment
from shop.users.service import get_user


def user_spend_report() -> list:
    rows = []
    for order in order_repo.all_orders():
        rows.append({"user": get_user(order.user_id).name, "total": order.total})
    return rows


def revenue_total(payments: List[Payment]) -> float:
    return round(sum(p.amount for p in payments), 2)
```

**`sample-app/shop/app.py`**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shop.errors import NotFoundError, ValidationError
from shop.orders.routes import router as orders_router
from shop.payments.routes import router as payments_router
from shop.users.routes import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="Shop")

    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, exc: NotFoundError):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValidationError)
    async def invalid(request: Request, exc: ValidationError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    for router in (users_router, orders_router, payments_router):
        app.include_router(router)
    return app


app = create_app()
```

**`sample-app/tests/conftest.py`**

```python
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from shop.errors import NotFoundError, ValidationError
from shop.orders import repo as order_repo
from shop.payments import repo as payment_repo


@pytest.fixture(autouse=True)
def clean_orders():
    order_repo.reset()
    payment_repo.reset()
    yield
    order_repo.reset()
    payment_repo.reset()


def make_client(router) -> TestClient:
    """A client for ONE router, so an import error in another module cannot break these tests."""
    app = FastAPI()

    @app.exception_handler(NotFoundError)
    async def not_found(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValidationError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    app.include_router(router)
    return TestClient(app)
```

**`sample-app/tests/users/test_service.py`**

```python
import pytest

from shop.errors import NotFoundError
from shop.users.service import get_user, list_users


def test_get_user_returns_user():
    assert get_user(1).name == "Asha Rao"


def test_get_user_missing_raises():
    with pytest.raises(NotFoundError):
        get_user(999)


def test_list_users():
    assert len(list_users()) == 2
```

**`sample-app/tests/users/test_routes.py`**

```python
from tests.conftest import make_client
from shop.users.routes import router

client = make_client(router)


def test_get_user_route_ok():
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["email"] == "asha@example.com"


def test_list_users_route():
    assert len(client.get("/users").json()) == 2
```

**`sample-app/tests/orders/test_service.py`**

```python
from shop.orders.schemas import OrderIn
from shop.orders.service import create_order, get_order


def make_input(user_id=1):
    return OrderIn(user_id=user_id, items=[10.0, 5.5])


def test_create_order_totals_items():
    assert create_order(make_input()).total == 15.5


def test_get_order_roundtrip():
    order = create_order(make_input())
    assert get_order(order.id).user_id == 1
```

**`sample-app/tests/orders/test_invoice.py`**

```python
from shop.orders.invoice import build_invoice, payment_line
from shop.orders.repo import Order
from shop.payments.charge import Payment


def test_payment_line_uses_the_payment_amount():
    assert payment_line(Payment(1, 103.2)) == {"label": "payment", "amount": 103.2}


def test_invoice_addresses_the_user():
    invoice = build_invoice(Order(1, 1, 20.0))
    assert invoice["to"] == "asha@example.com"
    assert invoice["total"] == 20.0
```

**`sample-app/tests/orders/test_routes.py`**

```python
from tests.conftest import make_client
from shop.orders.routes import router

client = make_client(router)


def test_post_order_ok():
    response = client.post("/orders", json={"user_id": 1, "items": [5, 5]})
    assert response.status_code == 200
    assert response.json()["total"] == 10
```

**`sample-app/tests/payments/test_charge.py`**

```python
from shop.payments.charge import charge


def test_charge_adds_fee_in_dollars():
    assert charge(1, 100.0).amount == 103.2
```

**`sample-app/tests/payments/test_receipt.py`**

```python
from shop.payments.charge import Payment
from shop.payments.receipt import render_receipt


def test_receipt_shows_dollars():
    assert render_receipt(Payment(1, 103.2)) == "Receipt for Asha Rao: $103.20"
```

**`sample-app/tests/payments/test_routes.py`**

```python
from tests.conftest import make_client
from shop.payments.routes import router

client = make_client(router)


def test_post_payment_ok():
    body = {"user_id": 1, "amount": 100, "card": "4242424242424242"}
    assert client.post("/payments", json=body).json()["amount"] == 103.2
```

**`sample-app/tests/notifications/test_email.py`**

```python
from shop.notifications.email import send_receipt_email, send_welcome
from shop.payments.charge import Payment


def test_send_welcome():
    assert send_welcome(1) is True


def test_receipt_email_mentions_the_amount():
    assert send_receipt_email(Payment(1, 103.2)) == "Thanks! We charged $103.20"
```

**`sample-app/tests/payments/test_repo.py`**

```python
from shop.payments import repo
from shop.payments.charge import Payment


def test_save_and_list_payments():
    repo.save_payment(Payment(1, 10.0))
    assert [p.user_id for p in repo.all_payments()] == [1]
```
````


**Expected result:** 16 tests pass on the baseline. With Pydantic 2.9 and FastAPI 0.115 installed instead, several modules fail (scenario S3): `pytest --continue-on-collection-errors` reports failures in orders (Optional field now required), collection errors in payments (`regex` removed), users (`constr(regex=...)`) and notifications (`BaseSettings` moved). That is the intended story.

---

## B2. Scenarios, ground truth and branches  (about 3 coins, DO SECOND)

Three scenarios, each a patch file. **The patches are generated by a script with `difflib`** (LF line endings, no git configuration involved), because Windows git can produce CRLF patches that break `git apply` elsewhere. The script below was tested: S1 and S2 leave the whole suite green (16 passed) while silently breaking callers; S3 breaks four modules.

````text
Read PLAN.md (section 6) first. Work on main.

STEP 1. Create scripts/make_patches.py with EXACTLY this content, then run it from the repo root: `python scripts/make_patches.py`. It writes sample-app/scenarios/s1-null-user.patch, s2-cents.patch and s3-pydantic2.patch.

```python
"""Generate the three scenario patches with difflib (LF only, no git config involved).

Run from the repo root:  python scripts/make_patches.py
Writes sample-app/scenarios/<id>.patch. Paths inside patches are relative to sample-app/ (a/shop/...).
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

APP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sample-app")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else APP / "scenarios"

# Each scenario: {relative path inside sample-app: [(old, new), ...]}. Every `old` must occur exactly once.
SCENARIOS = {
    "s1-null-user": {
        "shop/users/service.py": [
            ("from shop.errors import NotFoundError\n", ""),
            ('    user = repo.find_user(user_id)\n    if user is None:\n        raise NotFoundError("user", user_id)\n    return user\n',
             "    return repo.find_user(user_id)\n"),
        ],
        "tests/users/test_service.py": [
            ("import pytest\n\nfrom shop.errors import NotFoundError\nfrom shop", "from shop"),
            ("def test_get_user_missing_raises():\n    with pytest.raises(NotFoundError):\n        get_user(999)\n",
             "def test_get_user_missing_returns_none():\n    assert get_user(999) is None\n"),
        ],
    },
    "s2-cents": {
        "shop/payments/charge.py": [
            ("    amount: float  # dollars\n", "    amount: int  # cents\n"),
            ("    return Payment(user_id, round(amount + fee, 2))\n", "    return Payment(user_id, round((amount + fee) * 100))\n"),
        ],
        "tests/payments/test_charge.py": [("== 103.2", "== 10320")],
        "tests/payments/test_routes.py": [("== 103.2", "== 10320")],
    },
    "s3-pydantic2": {
        "requirements.txt": [("fastapi==0.99.1", "fastapi==0.115.0"), ("pydantic==1.10.13", "pydantic==2.9.2")],
    },
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, files in SCENARIOS.items():
        chunks: list[str] = []
        for rel, edits in files.items():
            old_text = (APP / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
            new_text = old_text
            for old, new in edits:
                if new_text.count(old) != 1:
                    raise SystemExit(f"{name}: {rel}: expected exactly one occurrence of {old[:50]!r}, found {new_text.count(old)}")
                new_text = new_text.replace(old, new)
            diff = difflib.unified_diff(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                                        fromfile=f"a/{rel}", tofile=f"b/{rel}")
            chunks.append("".join(diff))
        patch = "".join(chunks)
        assert "\r" not in patch
        (OUT / f"{name}.patch").write_text(patch, encoding="utf-8", newline="\n")
        print(f"{name}.patch: {len(files)} file(s), {len(patch.splitlines())} lines")


if __name__ == "__main__":
    main()
```

STEP 2. Verify each patch. For s1-null-user and s2-cents: copy sample-app (without .venv) to a temp folder, `git init` there, `git apply scenarios/<id>.patch`, run `sample-app/.venv/Scripts/python -m pytest -q` inside it: it must show ALL tests passing (that is the point: the change is invisible to the tests). For s3-pydantic2: `git apply --check --directory=sample-app sample-app/scenarios/s3-pydantic2.patch` must succeed. Also confirm there is no carriage return in any patch: `python -c "import sys; sys.exit(any(chr(13).encode() in open(f,'rb').read() for f in sys.argv[1:]))" sample-app/scenarios/*.patch` must exit 0. If STEP 2 is not fully green for S1 or S2, or an exact-text guard in make_patches.py fires because the app was extended, do NOT delete or weaken any test: extend SCENARIOS in scripts/make_patches.py so the patch also updates the author's own tests that directly assert the changed behaviour (a developer making this change would update exactly those), then re-run. The point is that the change is invisible to every other test.

STEP 3. Create scripts/scenario_branch.py with EXACTLY this content and run `python scripts/scenario_branch.py` (working tree must be clean). It creates branches scenario/s1-null-user, scenario/s2-cents, scenario/s3-pydantic2 and returns to main.

```python
"""Create the scenario branches: python scripts/scenario_branch.py <id> [<id> ...]   (ids: s1-null-user, s2-cents, s3-pydantic2)

For each id: branch scenario/<id> from main, apply sample-app/scenarios/<id>.patch, commit, return to main.
The patch paths are relative to sample-app/, so it is applied with --directory=sample-app.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDS = ("s1-null-user", "s2-cents", "s3-pydantic2")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result


def make_branch(sid: str) -> None:
    patch = ROOT / "sample-app" / "scenarios" / f"{sid}.patch"
    if not patch.exists():
        raise SystemExit(f"missing {patch}")
    branch = f"scenario/{sid}"
    if git("rev-parse", "--verify", branch, check=False).returncode == 0:
        print(f"{branch} already exists, skipping")
        return
    git("switch", "main")
    git("switch", "-c", branch)
    git("apply", "--directory=sample-app", str(patch))
    git("add", "-A")
    git("commit", "-m", f"scenario {sid}: apply patch")
    git("switch", "main")
    print(f"created {branch}")


def main() -> None:
    if git("status", "--porcelain").stdout.strip():
        raise SystemExit("commit or stash your changes first (working tree not clean)")
    for sid in sys.argv[1:] or IDS:
        if sid not in IDS:
            raise SystemExit(f"unknown scenario {sid}; expected one of {IDS}")
        make_branch(sid)


if __name__ == "__main__":
    main()
```

STEP 4. Ground truth for S1 and S2 (NOT S3): write sample-app/scenarios/s1-null-user.expected.json and s2-cents.expected.json.
Format:
{"scenario": "s1-null-user", "changedSymbol": "shop/users/service.py#get_user",
 "items": [{"id": "shop/orders/invoice.py#build_invoice", "file": "shop/orders/invoice.py", "expected": "will_break", "evidence": "how you verified it"}]}
where expected is "will_break" or "safe".
Derive ground truth HONESTLY BY EXECUTION, never by opinion: for S1 the situation is "a caller asks about a user id that does not exist"; for S2 it is "a caller receives a Payment produced by the patched charge()". For every place that references the changed symbol (use search and the call graph), write a tiny throwaway script (do not commit it) that runs that code path against the patched tree and observe what happens (exception, wrong value, wrong HTTP status, silent acceptance). expected = will_break if the observable behaviour is wrong compared to the pre-patch behaviour for that situation; safe if it behaves the same or already handles it. Record the observed outcome in "evidence". Include indirect callers that are affected through another caller. Include the "safe" places too (at least one per scenario; if none exist, say so in a top-level "note").
For S3 no expected.json: its ground truth is the real test failures (task B8).

DONE WHEN:
- `ls sample-app/scenarios` shows 3 patches and 2 expected.json files.
- `git branch --list` shows the three scenario branches; on each scenario branch `sample-app/.venv/Scripts/python -m pytest -q` behaves as described in STEP 2.
- You are back on main with a clean tree.
Commit (on main): [bob B2] scenarios, ground truth and scenario branches
````


**Right after B2, by hand (10 seconds):** open `.bobignore` and uncomment the line `sample-app/scenarios/*.expected.json`, then commit `[B2] hide ground truth from Bob`. From now on Bob cannot read the ground truth while predicting. Tell A.

---

## B3. Engine scaffold, trees and diff parser  (Plan mode first, about 3 coins)

Create the Python package with the layout below (tested: `pip install -e .` works, `uplift ...` and `python -m uplift ...` both work). Then implement the diff parser from the reference sketch.

`engine/pyproject.toml` (exact):

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "uplift"
version = "0.1.0"
description = "Predict what a change will break, prove it, repair it."
requires-python = ">=3.11"
dependencies = ["typer>=0.12", "jsonschema>=4", "jedi>=0.19", "unidiff>=0.7"]

[project.optional-dependencies]
dev = ["pytest>=8"]
mcp = ["mcp>=1.2,<2"]

[project.scripts]
uplift = "uplift.cli:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`engine/src/uplift/__main__.py`: `from uplift.cli import app` then `if __name__ == "__main__": app()`. `engine/src/uplift/__init__.py`: empty.

`engine/src/uplift/cli.py` starts as:

```python
import typer

app = typer.Typer(help="Uplift: predict, prove, repair.", no_args_is_help=True)

# One @app.command() per engine command (diff, graph, report, validate, proof-run, migrate-scan,
# upgrade-test, comment, run-all, mcp). Keep all console output ASCII (no box characters, no emoji):
# Windows consoles can raise UnicodeEncodeError otherwise. Also set pretty_exceptions_enable=False if needed.
```

````text
Read PLAN.md and schema/report.schema.json first. Use Plan mode first, then implement.

GOAL: create engine/, the Python package `uplift`, with the diff parser (feature F1).

FILES: engine/pyproject.toml (exact text above), engine/requirements.txt (typer, jsonschema, jedi, unidiff, pytest), engine/src/uplift/{__init__,__main__,cli,diff}.py, engine/tests/test_diff.py.
Then: `python -m venv engine/.venv`, `engine/.venv/Scripts/python -m pip install -e engine[dev]`.

diff.py contains, from the reference sketch below: copy_tree, git_apply, head_and_base (both flavours of the patch), Symbol + symbols_in + enclosing, signature/returns/body helpers, HINT_RULES + hints_for, and changed_symbols. changeType values must be one of the schema enum: signature, returnShape, behavior, removed, renamed, added.

CLI command (typer): `uplift diff --repo <dir> --patch <file> [--applied] --out <file>` writes {"changedSymbols": [...]} as JSON and prints a short ASCII table.

TESTS (engine/tests/test_diff.py). Use a small fixture project created in a tmp_path inside the test (a package with two functions and a patch you write in the test), NOT the real sample-app, so the tests run anywhere. Required cases:
1. A patch that removes a raise and changes the body only: changeType "behavior", hints contain "raise removed".
2. A patch that changes the argument list: "signature".
3. A patch that deletes a function: "removed"; adds a function: "added".
4. --applied and not-applied give the same changedSymbols.
5. Test-only changes (files under tests/) produce no changed symbols.

ALSO run it by hand on the real demo app: `uplift diff --repo sample-app --patch sample-app/scenarios/s1-null-user.patch --out .uplift/diff.json` must list exactly one changed symbol: id "shop/users/service.py#get_user", changeType "behavior", hints containing "raise removed". For s2-cents it must list shop/payments/charge.py#Payment and shop/payments/charge.py#charge, with hints containing "unit scaling added" on charge.

Keep console output ASCII only.
DONE WHEN: `cd engine && .venv/Scripts/python -m pytest -q` passes, and the two manual runs above print the expected symbols.
Commit: [bob B3] engine scaffold and diff parser

REFERENCE SKETCH (tested; adapt and split, keep the behaviour):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import jedi
from unidiff import PatchSet

IGNORE = shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "node_modules")


# ---------- trees ----------
def copy_tree(src: Path) -> Path:
    dst = Path(tempfile.mkdtemp(prefix="uplift_")) / src.name
    shutil.copytree(src, dst, ignore=IGNORE)
    return dst


def git_apply(tree: Path, patch: Path, reverse: bool = False) -> None:
    cmd = ["git", "apply", "--whitespace=nowarn"] + (["-R"] if reverse else []) + [str(patch.resolve())]
    r = subprocess.run(cmd, cwd=tree, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git apply failed: {r.stderr.strip()}")


def head_and_base(repo: Path, patch: Path, applied: bool) -> tuple[Path, Path]:
    """applied=True: repo already contains the patch. Otherwise the patch is applied to a temp copy."""
    if applied:
        base = copy_tree(repo)
        git_apply(base, patch, reverse=True)
        return repo, base
    head = copy_tree(repo)
    git_apply(head, patch)
    return head, repo


# ---------- symbols ----------
@dataclass
class Symbol:
    qualname: str
    kind: str  # function | method | class
    start: int
    end: int
    node: ast.AST = field(repr=False, default=None)


def symbols_in(path: Path) -> list[Symbol]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    out: list[Symbol] = []

    def visit(node, prefix, in_class):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = f"{prefix}{child.name}"
                out.append(Symbol(q, "method" if in_class else "function", child.lineno, child.end_lineno, child))
                visit(child, q + ".", False)
            elif isinstance(child, ast.ClassDef):
                q = f"{prefix}{child.name}"
                out.append(Symbol(q, "class", child.lineno, child.end_lineno, child))
                visit(child, q + ".", True)
            else:
                visit(child, prefix, in_class)

    visit(tree, "", False)
    return out


def enclosing(symbols: list[Symbol], line: int) -> Symbol | None:
    best = None
    for s in symbols:
        if s.start <= line <= s.end and (best is None or (s.end - s.start) < (best.end - best.start)):
            best = s
    return best


def signature_of(node) -> str:
    if isinstance(node, ast.ClassDef):
        return ast.dump(ast.Tuple(elts=node.bases, ctx=ast.Load()))
    return ast.dump(node.args) if hasattr(node, "args") else ""


def returns_of(node) -> str:
    return ast.dump(node.returns) if getattr(node, "returns", None) is not None else ""


def body_of(node) -> str:
    return "|".join(ast.dump(n) for n in getattr(node, "body", []))


HINT_RULES = [
    (r"^\s*raise\b", "removed", "raise removed"),
    (r"^\s*return\s+None\b", "added", "return None added"),
    (r"^\s*if\b.*\bis\s+None\b", "removed", "None check removed"),
    (r"^\s*if\b.*\bis\s+None\b", "added", "None check added"),
    (r"\*\s*100\b|\b100\s*\*", "added", "unit scaling added"),
    (r"/\s*100\b", "added", "unit scaling added"),
]


def hints_for(added: list[str], removed: list[str]) -> list[str]:
    hints = []
    for pattern, side, label in HINT_RULES:
        lines = added if side == "added" else removed
        if any(re.search(pattern, l) for l in lines) and label not in hints:
            hints.append(label)
    num = re.compile(r"\b\d+(\.\d+)?\b")
    if {m.group() for l in added for m in num.finditer(l)} != {m.group() for l in removed for m in num.finditer(l)} and (added or removed):
        if any(num.search(l) for l in added + removed):
            hints.append("numeric literal changed")
    return hints


def changed_symbols(head: Path, base: Path, patch: Path) -> list[dict]:
    """Map every hunk to enclosing symbols in base and head, classify the change."""
    ps = PatchSet(patch.read_text(encoding="utf-8"))
    result: dict[tuple[str, str], dict] = {}
    for pf in ps:
        rel = pf.path  # unidiff strips the a/ b/ prefixes
        if not rel.endswith(".py") or rel.startswith("tests/"):
            continue
        head_syms, base_syms = symbols_in(head / rel), symbols_in(base / rel)
        touched: dict[str, dict] = {}
        for hunk in pf:
            for line in hunk:
                if line.is_added and line.target_line_no:
                    sym = enclosing(head_syms, line.target_line_no)
                    if sym:
                        touched.setdefault(sym.qualname, {"added": [], "removed": []})["added"].append(line.value)
                elif line.is_removed and line.source_line_no:
                    sym = enclosing(base_syms, line.source_line_no)
                    if sym:
                        touched.setdefault(sym.qualname, {"added": [], "removed": []})["removed"].append(line.value)
        head_by = {s.qualname: s for s in head_syms}
        base_by = {s.qualname: s for s in base_syms}
        for q, d in touched.items():
            h, b = head_by.get(q), base_by.get(q)
            if b and not h:
                change = "removed"
            elif h and not b:
                change = "added"
            elif signature_of(h.node) != signature_of(b.node):
                change = "signature"
            elif returns_of(h.node) != returns_of(b.node):
                change = "returnShape"
            else:
                change = "behavior"
            kind = (h or b).kind
            result[(rel, q)] = {"id": f"{rel}#{q}", "kind": kind, "changeType": change,
                                "hints": hints_for(d["added"], d["removed"])}
    return list(result.values())


# ---------- graph ----------
def find_candidates(head: Path, changed: list[dict], max_hops: int = 3) -> list[dict]:
    project = jedi.Project(path=str(head))
    seen: set[str] = {c["id"] for c in changed}
    frontier = [c["id"] for c in changed]
    candidates: list[dict] = []
    for hop in range(1, max_hops + 1):
        nxt = []
        for sym_id in frontier:
            rel, qual = sym_id.split("#", 1)
            path = head / rel
            sym = next((s for s in symbols_in(path) if s.qualname == qual), None)
            if not sym:
                continue
            col = path.read_text(encoding="utf-8").splitlines()[sym.start - 1].index(qual.split(".")[-1])
            script = jedi.Script(path=str(path), project=project)
            for ref in script.get_references(sym.start, col, include_builtins=False):
                if ref.is_definition() or not ref.module_path:
                    continue
                ref_path = Path(ref.module_path)
                try:
                    ref_rel = ref_path.resolve().relative_to(head.resolve()).as_posix()
                except ValueError:
                    continue
                if ref_rel.startswith("tests/") or not ref_rel.endswith(".py"):
                    continue
                enc = enclosing(symbols_in(ref_path), ref.line)
                if not enc:
                    continue
                cid = f"{ref_rel}#{enc.qualname}"
                if cid in seen:
                    continue
                seen.add(cid)
                lines = ref_path.read_text(encoding="utf-8").splitlines()
                snippet = "\n".join(lines[max(0, ref.line - 4): ref.line + 4])
                parts = ref_rel.split("/")
                candidates.append({"id": cid, "file": ref_rel, "line": ref.line, "hop": hop, "via": sym_id,
                                   "module": parts[1] if len(parts) > 2 else "core",
                                   "layer": "direct" if hop == 1 else "indirect", "snippet": snippet})
                nxt.append(cid)
        frontier = nxt
    return candidates


# ---------- junit ----------
def run_pytest(python: str, cwd: Path, extra: list[str] | None = None) -> dict:
    fd, name = tempfile.mkstemp(suffix=".xml")  # keep the junit file OUT of the tree under test
    os.close(fd)
    xml = Path(name)
    cmd = [python, "-m", "pytest", "-q", "-p", "no:warnings", "--continue-on-collection-errors", f"--junitxml={xml}"] + (extra or [])
    try:
        subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return parse_junit(xml)
    finally:
        xml.unlink(missing_ok=True)


def parse_junit(xml: Path) -> dict:
    root = ET.parse(xml).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    out = {"passed": 0, "failed": 0, "cases": {}}
    for suite in suites:
        for case in suite.iter("testcase"):
            # collection errors have classname "" and the dotted module in `name`
            name = f"{case.get('classname')}::{case.get('name')}" if case.get("classname") else f"{case.get('name')}::<collection>"
            bad = case.find("failure") is not None or case.find("error") is not None
            out["cases"][name] = "failed" if bad else "passed"
            out["failed" if bad else "passed"] += 1
    return out
```
````


---

## B4. Reference graph  (about 3 coins)

````text
Read PLAN.md. In engine/src/uplift/graph.py implement `find_candidates` from the reference sketch in task B3 (it is already in the sketch: jedi references, enclosing function, up to 3 hops, snippet, module, layer). Improve it as follows:
- If jedi cannot resolve a reference (dynamic code), fall back to a name-based match with the ast module and add "resolution": "name" to that candidate; resolved ones get "resolution": "jedi".
- Deduplicate, no cycles, at most 200 candidates.
- Skip references inside tests/.
- module = first folder under shop/ (files directly in shop/ get "core").

CLI: `uplift graph --repo <dir> --patch <file> [--applied] --out .uplift/graph.json` runs diff + graph and writes {"changedSymbols": [...], "candidates": [...], "filesScanned": N, "secondsTaken": S}; print a short ASCII summary table (hop, id, module).

EXPECTED RESULTS on the reference demo app (write these as tests in engine/tests/test_graph.py; skip the test with a clear message if sample-app/ or its scenario patches are missing):
- s1-null-user: 9 candidates. Hop 1 (7): shop/admin/reports.py#user_spend_report, shop/notifications/email.py#send_welcome, shop/orders/invoice.py#build_invoice, shop/orders/service.py#create_order, shop/payments/charge.py#charge, shop/payments/receipt.py#render_receipt, shop/users/routes.py#get_user_route. Hop 2 (2): shop/orders/routes.py#post_order (via create_order), shop/payments/routes.py#post_payment (via charge).
- s2-cents: at least these hop-1 candidates: shop/admin/reports.py#revenue_total, shop/notifications/email.py#send_receipt_email, shop/orders/invoice.py#payment_line, shop/payments/receipt.py#render_receipt, shop/payments/repo.py#save_payment, shop/payments/routes.py#post_payment.
Also add a small fixture-based unit test (tmp_path project) that proves indirect (hop 2) detection and the name-based fallback.

DONE WHEN: `cd engine && .venv/Scripts/python -m pytest -q` passes and `uplift graph --repo sample-app --patch sample-app/scenarios/s1-null-user.patch --out .uplift/graph.json` prints the 9 candidates above.
Commit: [bob B4] reference graph walk
````


---

## B5. Routes, contracts and test mapping  (about 3 coins)

````text
Read PLAN.md. Create engine/src/uplift/routes.py and engine/src/uplift/testmap.py from the reference sketch below (tested), then wire them into `uplift graph`.

routes.py: `route_map(root)` finds FastAPI routes from decorators (`@router.get/post/put/delete/patch("...")` on an APIRouter(prefix=...)), returns [{method, path, handler: "file#function", file}]. Also handle `app.include_router(router, prefix="/x")` (add the extra prefix) if present.
After the graph walk: every candidate whose id equals a route handler adds a `contracts` entry {"type": "route", "id": "GET /users/{user_id}", "handler": "<id>", "verdict": "unknown"}. A candidate reachable only through such a handler is still listed as a normal candidate; the route itself is the contract.
testmap.py: `tests_for(root, files)` maps each affected file to the tests that import it, directly or one level through another module (ast on imports). Fill candidate["tests"], the top-level testsToRun (union, sorted) and `untested` (candidates whose "tests" is empty).

EXPECTED on the reference demo app, s1-null-user (write as tests; skip with a message if sample-app is missing):
- routes: POST /orders, GET /orders/{order_id}, POST /payments, GET /users/{user_id}, GET /users.
- contracts include GET /users/{user_id} (handler shop/users/routes.py#get_user_route), POST /orders, POST /payments.
- untested includes shop/admin/reports.py#user_spend_report (there are no tests for the admin package).
Add a fixture-based unit test for tests_for (tmp_path project with two tests importing a module directly and via another module).

DONE WHEN: engine tests pass and `.uplift/graph.json` now has "contracts", "testsToRun" and "untested".
Commit: [bob B5] routes and test mapping

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import ast
from pathlib import Path

HTTP = {"get", "post", "put", "delete", "patch"}


# ---------- routes ----------
def route_map(root: Path) -> list[dict]:
    routes = []
    for path in sorted((root / "shop").rglob("routes.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        prefixes: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "APIRouter":
                prefix = next((kw.value.value for kw in node.value.keywords if kw.arg == "prefix"), "")
                for target in node.targets:
                    prefixes[target.id] = prefix
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in HTTP
                        and isinstance(dec.func.value, ast.Name) and dec.func.value.id in prefixes):
                    sub = dec.args[0].value if dec.args and isinstance(dec.args[0], ast.Constant) else ""
                    routes.append({"method": dec.func.attr.upper(), "path": prefixes[dec.func.value.id] + sub,
                                   "handler": f"{rel}#{node.name}", "file": rel})
    return routes


# ---------- test mapping ----------
def module_of(path: Path, root: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def imports_of(path: Path) -> set[str]:
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out.update(f"{node.module}.{a.name}" for a in node.names)
    return out


def tests_for(root: Path, files: list[str]) -> dict[str, list[str]]:
    src_mods = {module_of(p, root): p.relative_to(root).as_posix() for p in (root / "shop").rglob("*.py")}
    src_imports = {rel: imports_of(root / rel) for rel in src_mods.values()}
    tests = [p for p in (root / "tests").rglob("test_*.py") if "uplift_proofs" not in p.parts]
    test_imports = {p.relative_to(root).as_posix(): imports_of(p) for p in tests}
    result: dict[str, list[str]] = {}
    for f in files:
        mod = module_of(root / f, root)
        found = []
        importers = {rel for rel, imps in src_imports.items() if mod in imps}  # one level through another module
        for t, imps in test_imports.items():
            if mod in imps or any(module_of(root / i, root) in imps for i in importers):
                found.append(t)
        result[f] = sorted(found)
    return result
```
````


---

## B6. Report, risk score, validation  (about 2 coins)

````text
Read PLAN.md and schema/report.schema.json. Create engine/src/uplift/report.py from the reference sketch below (tested: the report it builds validates against the schema).

Requirements:
- `uplift report --graph .uplift/graph.json [--verdicts .uplift/verdicts.json] [--proofs .uplift/proofs.json] [--repairs .uplift/repair-*.json] [--catalog .uplift/catalog.json] --scenario <id> --title "<title>" --out reports/<id>.json`
- verdicts.json is a JSON array of {id, verdict, reason, fix}; merge by candidate id; candidates without a verdict get "unknown". proofs.json (see B7) fills affected[].proof; repair-*.json files fill affected[].repair and pipeline/metrics (see below).
- risk exactly as in the schema description: score = min(100, 10*willBreak + 4*mightBreak + 12*untestedAffected + 15*contractHits); low<30, medium<60, high<80, critical>=80; risk.factors lists the arithmetic in words.
- metrics: filesScanned, secondsTaken, predicted (will_break items + will_break contracts), confirmed (proof status confirmed), unconfirmed, fixed (repair status fixed), regressions (default 0), tests.before/after when a repair file provides them.
- pipeline: predict "done" once a graph exists; prove "done" if proofs.json exists; repair "done" if any repair file exists; verify "pending" until told otherwise (a `--verified` flag sets it to done).
- provenance.generatedBy = "bob" if a verdicts file was given, otherwise "engine"; bobModes: pass with `--bob-modes a,b,c`.
- `uplift validate <files...>`: validate each report with jsonschema (Draft7) against schema/report.schema.json, found by walking up from the file to the repo root; print PASS/FAIL per file, exit 1 on any failure.
TESTS: risk formula with 3 hand-computed cases (0 items = 0 low; 4 will_break + 1 might_break + 1 untested + 1 contract hit = 71 high; a case that caps at 100); merge test with a tiny hand-written graph.json + verdicts.json; a test that the built report passes `validate`; graph-only run has provenance "engine" and every verdict "unknown".
DONE WHEN: `uplift report --graph .uplift/graph.json --scenario s1-null-user --title "S1" --out reports/s1-null-user.json` then `uplift validate reports/s1-null-user.json` prints PASS; engine tests pass.
Commit: [bob B6] report merge, risk and validation

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import time
from pathlib import Path

from uplift.diff import changed_symbols, head_and_base
from uplift.graph import find_candidates
from uplift.routes import route_map
from uplift.testmap import tests_for


# ---------- risk + report ----------
def risk(affected: list[dict], contracts: list[dict], untested: list[str]) -> dict:
    wb = sum(1 for a in affected if a["verdict"] == "will_break")
    mb = sum(1 for a in affected if a["verdict"] == "might_break")
    ch = sum(1 for c in contracts if c["verdict"] in ("will_break", "might_break"))
    score = min(100, 10 * wb + 4 * mb + 12 * len(untested) + 15 * ch)
    level = "low" if score < 30 else "medium" if score < 60 else "high" if score < 80 else "critical"
    factors = [f"{wb} will_break (+{10*wb})", f"{mb} might_break (+{4*mb})",
               f"{len(untested)} untested affected item (+{12*len(untested)})", f"{ch} contract hit (+{15*ch})"]
    return {"score": score, "level": level, "factors": factors}


def build_report(repo: Path, patch: Path, applied: bool, verdicts: dict[str, dict], scenario: dict) -> dict:
    t0 = time.time()
    head, base = head_and_base(repo, patch, applied)
    changed = changed_symbols(head, base, patch)
    cands = find_candidates(head, changed)
    routes = route_map(head)
    tm = tests_for(head, sorted({c["file"] for c in cands}))
    handlers = {r["handler"]: r for r in routes}
    affected, contracts = [], []
    for c in cands:
        v = verdicts.get(c["id"], {"verdict": "unknown"})
        item = {**c, "tests": tm.get(c["file"], []), "verdict": v["verdict"], "reason": v.get("reason", ""), "fix": v.get("fix", ""),
                "proof": {"status": "not_attempted"}}
        affected.append(item)
        if c["id"] in handlers:
            r = handlers[c["id"]]
            contracts.append({"type": "route", "id": f"{r['method']} {r['path']}", "handler": c["id"], "verdict": v["verdict"]})
    untested = [a["id"] for a in affected if not a["tests"]]
    rk = risk(affected, contracts, untested)
    predicted = sum(1 for a in affected if a["verdict"] == "will_break") + sum(1 for c in contracts if c["verdict"] == "will_break")
    return {
        "schemaVersion": 1, "mode": "impact",
        "provenance": {"generatedBy": "engine", "bobModes": []},
        "scenario": scenario,
        "change": {"summary": "demo", "kind": "patch", "patchFile": str(patch)},
        "changedSymbols": changed, "affected": affected, "contracts": contracts,
        "testsToRun": sorted({t for a in affected for t in a["tests"]}), "untested": untested,
        "risk": rk,
        "pipeline": {"predict": "done", "prove": "pending", "repair": "pending", "verify": "pending"},
        "migration": None,
        "metrics": {"filesScanned": sum(1 for _ in (head / "shop").rglob("*.py")), "secondsTaken": round(time.time() - t0, 1),
                    "predicted": predicted, "confirmed": 0},
    }
```
````


---

## B7. Proof runner  (about 4 coins, the key feature)

A proof is confirmed only if it **passes on base and fails on head**. The reference sketch below was tested in both flavours: a real proof came out `confirmed`, and a control test that passes everywhere came out `unconfirmed`.

````text
Read PLAN.md. Create engine/src/uplift/proof.py from the reference sketch below (it uses run_pytest and parse_junit, which are already in the task-B3 sketch; move them here or import them).

Command: `uplift proof-run --repo <dir> --patch <file> [--applied] --proofs <dir> [--app-python <path>] --out .uplift/proofs.json`.
Behaviour:
- Build base and head trees per the two flavours (head_and_base). Copy the proofs directory into whichever tree lacks it.
- Run pytest with the demo app's interpreter (`--app-python`, default: sample-app/.venv python if present, else sys.executable) inside each tree, with `--continue-on-collection-errors`, and a junit XML file created OUTSIDE the tree under test (tempfile). Never leave files in the repo.
- Collection errors appear in junit as a testcase with an EMPTY classname and the dotted module in `name`; treat such a file as "did not run" (fails on head, and unconfirmed if it also fails on base).
- Map each proof file to an affected item with a first-line comment `# uplift:item <id>`; fall back to the file stem.
- status = "confirmed" only if passesOnBase and failsOnHead; else "unconfirmed".
- Also record the full-suite counts on base and head (a second pytest run of the whole tests/ folder without the proofs folder).
Output: {"proofs": [{"item", "testFile", "passesOnBase", "failsOnHead", "status"}], "suite": {"base": {"passed", "failed"}, "head": {"passed", "failed"}}}.
Also print an ASCII table.

TESTS with a tiny fixture project in tmp_path (package with a function; a patch that changes its behaviour; two proof files: one that checks the old behaviour (must be confirmed) and one control that passes on both (must be unconfirmed); a proof that does not compile on head (unconfirmed with a clear message)). Test both flavours (--applied and not). Assert no *.xml file is left in the repo tree.

END-TO-END CHECK (by hand, real demo app, branch scenario/s1-null-user): write one proof file sample-app/tests/uplift_proofs/test_create_order_unknown_user.py asserting that creating an order for user_id 999 raises ValidationError; run proof-run with --applied; expect confirmed. Delete that hand-made file afterwards (Member A's Prover writes the real ones).
DONE WHEN: engine tests pass and the end-to-end check prints "confirmed".
Commit: [bob B7] proof runner

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from proto_engine import head_and_base, run_pytest  # noqa: E402

ITEM = re.compile(r"^#\s*uplift:item\s+(\S+)", re.M)


def proof_run(repo: Path, patch: Path, proofs_dir: Path, app_python: str, applied: bool) -> dict:
    head, base = head_and_base(repo, patch, applied)
    rel = proofs_dir.resolve().relative_to(repo.resolve())
    for tree in (head, base):  # base (or head) may be a temp copy that lacks the proofs
        if tree.resolve() != repo.resolve():
            shutil.copytree(repo / rel, tree / rel, dirs_exist_ok=True)
    on_base = run_pytest(app_python, base, [rel.as_posix()])
    on_head = run_pytest(app_python, head, [rel.as_posix()])
    proofs = []
    for f in sorted((repo / rel).glob("test_*.py")):
        module = ".".join((rel / f.stem).parts)  # tests.uplift_proofs.test_x
        def status(result):
            cases = [v for k, v in result["cases"].items() if k.startswith(module + "::")]
            return cases  # empty list = the file did not run (collection error is keyed by module name)
        b, h = status(on_base), status(on_head)
        passes_on_base = bool(b) and all(c == "passed" for c in b)
        fails_on_head = (not h) or any(c == "failed" for c in h)
        m = ITEM.search(f.read_text(encoding="utf-8"))
        proofs.append({"item": m.group(1) if m else f.stem, "testFile": (rel / f.name).as_posix(),
                       "passesOnBase": passes_on_base, "failsOnHead": fails_on_head,
                       "status": "confirmed" if passes_on_base and fails_on_head else "unconfirmed"})
    return {"proofs": proofs, "suite": {"base": {k: on_base[k] for k in ("passed", "failed")},
                                        "head": {k: on_head[k] for k in ("passed", "failed")}}}
```
````


---

## B8. Migrate scan and upgrade test  (about 4 coins)

Tested behaviour on the reference app under Pydantic 2.9: **collection errors abort pytest unless you pass `--continue-on-collection-errors`**, and a collection error shows up in junit with an empty classname (module in `name`).

````text
Read PLAN.md and schema/report.schema.json. Create engine/src/uplift/migrate.py from the reference sketch below (tested), with these commands:

1. `uplift migrate-scan --repo <dir> --catalog <file> --out .uplift/occurrences.json`: for each catalog entry use its `detect` ({type: call | identifier | import | regex, pattern}) to find every occurrence in the repo's shop/ package: file, line, module, snippet. Output {"occurrences": [...], "counts": {"<entry id>": N}}.
2. `uplift upgrade-test --repo <dir> --requirements <file> --out .uplift/upgrade-before.json`: copy the repo to a temp dir; create a TEMPORARY venv there (`python -m venv`), `pip install -r` the upgraded requirements file, run pytest with `--continue-on-collection-errors` and a junit XML file outside the tree, group results per module (tests/<module>/...; collection errors and other cases go by the module in their name or "core") and output {"passed", "failed", "byModule": {"orders": {"passed", "failed"}, ...}}. Add `--current` to run the same with an existing interpreter instead of building a temp venv (for baselines and after-runs), and `--app-python <path>` to choose that interpreter (for S3 use `sample-app/.venv-v2/Scripts/python.exe`, the Pydantic 2 environment). With `--current` the command simply reports per-module test counts in that interpreter. Delete any temp venv when done.
3. Extend `uplift report`: with `--catalog`, fill migration.catalog (entries + occurrences counts) and migration.modules (from .uplift/repair-<module>-<scenario>.json files: module, worker, filesChanged, fixesApplied, testsBefore, testsAfter); create affected[] entries from occurrences (one per occurrence: id "<file>#<enclosing function or module>", verdict from verdicts if present, hop 1, layer "direct", via "requirements.txt#pydantic"); set change.kind "dependency-upgrade" with library/from/to read from `--library pydantic --from 1.10.13 --to 2.9.2`; changedSymbols = [{"id": "requirements.txt#pydantic", "kind": "dependency", "changeType": "dependency"}].

EXPECTED (tests skip with a message if sample-app is missing): on the reference demo app with this catalog
[{"id": "p2-basesettings", "detect": {"type": "import", "pattern": "from pydantic import BaseSettings"}}, {"id": "p2-orm-mode", "detect": {"type": "regex", "pattern": "orm_mode\\s*=\\s*True"}}, {"id": "p2-field-regex", "detect": {"type": "regex", "pattern": "\\bregex\\s*="}}, {"id": "p2-validator", "detect": {"type": "call", "pattern": "validator"}}, {"id": "p2-optional", "detect": {"type": "regex", "pattern": ":\\s*Optional\\[[^\\]]+\\]\\s*$"}}]
the scan finds: basesettings 1 (core), orm-mode 2 (users and orders), validator 1 (orders), optional 1 (orders), regex 2 (payments and users). The upgrade test with pydantic==2.9.2 and fastapi==0.115.0 reports 6 failed and 8 passed, with failures in notifications 1, payments 1, users 1, orders 3.
Also fixture-based unit tests for scan (each detect type) and for the per-module grouping including a collection error.
DONE WHEN: engine tests pass; the scan and upgrade-test commands print the expected numbers on the real demo app (run the upgrade-test on branch scenario/s3-pydantic2, requirements from that branch).
Commit: [bob B8] migrate scan and upgrade test

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from proto_engine import copy_tree, run_pytest  # noqa: E402

CATALOG = [
    {"id": "p2-basesettings", "detect": {"type": "import", "pattern": "from pydantic import BaseSettings"}},
    {"id": "p2-orm-mode", "detect": {"type": "regex", "pattern": r"orm_mode\s*=\s*True"}},
    {"id": "p2-field-regex", "detect": {"type": "regex", "pattern": r"\bregex\s*="}},
    {"id": "p2-validator", "detect": {"type": "call", "pattern": "validator"}},
    {"id": "p2-optional", "detect": {"type": "regex", "pattern": r":\s*Optional\[[^\]]+\]\s*$"}},
]


def module_of(rel: str) -> str:
    parts = rel.split("/")
    return parts[1] if len(parts) > 2 and parts[0] == "shop" else "core"


def scan(root: Path, catalog: list[dict]) -> list[dict]:
    out = []
    for path in sorted((root / "shop").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        for entry in catalog:
            d = entry["detect"]
            hits: list[int] = []
            if d["type"] == "regex":
                hits = [i + 1 for i, l in enumerate(lines) if re.search(d["pattern"], l)]
            elif d["type"] == "import":
                hits = [i + 1 for i, l in enumerate(lines) if l.strip() == d["pattern"] or d["pattern"] in l]
            elif d["type"] in ("call", "identifier") and tree is not None:
                for node in ast.walk(tree):
                    name = None
                    if d["type"] == "call" and isinstance(node, ast.Call):
                        f = node.func
                        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                    elif d["type"] == "identifier" and isinstance(node, ast.Name):
                        name = node.id
                    if name == d["pattern"]:
                        hits.append(node.lineno)
            for h in sorted(set(hits)):
                out.append({"entry": entry["id"], "file": rel, "line": h, "module": module_of(rel),
                            "snippet": "\n".join(lines[max(0, h - 2): h + 1])})
    return out


def failures_by_module(result: dict) -> dict[str, dict]:
    by = defaultdict(lambda: {"passed": 0, "failed": 0})
    for case, status in result["cases"].items():
        parts = case.split("::")[0].split(".")  # tests.orders.test_service -> orders
        module = parts[1] if len(parts) > 2 and parts[0] == "tests" else "core"
        by[module][status] += 1
    return dict(by)
```
````


---

## B9. CLI polish, run-all and PR comment  (about 2 coins)

````text
Read PLAN.md. Polish engine/src/uplift/cli.py and add engine/src/uplift/comment.py.

1. Every command has --help with a one-line description and every option documented; exit code 1 on failure with a clear ASCII message; all output ASCII.
2. `uplift run-all --repo <dir> --patch <file> [--applied] --scenario <id>` runs diff + graph + routes + tests and writes .uplift/graph.json, then prints the NEXT STEPS for Bob (which mode to switch to and which prompt file to use). It must NOT call any LLM.
3. comment.py from the reference sketch below (tested): `uplift comment --report <file>` prints a Markdown PR comment (risk line, item table sorted by verdict, contracts, untested code, tests to run, metrics line). If no item has a verdict, it says "Graph only. Verdicts, proofs and repairs come from a Bob run."
4. Unit-test the comment output on schema/examples/impact-s1.mock.json (contains the risk line "Risk 71/100 (high)", the table header, and a contracts line) and on a graph-only report.
DONE WHEN: engine tests pass; `uplift --help` lists diff, graph, report, validate, proof-run, migrate-scan, upgrade-test, comment, run-all.
Commit: [bob B9] cli polish and pr comment

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import json
from pathlib import Path


# ---------------- PR comment ----------------
BADGE = {"low": "green", "medium": "yellow", "high": "orange", "critical": "red"}


def pr_comment(report: dict) -> str:
    r, m = report["risk"], report["metrics"]
    lines = [f"### Uplift: blast radius for `{report['scenario']['title']}`", "",
             f"**Risk {r['score']}/100 ({r['level']})** - {'; '.join(r.get('factors', []))}", ""]
    has_verdicts = any(a["verdict"] != "unknown" for a in report["affected"])
    if not has_verdicts:
        lines += ["_Graph only. Verdicts, proofs and repairs come from a Bob run._", ""]
    lines += ["| Item | Verdict | Proof | Reason |", "| --- | --- | --- | --- |"]
    for a in sorted(report["affected"], key=lambda a: ["will_break", "might_break", "unknown", "safe"].index(a["verdict"])):
        lines.append(f"| `{a['id']}` | {a['verdict']} | {(a.get('proof') or {}).get('status', '-')} | {a.get('reason', '')} |")
    if report.get("contracts"):
        lines += ["", "**API contracts:** " + ", ".join(f"`{c['id']}` ({c['verdict']})" for c in report["contracts"])]
    if report.get("untested"):
        lines += ["", "**Untested affected code:** " + ", ".join(f"`{u}`" for u in report["untested"])]
    lines += ["", f"**Tests to run:** {', '.join(report.get('testsToRun', [])) or 'none'}", "",
              f"predicted {m['predicted']}, confirmed {m['confirmed']}, fixed {m.get('fixed', 0)}, regressions {m.get('regressions', 0)}"]
    return "\n".join(lines)
```
````


---

## B10. CI and GitHub Action  (about 2 coins)

````text
Read PLAN.md. Create three files.

.github/workflows/ci.yml:
name: ci
on: [push, pull_request]
jobs:
  engine:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -e "engine[dev]" -r sample-app/requirements.txt
      - run: cd engine && python -m pytest -q
  sample-app:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r sample-app/requirements.txt
      - run: cd sample-app && python -m pytest -q
(The engine job installs the demo app's requirements into the same environment so engine tests that run the demo app's tests work; do NOT install the mcp extra there.)

.github/workflows/uplift.yml: on pull_request; permissions: contents read, pull-requests write; steps: checkout with fetch-depth 0; setup-python 3.12; `pip install -e engine -r sample-app/requirements.txt`; build the PR patch with `git diff origin/${{ github.base_ref }}...HEAD --relative=sample-app -- sample-app > /tmp/pr.patch` (skip the job with a message if it is empty); `uplift graph --repo sample-app --patch /tmp/pr.patch --applied --out .uplift/graph.json`; `uplift report --graph .uplift/graph.json --scenario pr --title "Pull request" --out reports/pr.json`; `uplift comment --report reports/pr.json > comment.md`; post it with `gh pr comment ${{ github.event.pull_request.number }} --edit-last --create-if-none --body-file comment.md` using env GH_TOKEN: ${{ github.token }}. The comment is graph-only, which is honest: it says verdicts come from a Bob run.

engine/README.md: a table of every uplift command with its options and an example each; setup steps (venvs, PYTHONUTF8=1). LICENSE already exists at the repo root; do not recreate it.
DONE WHEN: both workflow files are valid YAML (`python -c "import yaml; yaml.safe_load(open(path))"` for each; install pyyaml if needed) and the README lists all commands.
Commit: [bob B10] ci and action
````


---

## B11. MCP server  (about 3 coins)

Tested: the official `mcp` package version 1.x exposes `FastMCP` and registers tools; **version 2.x renamed the API, so the extra is pinned `mcp>=1.2,<2`** (already in pyproject.toml under `[project.optional-dependencies] mcp`).

Bob's MCP config (verified from the Bob 2.0 install): workspace file `.bob/mcp.json`, top-level `mcpServers`; each server has `command`, `args`, optional `env`, `alwaysAllow`, `disabledTools`, `groups` (limit the server to specific mode slugs). It hot-reloads on save. `${workspaceFolder}` is expanded.

````text
Read PLAN.md. Install the extra in the engine venv: `engine/.venv/Scripts/python -m pip install -e "engine[mcp]"`.

Create engine/src/uplift/mcp_server.py from the reference sketch below (tested). Expose FOUR tools that call the existing engine functions directly (no new logic) and return short JSON strings:
- uplift_graph(repo: str, patch: str, applied: bool = False) -> writes .uplift/graph.json
- uplift_proof_run(repo: str, patch: str, proofs: str, applied: bool = False) -> writes .uplift/proofs.json
- uplift_migrate_scan(repo: str, catalog: str) -> writes .uplift/occurrences.json
- uplift_report(scenario: str, title: str) -> assembles reports/<scenario>.json from whatever .uplift/*.json files exist
Add the CLI command `uplift mcp` (stdio transport: `mcp.run()`), and a test that lists the four tool names.
Then create or update .bob/mcp.json (read it first; never overwrite blindly):
{"mcpServers": {"uplift": {"command": "${workspaceFolder}/engine/.venv/Scripts/python.exe", "args": ["-m", "uplift", "mcp"], "alwaysAllow": ["uplift_graph", "uplift_proof_run", "uplift_migrate_scan", "uplift_report"]}}}
Do NOT add a "groups" field to the server: its meaning is ambiguous in Bob's docs, and access is already limited because only four modes (uplift-impact-analyst, uplift-prover, uplift-migration-planner, uplift-verifier) have the `mcp` permission group in .bob/custom_modes.yaml. Explain how to confirm the server connected (Bob's MCP panel) and how to run one tool call from one of those modes.
DONE WHEN: engine tests pass; Bob's MCP panel shows "uplift" connected with 4 tools (screenshot it for the session log).
Commit: [bob B11] mcp server

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import json
from pathlib import Path


# ---------------- MCP skeleton ----------------
def build_mcp():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("uplift")

    @mcp.tool()
    def uplift_graph(repo: str, patch: str, applied: bool = False) -> str:
        """Build the blast-radius graph for a patch and write .uplift/graph.json."""
        return json.dumps({"ok": True, "repo": repo, "patch": patch, "applied": applied})

    return mcp
```
````


---

## B12. Fix prompts and hardening  (remaining coins)

Failures found by `python scripts/verify.py --run` or by a review of Bob's output. Write the exact fix prompt and paste it into the same Bob task. Typical issues: `Client.__init__() got an unexpected keyword 'app'` (httpx is not 0.27.2), an ImportError on `mcp.server.fastmcp` (mcp is 2.x, pin `<2`), pytest aborting on a collection error (missing `--continue-on-collection-errors`), CRLF in a patch, a proof that never fails on head.

---

## B13. Docker impact  (F17, STRETCH: only after CP2 is green, about 4 coins)

````text
Read PLAN.md (F17) and the `infraImpact` field in schema/report.schema.json.

1. sample-app/Dockerfile: a realistic multi-stage Python build (python:3.12-slim) with ONE deliberate layer-ordering inefficiency (`COPY . .` before `RUN pip install -r requirements.txt`). Add sample-app/.dockerignore. Not part of the tests.
2. engine/src/uplift/docker.py from the reference sketch below (tested): parse FROM/COPY/ADD/RUN/WORKDIR into a layer map; `docker_impact(dockerfile, changed_files)` returns infraImpact entries {file, layer, totalLayers, trigger, layersRebuilt, suggestion}.
3. Wire into `uplift graph` (changed files from the patch, plus requirements.txt if the patch touches it) and `uplift report` (top-level infraImpact list). Only when a Dockerfile exists.
4. NEVER invent a time cost. Include `measuredRebuildSeconds` only if you actually measured it with `docker build` on this machine; otherwise omit it.
5. Tests with two small fixture Dockerfiles (one with the inefficiency, one well ordered which yields no requirements.txt warning).
DONE WHEN: engine tests pass; on the demo app, a patch touching shop/users/service.py reports "layers 2-N rebuild" for the deliberate inefficiency.
Commit: [bob B13] dockerfile layer impact

REFERENCE SKETCH (tested):

```python
# Reference sketch. It was run and tested against the reference demo app. Adapt it, split it into the modules named in the task, add type hints and tests; keep the behaviour.
from __future__ import annotations

import re
from pathlib import Path


# ---------------- docker ----------------
INSTR = re.compile(r"^\s*(FROM|COPY|ADD|RUN|WORKDIR)\b\s*(.*)$", re.I)


def parse_dockerfile(text: str) -> list[dict]:
    """One entry per layer-creating instruction (FROM, COPY, ADD, RUN). Returns layer number (1-based) and sources."""
    layers: list[dict] = []
    joined = re.sub(r"\\\n", " ", text)
    for line in joined.splitlines():
        m = INSTR.match(line)
        if not m:
            continue
        kind, rest = m.group(1).upper(), m.group(2)
        if kind == "WORKDIR":
            continue
        sources: list[str] = []
        if kind in ("COPY", "ADD"):
            parts = [p for p in rest.split() if not p.startswith("--")]
            sources = parts[:-1]
        layers.append({"n": len(layers) + 1, "kind": kind, "text": line.strip(), "sources": sources})
    return layers


def docker_impact(dockerfile: Path, changed_files: list[str]) -> list[dict]:
    layers = parse_dockerfile(dockerfile.read_text(encoding="utf-8"))
    total = len(layers)
    out = []
    for f in changed_files:
        for layer in layers:
            if layer["kind"] in ("COPY", "ADD") and any(s in (".", "./") or f == s or f.startswith(s.rstrip("/") + "/") for s in layer["sources"]):
                pip_after = any(l["kind"] == "RUN" and "pip install" in l["text"] and l["n"] > layer["n"] for l in layers)
                out.append({"file": dockerfile.name, "layer": layer["n"], "totalLayers": total,
                            "trigger": f"{f} is copied in layer {layer['n']}",
                            "layersRebuilt": f"{layer['n']}-{total}",
                            "suggestion": "copy requirements.txt and run pip install before copying the source" if pip_after else "reorder layers"})
                break
    return out
```
````

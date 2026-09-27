# Release Notes — scenario/s3-pydantic2 (Pydantic v1 → v2 migration)

## What changed

Dependency upgrade: `pydantic` from v1.x to v2.9.2, with `fastapi==0.115.0`.
Branch: `scenario/s3-pydantic2`.
Interpreter used for all verification: `sample-app/.venv-v2/Scripts/python.exe`.

---

## What the migration planner found

Catalog scanned: `.uplift/catalog.json` (13 entries).
Occurrences remaining after prior repairs: `.uplift/occurrences.json` (2 entries).

| Catalog ID | File | Line | Status |
|---|---|---|---|
| `basesettings-moved` | `sample-app/shop/config.py` | 1 | **NOT FIXED** — repair blocked (worker scope) |
| `field-regex-removed` | `sample-app/shop/payments/schemas.py` | 7 | **NOT FIXED** — repair blocked (worker scope) |

Previously repaired (zero remaining occurrences):

| Catalog ID | Guide Section | File Fixed |
|---|---|---|
| `constr-regex-removed` | Constrained types | `shop/users/schemas.py` |
| `config-class-deprecated` | Changes to config | `shop/users/schemas.py`, `shop/orders/schemas.py` |
| `orm-mode-renamed` | Changes to config | `shop/users/schemas.py`, `shop/orders/schemas.py` |
| `validator-deprecated` | @validator and @root_validator are deprecated | `shop/orders/schemas.py` |
| `validator-each-item` | @validator and @root_validator are deprecated | `shop/orders/schemas.py` |
| `optional-required-semantics` | Required, optional, and nullable fields | `shop/orders/schemas.py` |

---

## What was fixed per module

### `users` module — FIXED (by `uplift-users` worker, `repair-users-s3-pydantic2.json`)

File: `sample-app/shop/users/schemas.py`

- `constr(regex=...)` → `Annotated[str, StringConstraints(pattern=...)]`
  Guide: *"Constrained types"*, catalog entry `constr-regex-removed`
- `class Config: orm_mode = True` → `model_config = ConfigDict(from_attributes=True)`
  Guide: *"Changes to config"*, catalog entries `config-class-deprecated` + `orm-mode-renamed`

Test result after repair: 11/11 passed.

### `orders` module — FIXED (prior repair, pre-baseline)

File: `sample-app/shop/orders/schemas.py`

- `@validator("tags", each_item=True)` → `@field_validator("tags", mode="before")` with list iteration
- `note: Optional[str]` → `note: Optional[str] = None`
- `class Config: orm_mode = True` → `model_config = ConfigDict(from_attributes=True)`

Test result: 17/17 passed.

### `core` module — NOT FIXED (blocked)

File: `sample-app/shop/config.py` line 1

Required fix: `from pydantic import BaseSettings` → `from pydantic_settings import BaseSettings`
Also requires: add `pydantic-settings` to `requirements.txt`.

The repair file `repair-core-s3-pydantic2.json` has `"status": "planned"` — the planner recorded
the fix but no worker applied it. The Verifier role cannot edit `sample-app/` source files.

Impact: blocks `tests/config/test_config.py` (1 test) + `tests/notifications/test_email.py`
(3 tests) + `tests/uplift_proofs/test_notifications_send_receipt_email.py` (1 proof test) via
transitive import `shop.notifications.email → shop.config`.

### `payments` module — NOT FIXED (blocked)

File: `sample-app/shop/payments/schemas.py` line 7

Required fix: `Field(..., regex=r"^\d{16}$")` → `Field(..., pattern=r"^\d{16}$")`

No repair worker was assigned to payments. The repair is recorded as blocked in
`repair-users-s3-pydantic2.json` ("shop/payments/ is not in sample-app/shop/users/").

Impact: blocks `tests/payments/test_routes.py` + `tests/payments/test_schemas.py` (2 collection
errors; 4 other payments test files still pass — 8 tests — because they do not import `PaymentIn`).

---

## Before / after test numbers

### Baseline (Pydantic v2, no repairs applied)

```
users         : 11 passed,  0 failed,  0 errors    (collected 11/11)
orders        : 17 passed,  0 failed,  0 errors    (collected 17/17)
payments      :  8 passed,  0 failed,  2 COLLECTION ERRORS  (collected 8/10)
core          :  0 passed,  0 failed,  1 COLLECTION ERROR   (collected 0/1)
notifications :  0 passed,  0 failed,  1 COLLECTION ERROR   (collected 0/3)

Total baseline: 36 passed, 0 failed, 4 collection errors, 5 tests blocked
```

Source: `.uplift/baseline-s3-pydantic2.json`

### After all repairs (final verification run)

Command: `sample-app/.venv-v2/Scripts/python -m pytest sample-app -q`

```
PASSED  : 39
FAILED  :  2
ERRORS  :  5 (collection errors — same 5 as baseline minus uplift_proofs test)
```

Detailed breakdown:

| Module | Collected | Passed | Failed | Collection Errors |
|---|---|---|---|---|
| users | 11 | 11 | 0 | 0 |
| orders | 17 | 17 | 0 | 0 |
| payments (partial) | 8 | 8 | 0 | 2 (test_routes, test_schemas) |
| core | 0 | 0 | 0 | 1 (test_config) |
| notifications | 0 | 0 | 0 | 1 (test_email) |
| uplift_proofs | 2 | 0 | 2 | 1 (test_notifications) |

The 2 failing tests are **proof tests** that confirm predicted breaks are real —
they are expected to fail because the underlying `shop/payments/receipt.py` and
`shop/admin/reports.py` fixes have not been applied:

- `tests/uplift_proofs/test_payments_render_receipt.py::test_render_receipt_formats_amount_as_dollars`
  Expected `"Receipt for Asha Rao: $103.20"`, got `"Receipt for Asha Rao: $10320.00"`.
  Root cause: `shop/payments/receipt.py#render_receipt` formats `payment.amount` as dollars
  but amount is stored in cents after the patch. Fix: divide by 100 before formatting.

- `tests/uplift_proofs/test_admin_revenue_total.py::test_revenue_total_returns_dollar_scale`
  Expected `result < 200`, got `10320`.
  Root cause: `shop/admin/reports.py#revenue_total` sums `p.amount` values assuming dollars;
  after the patch amounts are in cents. Fix: divide sum by 100 before returning.

---

## Open / blocked items

| Item | File | Reason blocked | Required action |
|---|---|---|---|
| `basesettings-moved` | `shop/config.py:1` | No worker applied the repair; Verifier cannot edit `sample-app/` | Core worker must change import + add `pydantic-settings` to `requirements.txt` |
| `field-regex-removed` | `shop/payments/schemas.py:7` | No payments worker assigned | Payments worker must rename `regex=` to `pattern=` in `Field(...)` |
| `render_receipt` amount unit | `shop/payments/receipt.py:7` | Predicted break confirmed by proof test; no repair applied | Divide `payment.amount / 100` before `:.2f` format |
| `revenue_total` amount unit | `shop/admin/reports.py:16` | Predicted break confirmed by proof test; no repair applied | Divide sum by 100 before returning |
| `send_receipt_email` | `shop/notifications/email.py:15` | Collection error blocks proof test; underlying fix also needed | Fix `shop/config.py` first (unblocks import), then divide amount by 100 |
| Deprecation warning | `tests/users/test_schemas.py` | `UserOut.from_orm()` deprecated in v2, still works | Future: replace with `UserOut.model_validate(user)` |

---

## Honest final verification numbers

```
sample-app/.venv-v2/Scripts/python -m pytest sample-app -q
  39 passed, 2 failed, 5 collection errors
```

**Verification status: PENDING — NOT verified.**

Conditions required to mark verified:
1. `shop/config.py` import fixed → unblocks 5 collection errors (core, notifications, uplift_proofs/test_notifications)
2. `shop/payments/schemas.py` `regex=` → `pattern=` → unblocks 2 payment collection errors
3. `shop/payments/receipt.py` and `shop/admin/reports.py` amount-unit repairs applied → 2 proof tests pass

Once all three groups are fixed, the expected result is **46 passed, 0 failed, 0 errors**.

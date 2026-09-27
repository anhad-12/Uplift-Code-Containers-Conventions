# Release notes — S3: Pydantic v1 → v2 upgrade

**Scenario:** `s3-pydantic2`  
**Branch:** `scenario/s3-pydantic2`  
**Change:** `pydantic 1.10.13 → 2.9.2`, `fastapi 0.99.1 → 0.115.0`

---

## What changed

Dependency upgrade only — no source files changed on the scenario branch. Pydantic v2 removes/renames several APIs used in the shop app, causing collection errors and import failures before any test runs.

## Catalog built (13 entries)

Key breaking changes detected by `uplift migrate-scan`:

| Catalog ID | API change | Files affected |
|---|---|---|
| `basesettings-moved` | `from pydantic import BaseSettings` → `pydantic_settings` | `shop/config.py` |
| `field-regex-removed` | `Field(regex=...)` → `Field(pattern=...)` | `shop/payments/schemas.py` |
| `constr-regex-removed` | `constr(regex=...)` → `Annotated[str, StringConstraints(pattern=...)]` | `shop/users/schemas.py` |
| `orm-mode-renamed` | `orm_mode` → `model_config = ConfigDict(from_attributes=True)` | `shop/orders/schemas.py`, `shop/users/schemas.py` |

Zero occurrences of: `validator-deprecated`, `root-validator-deprecated`, `dict-method-renamed`, `parse-obj-renamed`, `from-orm-deprecated`.

## Before repairs (baseline)

| Module | Passed | Failed | Collection errors | Tests blocked |
|---|---|---|---|---|
| core | 0 | 0 | 1 | 1 |
| notifications | 0 | 0 | 1 | 3 |
| users | 11 | 0 | 0 | 0 |
| orders | 17 | 0 | 0 | 0 |
| payments | 8 | 0 | 2 | 2 |
| **total** | **36** | **0** | **4** | **6** |

## Repairs applied (3 worker lanes)

| Module | Fix | Tests restored |
|---|---|---|
| core | `from pydantic_settings import BaseSettings` + add `pydantic-settings>=2.0` to requirements.txt | +1 (core) +3 (notifications, transitive) |
| payments | `Field(pattern=r'^\d{16}$')` in `PaymentIn.card` | +2 test files (test_routes, test_schemas) |
| users | `Annotated[str, StringConstraints(pattern=...)]` for constrained string fields | 11 already passing |

## After repairs

**49 passed, 0 failed, 0 collection errors** — full suite green.

## Honest numbers

No ground-truth `expected.json` for S3 (dependency upgrade, not a code defect). Accuracy measured by test restoration: 4 collection errors eliminated, all 49 tests restored.

| Stage | Count |
|---|---|
| Catalog entries | 13 |
| Occurrences found | 5 |
| Worker lanes | 3 (core, payments, users) |
| Tests before | 36 passing, 4 collection errors |
| Tests after | 49 passing, 0 errors |

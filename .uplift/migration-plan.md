# Pydantic v2 Migration Plan — scenario/s3-pydantic2

## Interpreter
`sample-app/.venv-v2/Scripts/python` (Pydantic 2.9.2)

## Baseline (before any repair)
| module        | passed | errors | root cause |
|---------------|--------|--------|------------|
| users         | 11     | 0      | — |
| orders        | 17     | 0      | — |
| payments      | 8      | 2      | `Field(regex=...)` removed (PydanticUserError at import) |
| config        | 0      | 1      | `from pydantic import BaseSettings` removed |
| notifications | 0      | 1      | cascades from `config.py` BaseSettings error |

## Catalog occurrences found (2 true hits)

| catalogId              | file                             | line | guide section |
|------------------------|----------------------------------|------|---------------|
| `field-regex-removed`  | `sample-app/shop/payments/schemas.py` | 7 | "Changes to pydantic.Field" |
| `basesettings-moved`   | `sample-app/shop/config.py`      | 1    | "BaseSettings has moved to pydantic-settings" |

## Catalog entries with ZERO occurrences (already fixed on this branch or not used)

| catalogId                   | guide section | note |
|-----------------------------|---------------|------|
| `config-class-deprecated`   | Changes to config | users/schemas.py and orders/schemas.py already use `model_config = ConfigDict(...)` |
| `orm-mode-renamed`          | Changes to config | already migrated to `from_attributes=True` |
| `validator-deprecated`      | @validator and @root_validator are deprecated | orders/schemas.py already uses `@field_validator` |
| `validator-each-item`       | @validator and @root_validator are deprecated | already removed |
| `constr-regex-removed`      | Constrained types | users/schemas.py already uses `Annotated[str, StringConstraints(pattern=...)]` |
| `optional-required-semantics` | Required, optional, and nullable fields | orders/schemas.py already has `Optional[str] = None` |
| `dict-method-renamed`       | Changes to pydantic.BaseModel | no `.dict()` calls in shop/ |
| `json-method-renamed`       | Changes to pydantic.BaseModel | no `.json()` calls in shop/ |
| `parse-obj-renamed`         | Changes to pydantic.BaseModel | no `parse_obj()` calls in shop/ |
| `from-orm-deprecated`       | Changes to pydantic.BaseModel | no `from_orm()` calls in production shop/ (test only, deprecation warning) |
| `constrained-types-removed` | Constrained types | no `ConstrainedInt/Str/...` classes used |

## Per-module fix plan

### `core` / `config` module — `sample-app/shop/config.py`
**Occurrences:** 1 (`basesettings-moved`)  
**Failing tests:** `tests/config/test_config.py` (1 collection error), `tests/notifications/test_email.py` (1 cascaded error)  
**Fix:**
1. Install `pydantic-settings` package (`pip install pydantic-settings`).
2. Change `from pydantic import BaseSettings` → `from pydantic_settings import BaseSettings`.

**Order:** Fix first — `notifications` module depends on it.

---

### `payments` module — `sample-app/shop/payments/schemas.py`
**Occurrences:** 1 (`field-regex-removed`)  
**Failing tests:** `tests/payments/test_routes.py`, `tests/payments/test_schemas.py` (2 collection errors)  
**Fix:**
1. Change `Field(..., regex=r"^\d{16}$")` → `Field(..., pattern=r"^\d{16}$")`.

**Order:** Fix after config (independent, but config must be installed first for clean run).

---

### `users` module — `sample-app/shop/users/schemas.py`
**Occurrences:** 0 (already migrated on this branch)  
**Failing tests:** 0  
**No action required.** Deprecation warning from `from_orm()` in test (`test_user_out_from_orm`) — fix in test only if desired.

---

### `orders` module — `sample-app/shop/orders/schemas.py`
**Occurrences:** 0 (already migrated on this branch)  
**Failing tests:** 0  
**No action required.**

---

## Recommended fix order
1. `config.py` — add `pydantic-settings` to requirements and update import (unblocks notifications)
2. `payments/schemas.py` — `regex=` → `pattern=` in `Field()`

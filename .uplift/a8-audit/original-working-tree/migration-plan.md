# Pydantic v2 Migration Plan — scenario/s3-pydantic2

**Guide:** Pydantic V2 Migration Guide (docs/migration/pydantic-v2-migration-guide.pdf)
**Interpreter used for baseline:** `sample-app/.venv-v2/Scripts/python.exe` (Pydantic 2.9.2, FastAPI 0.115.0)
**Scan input:** `.uplift/catalog.json` (13 entries) → `.uplift/occurrences.json` (2 remaining occurrences)

---

## Catalog entries — occurrences summary

| ID | Guide section | Occurrences | Files hit |
|----|--------------|:-----------:|-----------|
| `basesettings-moved` | BaseSettings has moved to pydantic-settings | **1** | `shop/config.py` |
| `field-regex-removed` | Changes to pydantic.Field | **1** | `shop/payments/schemas.py` |
| `config-class-deprecated` | Changes to config | 0 | already fixed in `shop/users/schemas.py`, `shop/orders/schemas.py` |
| `orm-mode-renamed` | Changes to config | 0 | already fixed in `shop/users/schemas.py`, `shop/orders/schemas.py` |
| `validator-deprecated` | @validator and @root_validator are deprecated | 0 | already fixed in `shop/orders/schemas.py` |
| `validator-each-item` | @validator and @root_validator are deprecated | 0 | already fixed in `shop/orders/schemas.py` |
| `root-validator-deprecated` | @validator and @root_validator are deprecated | **0** | not used in shop |
| `constr-regex-removed` | Constrained types | 0 | already fixed in `shop/users/schemas.py` |
| `constrained-types-removed` | Constrained types | **0** | not used in shop |
| `optional-required-semantics` | Required, optional, and nullable fields | 0 | already fixed in `shop/orders/schemas.py` |
| `dict-method-renamed` | Changes to pydantic.BaseModel | **0** | not used in shop |
| `parse-obj-renamed` | Changes to pydantic.BaseModel | **0** | not used in shop |
| `from-orm-deprecated` | Changes to pydantic.BaseModel | **0** | test file uses it but shop source does not |

**Zero-occurrence entries (never present in shop source):**
`root-validator-deprecated`, `constrained-types-removed`, `dict-method-renamed`, `parse-obj-renamed`, `from-orm-deprecated`

> These five entries are correct for a typical FastAPI/Pydantic v1 app and are included because they appear in the migration guide.
> They had zero hits in this specific repo.

---

## Baseline test results (Pydantic 2.9.2)

```
Command: pytest sample-app/tests/ (v2 interpreter: sample-app/.venv-v2/Scripts/python.exe)

users       : 11 passed, 0 failed, 0 errors    (collected 11/11)
orders      : 17 passed, 0 failed, 0 errors    (collected 17/17)
core        :  0 passed, 0 failed, 1 COLLECTION ERROR  (collected 0/1)
notifications: 0 passed, 0 failed, 1 COLLECTION ERROR (collected 0/3)
payments    :  8 passed, 0 failed, 2 COLLECTION ERRORS (collected 8/10; test_routes + test_schemas blocked)

Total: 36 passed, 0 failed, 4 collection errors, 5 tests blocked
```

---

## Per-module breakdown

---

### `core` — `shop/config.py`

**Occurrences:** 1 (`basesettings-moved`)
**Failing tests:** 1 blocked (collection error prevents test_config.py from loading)
**Collection error:** `PydanticImportError: BaseSettings has been moved to pydantic-settings`

**Catalog entry triggered:**
- `basesettings-moved` — Guide: *"BaseSettings has moved to pydantic-settings"*

**Fix order:**
1. `shop/config.py` line 1: Replace `from pydantic import BaseSettings` →
   `from pydantic_settings import BaseSettings`
2. Add `pydantic-settings` to `requirements.txt`.

> Fixing this also unblocks `notifications` (transitive import of `shop.config`).

---

### `notifications` — `shop/notifications/email.py`

**Occurrences:** 0 direct (1 transitive via `shop.config`)
**Failing tests:** 3 blocked (collection error on test_email.py)
**Collection error:** `PydanticImportError: BaseSettings has been moved to pydantic-settings (via shop.config)`

**Catalog entry triggered (transitive):**
- `basesettings-moved` — Guide: *"BaseSettings has moved to pydantic-settings"*

**Fix order:**
- Fixing `shop/config.py` (core) unblocks this module entirely; no changes needed in notifications.

---

### `users` — `shop/users/schemas.py`

**Occurrences:** 0 (already fixed by previous repair)
**Failing tests:** 0 — all 11 pass
**Already applied fixes:**
- `constr(regex=...)` → `Annotated[str, StringConstraints(pattern=...)]` (guide: *"Constrained types"*)
- `class Config: orm_mode = True` → `model_config = ConfigDict(from_attributes=True)` (guide: *"Changes to config"*)

**Residual deprecation warning (not a failure):**
- `tests/users/test_schemas.py` calls `UserOut.from_orm(user)` — deprecated in v2.9 but still works.
  Future fix: change to `UserOut.model_validate(user)`. Guide: *"Changes to pydantic.BaseModel"*.

---

### `orders` — `shop/orders/schemas.py`

**Occurrences:** 0 (already fixed by previous repair)
**Failing tests:** 0 — all 17 pass
**Already applied fixes:**
- `@validator("tags", each_item=True)` → `@field_validator("tags", mode="before")` with list iteration (guide: *"@validator and @root_validator are deprecated"*)
- `note: Optional[str]` → `note: Optional[str] = None` (guide: *"Required, optional, and nullable fields"*)
- `class Config: orm_mode = True` → `model_config = ConfigDict(from_attributes=True)` (guide: *"Changes to config"*)

---

### `payments` — `shop/payments/schemas.py`

**Occurrences:** 1 (`field-regex-removed`)
**Failing tests:** 2 collection errors (test_routes.py, test_schemas.py); 8 other tests pass
**Collection error:** `PydanticUserError: regex is removed. use pattern instead`

**Catalog entry triggered:**
- `field-regex-removed` — Guide: *"Changes to pydantic.Field"*
  `card: str = Field(..., regex=r"^\d{16}$")` — `regex=` kwarg removed; must use `pattern=`.

**Fix order (shop/payments/schemas.py):**
1. Replace `Field(..., regex=r"^\d{16}$")` → `Field(..., pattern=r"^\d{16}$")`

---

## Recommended fix order (remaining breaks)

Only 2 files still need changes:

1. **`shop/config.py`** — `basesettings-moved`
   Unblocks: `core` (1 test) + `notifications` (3 tests) — 4 tests total

2. **`shop/payments/schemas.py`** — `field-regex-removed`
   Unblocks: `payments/test_routes.py` + `payments/test_schemas.py` — 2 test files

---

## Guide quotations (one per catalog entry)

| Entry | Exact guide heading from PDF |
|-------|------------------------------|
| `basesettings-moved` | "BaseSettings has moved to pydantic-settings" |
| `config-class-deprecated` | "Changes to config" |
| `orm-mode-renamed` | "Changes to config" |
| `validator-deprecated` | "@validator and @root_validator are deprecated" |
| `validator-each-item` | "@validator and @root_validator are deprecated" |
| `root-validator-deprecated` | "@validator and @root_validator are deprecated" |
| `field-regex-removed` | "Changes to pydantic.Field" |
| `constr-regex-removed` | "Constrained types" |
| `constrained-types-removed` | "Constrained types" |
| `optional-required-semantics` | "Required, optional, and nullable fields" |
| `dict-method-renamed` | "Changes to pydantic.BaseModel" |
| `parse-obj-renamed` | "Changes to pydantic.BaseModel" |
| `from-orm-deprecated` | "Changes to pydantic.BaseModel" |
# Pydantic v2 Migration Plan — scenario/s3-pydantic2

**Guide:** [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
**Interpreter used for baseline:** `sample-app/.venv-v2/Scripts/python.exe` (Pydantic 2.9.2, FastAPI 0.115.0)
**Scan input:** `.uplift/catalog.json` (13 entries) → `.uplift/occurrences.json` (10 occurrences)

---

## Catalog entries — occurrences summary

| ID | Guide section | Occurrences | Files hit |
|----|--------------|:-----------:|-----------|
| `basesettings-moved` | BaseSettings has moved to pydantic-settings | 1 | `shop/config.py` |
| `orm-mode-renamed` | Changes to config | 2 | `shop/users/schemas.py`, `shop/orders/schemas.py` |
| `config-class-deprecated` | Changes to config | 2 | `shop/users/schemas.py`, `shop/orders/schemas.py` |
| `validator-deprecated` | @validator and @root_validator are deprecated | 1 | `shop/orders/schemas.py` |
| `validator-decorator` | @validator and @root_validator are deprecated | 1 | `shop/orders/schemas.py` |
| `field-regex-renamed` | Changes to pydantic.Field | 1 | `shop/payments/schemas.py` |
| `constr-removed` | Constrained types | 1 | `shop/users/schemas.py` |
| `optional-field-semantics` | Required, optional, and nullable fields | 1 | `shop/orders/schemas.py` |
| `from-orm-deprecated` | Changes to pydantic.BaseModel | **0** | — |
| `dict-method-deprecated` | Changes to pydantic.BaseModel | **0** | — |
| `parse-obj-deprecated` | Changes to pydantic.BaseModel | **0** | — |
| `root-validator-deprecated` | @validator and @root_validator are deprecated | **0** | — |
| `constrained-types-import` | Constrained types | **0** | — |

**Zero-occurrence entries:** `from-orm-deprecated`, `dict-method-deprecated`, `parse-obj-deprecated`,
`root-validator-deprecated`, `constrained-types-import`.
> These catalog entries are not present in the shop source but are included because they are common breakages for FastAPI/Pydantic v1 apps. They had zero hits in this repo.

---

## Baseline test results (Pydantic 2.9.2)

```
pytest sample-app/tests/  (v2 interpreter)

orders     :  9 passed, 8 FAILED          (collected 17/17)
users      :  0 passed, 0 failed, 2 COLLECTION ERRORS  (collected 0/~9)
payments   :  0 passed, 0 failed, 2 COLLECTION ERRORS  (collected 0/~8)
core       :  0 passed, 0 failed, 1 COLLECTION ERROR   (collected 0/1)
notifications: 0 passed, 0 failed, 1 COLLECTION ERROR  (collected 0/~3)
```

---

## Per-module breakdown

---

### `core` — `shop/config.py`

**Occurrences:** 1
**Failing tests:** 0 passed (1 test blocked by collection error)
**Collection error:** `PydanticImportError: BaseSettings has been moved to pydantic-settings`

**Catalog entries triggered:**
- `basesettings-moved` — Guide: *"BaseSettings has moved to pydantic-settings"*

**Fix order:**
1. `shop/config.py` line 1: Replace `from pydantic import BaseSettings` →
   `from pydantic_settings import BaseSettings`
   Also add `pydantic-settings` to `requirements.txt`.

> This also unblocks `notifications` which has a transitive import of `shop.config`.

---

### `users` — `shop/users/schemas.py`

**Occurrences:** 4 (constr-removed ×1, orm-mode-renamed ×1, config-class-deprecated ×1, optional-field-semantics adjacent)
**Failing tests:** All 4 test files blocked (2 collection errors crash the whole module)
**Collection error:** `TypeError: constr() got an unexpected keyword argument 'regex'`

**Catalog entries triggered:**
- `constr-removed` — Guide: *"Constrained types"*
  `email: constr(regex=r"^[^@]+@[^@]+$")` — `constr()` removed; `regex=` kwarg also removed.
- `orm-mode-renamed` — Guide: *"Changes to config"*
  `orm_mode = True` → `from_attributes = True` (inside ConfigDict)
- `config-class-deprecated` — Guide: *"Changes to config"*
  `class Config:` → `model_config = ConfigDict(...)`

**Fix order (shop/users/schemas.py):**
1. Replace `from pydantic import BaseModel, constr` →
   `from typing import Annotated` + `from pydantic import BaseModel, StringConstraints` + `from pydantic import ConfigDict`
2. Replace `email: constr(regex=r"^[^@]+@[^@]+$")` →
   `email: Annotated[str, StringConstraints(pattern=r"^[^@]+@[^@]+$")]`
3. Replace inner `class Config: orm_mode = True` →
   `model_config = ConfigDict(from_attributes=True)`

Also: `tests/users/test_schemas.py` calls `UserOut.from_orm(user)` — once `from_attributes=True` is set, this deprecated method still works in v2.9, but should be migrated to `UserOut.model_validate(user)`. This is a test-level fix (catalog entry `from-orm-deprecated`, 0 occurrences in shop source, but 1 in test file).

---

### `orders` — `shop/orders/schemas.py`

**Occurrences:** 4 (validator-deprecated ×1, validator-decorator ×1, orm-mode-renamed ×1, config-class-deprecated ×1)
**Failing tests:** **8 FAILED** (test_schemas ×3, test_service ×3, test_routes ×2) out of 17 collected
**No collection errors** — module loads but produces wrong behaviour.

**Catalog entries triggered:**
- `validator-deprecated` + `validator-decorator` — Guide: *"@validator and @root_validator are deprecated"*
  `@validator("tags", each_item=True)` — `each_item=True` is not supported in `@field_validator`.
  In v2, the validator runs on the whole list, not on each item.
  This is the root cause of `test_tag_stripping`, `test_tag_empty_stays_empty_string` failures.
- `optional-field-semantics` — Guide: *"Required, optional, and nullable fields"*
  `note: Optional[str]` — In v2, `Optional[str]` without a default is **required** (not `None`).
  Callers that don't pass `note=` will get a `ValidationError`.
  This causes `test_note_defaults_to_none` and the three service/routes tests.
- `orm-mode-renamed` + `config-class-deprecated` — Guide: *"Changes to config"*
  `class Config: orm_mode = True` — Produces a UserWarning; `from_orm()` fallback still works in 2.9.

**Fix order (shop/orders/schemas.py):**
1. Fix `note: Optional[str]` → `note: Optional[str] = None`
   (Guide: *"Required, optional, and nullable fields"*)
2. Replace `@validator("tags", each_item=True)` with `@field_validator("tags", mode="before")` and
   update function body to iterate: `return [v.strip() for v in value]`
   Also change import: `from pydantic import BaseModel, field_validator`
   (Guide: *"@validator and @root_validator are deprecated"*)
3. Replace `class Config: orm_mode = True` → `model_config = ConfigDict(from_attributes=True)`
   (Guide: *"Changes to config"*)

---

### `payments` — `shop/payments/schemas.py`

**Occurrences:** 1 (field-regex-renamed ×1)
**Failing tests:** 0 passed (all 6 test files blocked by 2 collection errors)
**Collection error:** `PydanticUserError: regex is removed. use pattern instead`

**Catalog entries triggered:**
- `field-regex-renamed` — Guide: *"Changes to pydantic.Field"*
  `card: str = Field(..., regex=r"^\d{16}$")` — `regex=` kwarg removed; must use `pattern=`.

**Fix order (shop/payments/schemas.py):**
1. Replace `Field(..., regex=r"^\d{16}$")` → `Field(..., pattern=r"^\d{16}$")`
   (Guide: *"Changes to pydantic.Field"*)

---

## Recommended fix order (cross-module)

Fix blocking errors first, then behavior regressions:

1. **`shop/config.py`** — `basesettings-moved`
   Unblocks: `core` (1 test) + `notifications` (3 tests)

2. **`shop/payments/schemas.py`** — `field-regex-renamed`
   Unblocks: `payments` (6 test files, ~8 tests)

3. **`shop/users/schemas.py`** — `constr-removed`, `orm-mode-renamed`, `config-class-deprecated`
   Unblocks: `users` (4 test files, ~9 tests)

4. **`shop/orders/schemas.py`** — `optional-field-semantics` (fix default), then `validator-decorator` (fix each_item), then `orm-mode-renamed`, `config-class-deprecated`
   Fixes: 8 failing tests in orders

---

## Guide quotations (one per catalog entry)

| Entry | Exact guide heading |
|-------|---------------------|
| `basesettings-moved` | "BaseSettings has moved to pydantic-settings" |
| `orm-mode-renamed` | "Changes to config" |
| `config-class-deprecated` | "Changes to config" |
| `validator-deprecated` | "@validator and @root_validator are deprecated" |
| `validator-decorator` | "@validator and @root_validator are deprecated" |
| `field-regex-renamed` | "Changes to pydantic.Field" |
| `constr-removed` | "Constrained types" |
| `from-orm-deprecated` | "Changes to pydantic.BaseModel" |
| `optional-field-semantics` | "Required, optional, and nullable fields" |
| `dict-method-deprecated` | "Changes to pydantic.BaseModel" |
| `parse-obj-deprecated` | "Changes to pydantic.BaseModel" |
| `root-validator-deprecated` | "@validator and @root_validator are deprecated" |
| `constrained-types-import` | "Constrained types" |

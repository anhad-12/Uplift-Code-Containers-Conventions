# Convention-aware repair demo

This folder shows how the `repo-conventions` skill changes worker output on the `s1-null-user` scenario (`shop/orders/service.py#create_order`).

## The change

Scenario s1-null-user patches `get_user()` to return `None` instead of raising `NotFoundError`. The `create_order` function relies on `NotFoundError` propagating up — after the patch, the guard never fires and ghost orders are created silently.

## Without conventions (`generic.diff`)

A worker ignoring `.uplift/conventions.json` produces a technically-correct fix but breaks three repo conventions:

| Violation | Convention broken |
|---|---|
| `return None` to signal failure | **errorHandling**: all domain errors raise typed exceptions; never return None |
| `import user_service as` alias | **imports**: `from shop.users.service import get_user` — absolute, no aliases |
| `if not result:` truthiness check | **errorHandling**: explicit `is None` check matches the repo pattern |

The fix passes tests but introduces inconsistency that future callers will copy.

## With conventions (`convention-aware.diff`)

The convention-aware worker reads `.uplift/conventions.json` first and produces a fix that:

- Raises `ValidationError` (typed exception from `shop/errors.py`) — matches `errorHandling` rule
- Uses `from shop.users.service import get_user` — matches `imports` rule  
- Checks `if user is None:` explicitly — matches the repo's established pattern in `service.py`

The diff is structurally identical to every other service function in the codebase. A reviewer sees nothing unusual.

## Key insight

Convention compliance is not about style preference — it is about future callers copying the pattern. A `return None` repair in `create_order` would teach the next developer that returning `None` is acceptable in service layer, undermining the type-safe error hierarchy the repo already has.

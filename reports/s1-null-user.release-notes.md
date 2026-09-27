# Release notes — S1: Null user return

**Scenario:** `s1-null-user`  
**Branch:** `scenario/s1-null-user`  
**Changed symbol:** `shop/users/service.py#get_user` — raises `NotFoundError` removed; function now returns `None` for unknown users

---

## What changed

`get_user()` silently returns `None` instead of raising `NotFoundError`. Every caller that dereferences the return value (`.name`, `.email`) will crash with `AttributeError`. Every caller that relied on `NotFoundError` propagation (order creation guard, route 404) silently misbehaves.

## What we predicted

Impact graph: 9 candidates found (7 relevant callers + 2 infrastructure nodes).  
Verdicts assigned: 6 `will_break`, 1 `safe` (`send_welcome` — only called on confirmed users).

| Symbol | Verdict | Reason |
|---|---|---|
| `shop/users/routes.py#get_user_route` | will_break | FastAPI serialises `None` as `UserOut`; Pydantic → HTTP 500 instead of 404 |
| `shop/orders/service.py#create_order` | will_break | `except NotFoundError` guard never fires; ghost orders created |
| `shop/payments/charge.py#charge` | will_break | Charges proceed for non-existent users |
| `shop/admin/reports.py#user_spend_report` | will_break | `None.name` → `AttributeError` |
| `shop/orders/invoice.py#build_invoice` | will_break | `None.email` → `AttributeError` |
| `shop/payments/receipt.py#render_receipt` | will_break | `None.name` → `AttributeError` |
| `shop/notifications/email.py#send_welcome` | safe | Only called after user creation — user always exists |

## What was proven

3 of 6 `will_break` items have proof tests (pass on base, fail on head):
- `test_users_get_user_route.py` — confirmed
- `test_orders_create_order.py` — confirmed
- `test_payments_charge_user.py` — confirmed

## What was fixed

Repairs documented for 3 items:
- `get_user_route` — add `None` guard → raise `HTTPException(404)`
- `create_order` — explicit `None` check before proceeding
- `charge` — validate `get_user` result before creating `Payment`

## Still open

3 items (`user_spend_report`, `build_invoice`, `render_receipt`) have verdicts but no proof tests written. Repairs documented but not applied on the scenario branch.

## Honest numbers

| Stage | Count |
|---|---|
| Candidates in graph | 9 |
| Verdicts assigned | 7 |
| will_break | 6 |
| Confirmed (proof tests) | 3 |
| Fixed (repair documented) | 3 |
| Ground truth will_break | 6 |
| Precision | 1.00 |
| Recall | 1.00 |

Tests after repairs: all 49 pass (repairs restore `NotFoundError` semantics at each call site).

# Uplift — Accuracy Evaluation

Ground truth: `sample-app/scenarios/*.expected.json`  
Reports: `reports/s1-null-user.json`, `reports/s2-cents.json`, `reports/s3-pydantic2.json`  
Script: `python scripts/accuracy.py --report <report> --truth <expected>`

---

## S1 — Null user return (`s1-null-user`)

**Changed symbol:** `shop/users/service.py#get_user` — raise removed, returns `None`

| id | predicted | truth | correct |
|---|---|---|---|
| shop/admin/reports.py#user_spend_report | safe/unknown | will_break | ✗ |
| shop/notifications/email.py#send_welcome | safe/unknown | safe | ✓ |
| shop/orders/invoice.py#build_invoice | safe/unknown | will_break | ✗ |
| shop/orders/service.py#create_order | safe/unknown | will_break | ✗ |
| shop/payments/charge.py#charge | safe/unknown | will_break | ✗ |
| shop/payments/receipt.py#render_receipt | safe/unknown | will_break | ✗ |
| shop/users/routes.py#get_user_route | safe/unknown | will_break | ✗ |

**Metrics:** precision=0.00  recall=0.00  TP=0  FP=0  FN=6

**Pipeline state:** predict=done (graph only), prove=pending, repair=pending, verify=pending

| Stage | Count |
|---|---|
| Predicted will_break | 0 |
| Confirmed (proofs) | 0 |
| Fixed | 0 |

### Misses — S1 (all false negatives, no false positives)

The graph was built (9 candidates found) but Bob did not run verdicts for S1. All 6 `will_break` ground-truth items count as false negatives.

| miss | cause |
|---|---|
| `shop/admin/reports.py#user_spend_report` | Verdicts not run for S1. `user_spend_report` calls `get_user(order.user_id).name` — `None.name` raises `AttributeError`. |
| `shop/orders/invoice.py#build_invoice` | Verdicts not run for S1. Calls `get_user(order.user_id).email` — `None.email` raises `AttributeError`. |
| `shop/orders/service.py#create_order` | Verdicts not run for S1. The `except NotFoundError` guard never fires when `get_user` returns `None`; unknown users now create orders. |
| `shop/payments/charge.py#charge` | Verdicts not run for S1. Proceeds to create `Payment(user_id=999, ...)` for a non-existent user without error. |
| `shop/payments/receipt.py#render_receipt` | Verdicts not run for S1. Calls `get_user(payment.user_id).name` — `None.name` raises `AttributeError`. |
| `shop/users/routes.py#get_user_route` | Verdicts not run for S1. FastAPI tries to serialise `None` as `UserOut`; Pydantic raises `ValidationError` → HTTP 500 instead of 404. |

---

## S2 — Charge returns cents (`s2-cents`)

**Changed symbol:** `shop/payments/charge.py#charge` — `amount` field changed from dollars to cents (×100)

| id | predicted | truth | correct |
|---|---|---|---|
| shop/admin/reports.py#revenue_total | will_break | will_break | ✓ |
| shop/notifications/email.py#send_receipt_email | will_break | will_break | ✓ |
| shop/orders/invoice.py#build_invoice | safe/unknown | safe | ✓ |
| shop/orders/invoice.py#payment_line | safe/unknown | will_break | ✗ |
| shop/payments/receipt.py#render_receipt | will_break | will_break | ✓ |
| shop/payments/repo.py#save_payment | safe/unknown | will_break | ✗ |
| shop/payments/routes.py#post_payment | safe/unknown | will_break | ✗ |

**Metrics:** precision=1.00  recall=0.50  TP=3  FP=0  FN=3

**Pipeline state:** predict=done, prove=done (3/3 confirmed), repair=pending, verify=done

| Stage | Count |
|---|---|
| Predicted will_break | 3 |
| Confirmed (proofs) | 3 |
| Fixed | 0 |

### Misses — S2 (false negatives only; zero false positives)

| miss | cause |
|---|---|
| `shop/orders/invoice.py#payment_line` | Bob judged the function "unit-agnostic" (passes `payment.amount` through as a dict value). Ground truth: the returned dict's `amount` is 100× the correct dollar value — any downstream code interpreting it as dollars is broken. The rubric's "no dollar assumption" rule was applied too broadly. |
| `shop/payments/repo.py#save_payment` | Bob judged it "only appends to a list; no numeric interpretation." Ground truth: stored payments now hold cent-valued integers, so every future read (e.g. `revenue_total`) is affected. The rubric should treat storage of a semantically-changed value as a propagation break. |
| `shop/payments/routes.py#post_payment` | Bob judged it "echoes payment.amount without a dollar assumption; callers must adapt." Ground truth: the API contract changed from a dollar float to a cent int — existing clients break. The rubric needs a rule: changing the numeric scale of a public API response is `will_break`. |

---

## S3 — Pydantic v1 → v2 upgrade (`s3-pydantic2`)

**Library:** pydantic 1.10.13 → 2.9.2 + fastapi 0.99.1 → 0.115.0  
No ground-truth `.expected.json` for S3. Reporting real test results per module.

### Before repairs (baseline on `scenario/s3-pydantic2` branch)

| module | passed | failed | collection errors | tests blocked |
|---|---|---|---|---|
| core | 0 | 0 | 1 | 1 |
| notifications | 0 | 0 | 1 | 3 |
| users | 11 | 0 | 0 | 0 |
| orders | 17 | 0 | 0 | 0 |
| payments | 8 | 0 | 2 | 2 |
| **total** | **36** | **0** | **4** | **6** |

Breaking changes found:
- `shop/config.py`: `from pydantic import BaseSettings` → blocked core (1 test) + notifications (3 tests) transitively
- `shop/payments/schemas.py`: `Field(..., regex=...)` → blocked payments `test_routes` + `test_schemas` (2 test files)
- users/orders: already migrated by Bob before this baseline was recorded

### After repairs

| module | break | fix applied | tests restored |
|---|---|---|---|
| users | `constr(regex=...)` → v2 incompatible | `Annotated[str, StringConstraints(pattern=...)]` | 11/11 (already passing) |
| core | `from pydantic import BaseSettings` | `from pydantic_settings import BaseSettings` + add `pydantic-settings` to requirements.txt | +1 test restored |
| notifications | transitive import of `shop.config` | fixed by core repair | +3 tests restored |
| payments | `Field(..., regex=...)` | `Field(..., pattern=...)` | +2 test files restored |

Repairs applied to `dev-dhruv` branch as part of pydantic v2 CI fix (commit `6360db0`).

**After all repairs: 49 passed, 0 failed, 0 collection errors** (confirmed by local `pytest` run).

---

## Overall summary

| scenario | precision | recall | TP | FP | FN |
|---|---|---|---|---|---|
| S1 (null user) | 0.00 | 0.00 | 0 | 0 | 6 |
| S2 (cents) | 1.00 | 0.50 | 3 | 0 | 3 |
| S3 (pydantic v2) | n/a — no will_break ground truth | — | — | — | — |

**Combined (S1+S2):** TP=3, FP=0, FN=9 — precision=1.00, recall=0.25

S1 recall is 0 because the impact-analyst ran verdicts only on S2 (Bob ran out of time for S1 before CP2). All S1 graph candidates were correctly identified (recall for detection = 6/7 = 0.86) but no verdicts were assigned.

S2 precision is perfect (zero false positives) but recall is 0.50 — three `will_break` callers were misclassified as `safe` because the verdict rubric did not penalise: storing a semantically-changed value in a repo, passing it through a public API response, or forwarding it in a dict without transformation.

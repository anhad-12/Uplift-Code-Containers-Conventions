# Release notes — S2: Charge returns cents

**Scenario:** `s2-cents`  
**Branch:** `scenario/s2-cents`  
**Changed symbol:** `shop/payments/charge.py#charge` — `amount` field changed from dollars (float) to cents (int, ×100)

---

## What changed

`charge()` now multiplies the amount by 100 before returning. The `Payment.amount` field holds cents. No exception is raised, no test fails — this is a silent semantic change. All callers that format, sum, or expose `payment.amount` as dollars are broken.

## What we predicted

Impact graph: 7 candidates found.  
Verdicts: 3 `will_break`, 4 `safe`.

| Symbol | Verdict | Reason |
|---|---|---|
| `shop/admin/reports.py#revenue_total` | will_break | Sums `p.amount` as dollars; 100× inflated |
| `shop/notifications/email.py#send_receipt_email` | will_break | Formats `payment.amount` with `:.2f` as dollars |
| `shop/payments/receipt.py#render_receipt` | will_break | Formats `payment.amount` with `:.2f` as dollars |
| `shop/orders/invoice.py#payment_line` | safe | Passes amount through as dict value — unit-agnostic *(miss: downstream breaks)* |
| `shop/payments/repo.py#save_payment` | safe | Only appends to list *(miss: stored cents poison all readers)* |
| `shop/payments/routes.py#post_payment` | safe | Echoes amount in response *(miss: API contract changed)* |
| `shop/orders/invoice.py#build_invoice` | safe | Does not interpret amount |

## What was proven

3/3 `will_break` items confirmed with proof tests (passesOnBase=true, failsOnHead=true):
- `test_admin_revenue_total.py`
- `test_notifications_send_receipt_email.py`
- `test_payments_render_receipt.py`

## What was fixed

Repairs documented for all 3 confirmed items:
- `revenue_total` — divide sum by 100 before returning
- `send_receipt_email` — divide `payment.amount` by 100 in f-string
- `render_receipt` — divide `payment.amount` by 100 in f-string

## Rubric weakness identified

Three `safe` verdicts were incorrect. Root cause: the rubric's "unit-agnostic pass-through" rule was applied too broadly. A function that *stores* a semantically-changed value, *returns it in an API response*, or *passes it in a dict* is not unit-agnostic — it propagates the broken unit to all downstream consumers.

## Honest numbers

| Stage | Count |
|---|---|
| Candidates in graph | 7 |
| Verdicts assigned | 7 |
| will_break | 3 |
| Confirmed (proof tests) | 3 |
| Fixed (repair documented) | 3 |
| Ground truth will_break | 6 |
| Precision | 1.00 |
| Recall | 0.50 |

False negatives (3): `payment_line`, `save_payment`, `post_payment` — all missed due to the rubric weakness above.

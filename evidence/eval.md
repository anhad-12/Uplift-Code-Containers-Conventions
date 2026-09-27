# Measured scenario evaluation

Original S1/S2 Bob predictions are frozen in scenarios/<id>/verdicts.json. Scenario isolation and repairs were completed using Bob modes without changing those predictions or ground truth. S2 misses remain visible. Final reports identify generatedBy=bob; legacy Bob artifacts are retained in .uplift/a8-audit/.

## Results

| Scenario | Predicted candidates | Confirmed predicted candidates | Fixed items | Before passed / failed / errors | After passed / failed / errors |
| --- | --- | --- | --- | --- | --- |
| s1-null-user | 6 | 6 | 6 | 46 / 6 / 0 | 52 / 0 / 0 |
| s2-cents | 3 | 3 | 6 | 46 / 6 / 0 | 53 / 0 / 0 |
| s3-pydantic2 | 4 | 0 | 4 | 26 / 8 / 6 | 46 / 0 / 0 |

Counts distinguish test failures from collection errors. A collection error can block several tests, so before/after totals need not match. S1 metrics.predicted also includes one affected route contract (7); the table and accuracy use only candidate ids (6). S3 uses full-suite upgrade evidence, not individually confirmed code proofs.

## s1-null-user

precision: 1.0, recall: 1.0, truePositives: 6, falsePositives: 0, falseNegatives: 0

| id | predicted | truth | correct? |
| --- | --- | --- | --- |
| shop/orders/invoice.py#build_invoice | will_break | will_break | yes |
| shop/orders/service.py#create_order | will_break | will_break | yes |
| shop/users/routes.py#get_user_route | will_break | will_break | yes |
| shop/payments/charge.py#charge | will_break | will_break | yes |
| shop/payments/receipt.py#render_receipt | will_break | will_break | yes |
| shop/admin/reports.py#user_spend_report | will_break | will_break | yes |
| shop/notifications/email.py#send_welcome | safe | safe | yes |

No false positives or false negatives. All six original predictions are reproduced by passing-on-base/failing-on-head proofs, and all pass after repair.
## s2-cents

precision: 1.0, recall: 0.5, truePositives: 3, falsePositives: 0, falseNegatives: 3

| id | predicted | truth | correct? |
| --- | --- | --- | --- |
| shop/payments/receipt.py#render_receipt | will_break | will_break | yes |
| shop/notifications/email.py#send_receipt_email | will_break | will_break | yes |
| shop/orders/invoice.py#payment_line | safe | will_break | NO |
| shop/admin/reports.py#revenue_total | will_break | will_break | yes |
| shop/payments/routes.py#post_payment | safe | will_break | NO |
| shop/payments/repo.py#save_payment | safe | will_break | NO |
| shop/orders/invoice.py#build_invoice | missing | safe | yes |

Three false negatives; no false positives:

- save_payment: the analyst treated passive storage as safe, overlooking the persisted dollar-unit contract.
- post_payment: the analyst treated echoing an amount as safe, overlooking the public API dollar-unit contract.
- payment_line: the analyst treated dictionary passthrough as unit-agnostic, overlooking the invoice dollar-unit contract.

Three post-evaluation diagnostic proofs were added for these misses. They do not turn the original safe predictions into correct predictions. Fixed items can therefore exceed predicted or confirmed-prediction counts. The original admin proof was strengthened from a loose upper bound to the exact expected dollar amount.

S2 changes direct Payment test inputs to cents while keeping dollar-output expectations. Its patch had changed the route assertion to cents; repair restores the documented original dollar contract. Stored DollarPayment and charged Payment are distinct types, so converting a stored value twice does not shrink it again. One additional post-repair regression tests this round trip and all dollar consumers; this accounts for the increased final test count.

## S3 migration

No expected.json exists and no precision/recall is assigned. A clean Pydantic v1 baseline is run first; the same source/tests then run on Pydantic 2.9.2 before and after repair. No S1 null-user or S2 cents patch is applied. The clean baseline passes 46 tests. Repairs cover users, orders, payments, and core.

| Module | Before passed / failed / errors | After passed / failed / errors |
| --- | --- | --- |
| users | 6 / 0 / 7 | 47 / 0 / 0 |
| orders | 10 / 8 / 6 | 22 / 0 / 0 |
| payments | 8 / 0 / 5 | 33 / 0 / 0 |
| core | 3 / 0 / 3 | 8 / 0 / 0 |

## Provenance and reproduction

- Run `engine/.venv/Scripts/python scripts/reproduce.py` then `engine/.venv/Scripts/python scripts/evaluate_evidence.py` (use bin/python on POSIX).
- Each evidence/<scenario>/ directory contains base/before/after logs, JUnit XML, parsed counts, input graph/verdicts/proofs, repairs, added-line convention checks, and source/patch hashes.
- New work was done using Bob modes, not a separate session. Existing Bob screenshots and commit history are historical evidence only; missing screenshots are not fabricated.
- The old contaminated branches are preserved for audit; the reproducible isolated runner is the supported scenario execution path.
- Docker effects are conservative instruction invalidation estimates; no build duration or actual image-layer count is claimed.
- The app is a deliberately small synthetic fixture. These precision/recall values measure two fixed scenarios, not general performance on arbitrary repositories.

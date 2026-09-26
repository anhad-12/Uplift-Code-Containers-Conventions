# Uplift project rules

Uplift predicts what a change will break, proves it with a failing test, and repairs it with sandboxed workers.
Pipeline: PREDICT (graph + verdicts) -> PROVE (failing tests) -> REPAIR (workers) -> VERIFY (tests + report).
Two modes over one engine: `impact` (a patch) and `migrate` (a dependency upgrade). Docker-layer impact is part of impact; convention-aware fixes are part of migrate. These are layers within the two modes, never separate features. Do not use the phrase "blast radius" in any user-facing output (a rival is named BlastRadius); say "what a change will break" or "change impact".

## Stack
- Python 3.11 or 3.12 only. Windows paths are used in examples; use forward slashes in code.
- engine/  : the `uplift` package and CLI (venv: engine/.venv). Run commands as `uplift <command>` with that venv active.
- sample-app/ : FastAPI shop on Pydantic v1 (venv: sample-app/.venv). Package name `shop`, tests in tests/.
- dashboard/ : Dash app (venv: dashboard/.venv).
- Never install packages into the wrong venv. The demo app's tests run with sample-app/.venv only.

## Contract
- The report format is schema/report.schema.json. Never invent fields. Validate with `uplift validate <file>`.
- Verdict values: will_break, might_break, safe, unknown. Layer values: direct, indirect, contract.
- Work files go in .uplift/ (verdicts.json, proofs.json, catalog.json, occurrences.json, conventions.json, repair-<module>-<scenario>.json).
- Final reports go in reports/<scenario>.json.

## Working rules
- Stay inside the folder your mode allows. If a fix needs a change elsewhere, record it as blocked; do not do it.
- Commit messages start with `[bob <member><task>]`, for example `[bob A6] orders repair for S1`.
- Never guess. If an input file is missing, say so instead of inventing callers, verdicts or numbers.
- Every number you report must come from a command you ran. Paste the command output.
- Never read sample-app/scenarios/*.expected.json (hidden ground truth; only the evaluation task may).
- Keep console output ASCII.

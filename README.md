# Uplift

Know what a change will break before you merge, then prove and repair it.

Uplift combines a Python change-impact engine, isolated scenario repairs, and a Dash dashboard. Impact mode covers callers, API contracts, tests, and conservative Docker cache effects. Migration mode applies a guide-derived catalog and checks repairs against observed repository conventions.

Original IBM Bob predictions, proof sources, modes and historical sessions are retained. Scenario isolation, repairs, integration fixes, evaluation and verification were completed using Bob modes. Final reports explicitly identify that provenance.

## Run locally

Use Python 3.11 (recommended for the pinned Pydantic v1 baseline):

```powershell
py -3.11 scripts/setup.py
engine/.venv/Scripts/python scripts/reproduce.py
engine/.venv/Scripts/python scripts/evaluate_evidence.py
engine/.venv/Scripts/python scripts/convention_demo.py
engine/.venv/Scripts/python scripts/verify.py --run
dashboard/.venv311/Scripts/python dashboard/app.py
```

Open http://127.0.0.1:8050. On Linux/macOS, use `python3.11` and replace `Scripts/python` with `bin/python`.

The four environments keep the engine/MCP dependencies, Pydantic v1 app, Pydantic v2 app and dashboard separate. `scripts/setup.py` never installs into the system interpreter.

## Measured results

| Scenario | Before repairs | After repairs | Prediction precision / recall |
| --- | --- | --- | --- |
| S1: missing user | 46 passed, 6 failed | 52 passed | 1.00 / 1.00 |
| S2: cents conversion | 46 passed, 6 failed | 53 passed | 1.00 / 0.50 |
| S3: Pydantic v2 | 26 passed, 8 failed, 6 collection errors | 46 passed | Not applicable |

S2 includes an additional post-repair regression for repeated storage and downstream dollar consumers. S2's three missed contracts remain visible in the original predictions, even though all six breaks are repaired. Collection errors can prevent multiple tests from running; they are reported separately from assertion failures.

[Evaluation and every miss](evidence/eval.md) · [Measured convention comparison](docs/convention-demo/README.md) · [Completion record](docs/completion.md)

## Reproducibility

`sample-app/` stays on the clean Pydantic v1 baseline. `scripts/reproduce.py` creates disposable, isolated copies, applies exactly one scenario patch, runs proofs before and after repairs, and writes reports plus raw evidence. The legacy scenario branches were contaminated; they are preserved for audit and are not the supported reproduction path.

- `scenarios/`: frozen Bob verdicts, proof inputs, repair patches, migration catalog and conventions.
- `evidence/<scenario>/`: test console logs, JUnit XML, parsed results, repair diffs and source hashes.
- `reports/`: final reports and release notes.
- `dashboard/reports/`: the same real reports; mocks live only in test fixtures.
- `.bob/`: nine modes, four skills and a portable MCP launcher.

Engine CLI: `engine/.venv/Scripts/uplift --help`. To mark a report verified, `uplift report --verified` requires `--verification` containing a successful, nonempty full-suite result. `--generated-by bob` and `--conventions` preserve provenance and compliance data.

Docker output reports possible invalidation by Dockerfile instruction position. It does not claim measured build time or actual image-layer counts. See [limitations](docs/docker-impact.md).

## Evidence and deployment

Historical Bob screenshot gaps remain disclosed. `scripts/verify.py --require-bob-evidence` additionally enforces the original competition screenshot requirements; ordinary verification checks implementation readiness without inventing sessions.

The dashboard has deployment configuration in `dashboard/render.yaml`. No public deployment URL is claimed; run locally or deploy using your own hosting account. CI rebuilds all scenario evidence, runs tests, and retains the generated evidence as an artifact.

MIT licensed. See [SOURCES.md](SOURCES.md) and [Bob usage](docs/bob-usage.md).

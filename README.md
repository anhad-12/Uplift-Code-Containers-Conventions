# Uplift

**Know what a change will break. Prove it. Fix it.**

Uplift takes a code change (a patch, or a dependency upgrade) and runs three steps with IBM Bob 2.0:

1. **Predict.** A deterministic engine builds a code graph of everything that could be affected (callers, routes, tests). A read-only Bob mode judges each place: will break, might break, safe, with a reason and a fix.
2. **Prove.** Bob writes a test for each predicted break. The engine confirms it passes on the old code and fails on the new code.
3. **Repair.** Sandboxed Bob workers, each allowed to edit only one module, fix the breaks in parallel. The verifier re-runs everything.

The dashboard shows the blast radius, the proofs, the repairs and the measured numbers.

> Status: work in progress for the IBM Bob 2.0 Hackathon (Sep 25-27, 2026). This README is completed at the end; see [PLAN.md](PLAN.md) for the build plan.

## Repo map

| Folder | What |
| --- | --- |
| `.bob/` | Bob custom modes, skills and rules that make up Uplift's brain |
| `engine/` | `uplift` Python package: CLI and MCP server |
| `sample-app/` | FastAPI (Pydantic v1) demo shop with pytest tests and three scenarios |
| `dashboard/` | Dash + dash-cytoscape dashboard |
| `evidence/` | Real reports and the accuracy write-up |
| `bob_sessions/` | IBM Bob task session screenshots and log |
| `schema/` | The report format shared by everything |

## Built with

- **IBM Bob 2.0** created and extended the code files in this repo (the engine, the Bob modes and skills, the demo app, the dashboard) and did the reasoning at the heart of the product: impact verdicts through parallel subagents, proof tests, sandboxed parallel repairs, reading the migration guide PDF, and the accuracy evaluation (see `.bob/`, `bob_sessions/` and the `[bob X#]` commits).

## Bob usage
See `docs/bob-usage.md` and `bob_sessions/`.

## Data
See [SOURCES.md](SOURCES.md). No personal, client, confidential or social-media data.

## License
MIT

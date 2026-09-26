# Uplift

**Know what a change will break before you merge — in your code, your containers, and your conventions. Then let Bob fix it.**

> Uplift tells you what a change will break — in your code, your tests, your API contracts, and your Docker build — before you merge it. Then it uses IBM Bob to fix everything safely, matching your team's coding conventions so the fixes look hand-written.

Uplift is **one engine, two modes, one shared JSON report**:

- **Impact Mode** answers "what will this change break?" across code, tests, API contracts **and infrastructure**. A deterministic engine builds a 3-hop code graph, maps tests to affected code, and checks Dockerfile layer invalidation; Bob judges each item.
- **Migrate Mode** answers "upgrade this dependency safely, matching our style." Bob reads the vendor's migration guide, a Convention Scanner learns the repo's patterns, and sandboxed workers fix each module in parallel — so the fixes look hand-written, not generic AI output.

Both modes run the same four steps with IBM Bob 2.0:

1. **Predict.** The engine builds a code graph of everything that could be affected (callers, routes, tests, Docker layers). A read-only Bob mode judges each place: will break, might break, safe, with a reason and a fix.
2. **Prove.** Bob writes a test for each predicted break. The engine confirms it passes on the old code and fails on the new code.
3. **Repair.** Sandboxed Bob workers, each allowed to edit only one module, fix the breaks in parallel — following the repo's own conventions. The verifier re-runs everything and checks the new lines against those conventions.
4. **Verify & Show.** The verifier re-runs the suite, writes release notes, and the engine writes `report.json`. The dashboard shows the impact graph (with a Docker node), the proofs, the repairs, the convention compliance and the measured numbers — including the misses.

Docker impact and convention-aware fixes are not separate features; they are layers **within** the two modes — proof that the change-impact analysis is truly comprehensive.

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

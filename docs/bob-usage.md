# Bob Usage Statement

## How IBM Bob 2.0 powers Uplift

Uplift is not a wrapper around Bob. Bob is the reasoning layer that sits on top
of a deterministic engine. The engine computes; Bob decides.

### What Bob does

| Task | Bob mode | What Bob does |
|---|---|---|
| A0 | Agent | Writes `.bob/rules/rules.md` — the persistent context for all later tasks |
| A1 | Agent / Plan | Creates all 9 custom modes and 3 skills in `.bob/` |
| A2 | `uplift-impact-analyst` | Calls `uplift_graph` (MCP), spawns **parallel subagents** — one per module — to judge each candidate with the impact-verdict-rubric skill |
| A3 | `uplift-prover` | Uses document understanding to read each candidate's source; writes proof tests that state the old contract |
| A4 | `uplift-worker-users` | Sandboxed repair of the users module only (file-permission wall: `sample-app/shop/users/`) |
| A5 | `uplift-migration-planner` | Reads the Pydantic v2 migration guide PDF with **document understanding**; produces `.uplift/catalog.json` |
| A6 | `uplift-worker-*` | Three sandboxed workers (orders, payments, core) repair in **parallel** |
| A7 | `uplift-verifier` | Re-runs tests, assembles the final report via `uplift_report` (MCP) |
| A8 | Agent | Reveals hidden ground truth, runs `scripts/accuracy.py`, writes `evidence/eval.md` naming every miss |
| A9 | Agent | Publishes reports to `evidence/` and `dashboard/reports/` |
| A11 | `uplift-convention-scanner` | Reads 8-12 repo files; writes `.uplift/conventions.json`; workers use it to match codebase style |

### Bob features used

- **Agent mode** — orchestration tasks (A0, A8, A9)
- **Parallel subagents** — A2 spawns one subagent per module simultaneously; A6 runs three workers in parallel
- **Custom modes with sandboxed permissions** — 9 modes, 6 roles; each worker can only edit its own module folder
- **Skills** — `impact-verdict-rubric` (verdict logic), `write-proof-test` (proof structure), `migration-guide-reader` (catalog extraction)
- **Document understanding** — A5 reads the Pydantic v2 migration PDF
- **MCP tools** — `uplift_graph`, `uplift_proof_run`, `uplift_migrate_scan`, `uplift_report` called from Bob modes

### Bob session log

See `bob_sessions/LOG.md` for per-task coin cost, screenshot file name, and
commit hash. Screenshots are in `bob_sessions/`.

### Honest accounting

- The deterministic parts (graph walk, test execution, risk score, schema
  validation, accuracy math) are done by the engine, not Bob.
- Bob's session summaries are the record of Bob usage. Every verdict, proof,
  repair and migration catalog entry comes from a logged Bob task.
- Numbers in the dashboard come from `reports/*.json`, which are assembled by
  `uplift report` (engine) from Bob's `.uplift/*.json` output files.
- Misses are named in `evidence/eval.md` — we do not round up precision or recall.

---

*Replace the task table rows with actual LOG.md data before submission.
See PLAN.md sections 16 and 17 for the writing guide and pre-submission checklist.*

# Uplift: master build plan (Python edition)

Working name: **Uplift**. Rename freely; nothing in the code depends on it.
Deadline: **Sep 27, 8:30 PM IST** (11:00 AM ET). Video and slides are handled outside this plan.
Everything is Python: engine, demo app, dashboard, MCP server, scripts, CI.

## 1. Positioning

> Uplift **predicts** what a change will break, **proves** it with a failing test, and **repairs** it with sandboxed Bob workers, then shows the numbers.

Why not "a blast radius checker": a Python project called *BlastRadius* is already submitted (AST call graph, risk score, generated pytest). It stops at detection, has no visible Bob usage, no hosted demo and no repair. Uplift is the closed loop.

| Rival | What they have | What we do that they don't |
| --- | --- | --- |
| BlastRadius (BlindBit) | Python call graph, risk score, test generation | Bob-judged verdicts for behaviour changes, proof by failing test, automatic repair, API-route contracts, dependency migrations, real Bob modes/skills |
| Cutover | Lost-write detection with before/after numbers (16/48 fail, then 116/116 pass) | Our before/after is measured too, but on any change, not just DB migrations |
| FORTIFY | Inject failure, fix, re-test loop | Same loop discipline, applied to code changes |
| CodeOns | One Bob skill, parallel analysis | Nine Bob modes with hard permissions, four skills, parallel subagents and sandboxed workers |
| OpsPilot AI | Paste an error, get a Gemini patch | Whole-repo, measured, Bob-native |
| MajorTom (#2 in the landscape PDF) | Express 4 to 5 migration from the vendor guide, a verbatim quote per edit, 16/16 edits, honest accounting | We migrate a different library (Pydantic v1 to v2, so no head-to-head on the same demo) and differ in *how*: the migration starts from a measured blast radius, is proven by real failing tests before any fix, is fixed by parallel sandboxed workers, and **matches the repo's conventions** (F16). We keep the guide quotes too. |
| Issue to PR, Day-One Ready | Sandboxed Bob modes with file-permission walls | Permission walls are now common among top entries: table stakes, not the headline |
| Witnessed, uncaught, Rehearsal, Inbin Gate | "Don't trust the green checkmark": prove what an agent or a test claims | The crowded meta-lane. We prove **predictions about a change before merge**, and we report our misses |

**Correction to the landscape PDF:** it says zero teams build a graph-based blast-radius engine. BlastRadius (BlindBit) does. The lane is less crowded than the others, not empty.

## 2. The pipeline

```
change (patch or dependency upgrade)
  -> PREDICT  engine builds a code graph; Bob (Impact Analyst, cannot edit code) judges each affected place
  -> PROVE    Bob (Prover) writes a test that passes on base and fails on head; engine runs both
  -> REPAIR   Bob workers in parallel, each allowed to edit only its own module folder
  -> VERIFY   Bob (Verifier) re-runs everything, writes release notes; engine writes report.json
  -> SHOW     dashboard + PR comment
```

The engine is deterministic (what could be affected, what ran, what passed). Bob is the judge and the fixer. Every claim in the dashboard traces to a line of code or a test run.

## 3. Features

| ID | Feature | Owner | Priority |
| --- | --- | --- | --- |
| F1 | Diff to changed symbols, classified (signature / returnShape / behavior / removed / renamed) with deterministic hints ("raise removed", "return None added") | B | MUST |
| F2 | Reference graph, 3 hops, with code snippets | B | MUST |
| F3 | FastAPI route map, so affected routes are tagged as **contracts** | B | MUST |
| F4 | Test mapping, `testsToRun`, `untested` flags | B | MUST |
| F5 | Bob verdicts: will_break / might_break / safe + reason + fix (Impact Analyst mode) | A | MUST |
| F6 | **Proof**: Bob writes a failing test; engine confirms passes-on-base, fails-on-head | A + B | MUST |
| F7 | **Repair**: sandboxed worker modes fix modules in parallel | A | MUST |
| F8 | Migrate: Bob reads a migration guide PDF into a catalog; engine scans for occurrences; tests run on the upgraded dependency before and after | A + B | MUST |
| F9 | Verifier + release notes | A | SHOULD |
| F10 | Risk score with printed formula (contractHits = contracts judged will_break or might_break), report merge and schema validation | B | MUST |
| F11 | PR comment generator + GitHub Action | B | SHOULD |
| F12 | Dashboard (Dash + dash-cytoscape): scenario picker, graph, detail panel, pipeline stepper, metrics, migrate view, drop-your-own-report | C | MUST |
| F13 | Accuracy evaluation: precision and recall against ground truth | A | MUST (our credibility) |
| F14 | **MCP server** (Python `mcp` package) exposing the engine to Bob as tools (`uplift_graph`, `uplift_proof_run`, `uplift_migrate_scan`, `uplift_report`), registered in `.bob/mcp.json` | B | SHOULD (matches Cutover's Bob depth) |
| F15 | Rigor: engine unit tests, sample-app tests, CI workflow that runs both, MIT LICENSE, `evidence/` = committed real reports | B | MUST |
| F16 | **Convention-aware repair**: a Convention Scanner mode reads the repo and writes `.uplift/conventions.json` (naming, imports, error handling, file layout); workers must follow it; the Verifier checks new lines against it and retries once on a mismatch. Demo: generic fix vs convention-aware fix side by side | A (+ C badge) | SHOULD |
| F17 | **Docker impact**: deterministic Dockerfile parser; if a changed file or `requirements.txt` sits in an early COPY layer, flag which layers rebuild; shown as a container node in the graph | B (+ C node) | STRETCH: only after CP2 is green |

## 4. Repo layout

```
.bob/                 A   custom_modes.yaml, rules/rules.md, skills/*/SKILL.md, mcp.json   (committed: Bob is part of the product)
engine/               B   Python package `uplift` (src/uplift/*.py, tests/), CLI `uplift`
sample-app/           B   FastAPI shop (Pydantic v1) + pytest + scenarios/
dashboard/            C   Dash app (app.py, reports/, assets/)
schema/               -   report.schema.json + mock examples (already written)
prompts/              -   ready-to-paste Bob prompts per member
reports/              A   working reports produced by Bob runs (final ones go to evidence/ and dashboard/reports/)
evidence/             A   final real reports + eval.md (what judges and the dashboard read)
.github/workflows/    B   ci.yml (tests) and uplift.yml (PR comment)
scripts/              -   verify.py (the "what's implemented?" checker), scenario_branch.py (B2)
bob_sessions/         all screenshots + LOG.md
docs/                 C   statements, migration guide PDF
.bobignore            -   hides ground truth from Bob (section 11b)
```

## 5. Setup (everyone, first hour)

- Python **3.11 or 3.12** (`python --version`). Pydantic v1 (used by the demo app) does not work on newer Pythons; if you have 3.13+, install 3.12 and use `py -3.12`.
- **Separate virtual environments** (Pydantic v1 in the demo app conflicts with the `mcp` package, which needs Pydantic v2):
  - `engine/.venv`: engine, its tests, the MCP server.
  - `sample-app/.venv`: the demo app and its tests (Pydantic v1 pinned).
  - `dashboard/.venv`: the Dash app.
- Create with `py -3.12 -m venv <folder>\.venv` then `<folder>\.venv\Scripts\python -m pip install -r <folder>\requirements.txt` (Windows). The engine runs the demo app's tests with **the demo app's interpreter** (`--app-python`, default `sample-app/.venv`), and builds a temporary venv for the dependency-upgrade test.
- Bob IDE workspace = the repo root.

## 6. Demo scenarios (all built into `sample-app/`)

| ID | Change | Why it is interesting |
| --- | --- | --- |
| S1 | `get_user` returns `None` instead of raising `NotFoundError` | Python has no compiler to catch it; the full suite stays green (16 of 16 on the reference app) while callers that relied on the raise break, plus one route contract |
| S2 | Payment amounts change from dollars to cents | Same kind of value (a number), silent semantic break across 6+ places (receipt, route, email, invoice, admin revenue, repo); the suite stays green |
| S3 | Pydantic v1 to v2 (with FastAPI bumped to a v2-compatible release) | Document understanding of the official migration guide, parallel workers, real before/after test counts (6 failed, 8 passed on the reference app, failures in four modules) |

Each scenario has `sample-app/scenarios/<id>.patch` (paths relative to `sample-app/`; for S3 the patch bumps versions in `requirements.txt`) and `<id>.expected.json` with ground truth (S1 and S2), including **safe decoys** (callers that already handle the new behaviour). Ground truth is derived by applying the patch and running the tests, not by guessing. S3's ground truth is the real test failures on Pydantic v2.

**Isolation (one git branch per scenario).** Scenarios must never contaminate each other, and S3 must not break the Pydantic v1 baseline.
- `main` keeps a pristine `sample-app/`. It also holds the engine, `.bob/`, dashboard and `evidence/`.
- `scenario/s1-null-user`, `scenario/s2-cents`, `scenario/s3-pydantic2` are each `main` plus that scenario's patch, applied and committed (`git apply --directory=sample-app <patch>`). Bob's predict, prove and repair work happens **on its branch** (proof tests and repairs are committed there).
- The engine's `--applied` flag means "the repo already contains the patch": head = current tree, base = the tree with the patch reverse-applied in a temp copy. Without the flag the engine applies the patch in a temp copy (used by CI on main).
- Only finished reports go back to `main`: `git checkout scenario/<id> -- reports/<id>.json`, then copy into `evidence/` and `dashboard/reports/`.
- Bonus: open each scenario branch as a real PR on the public repo. The GitHub Action then posts the Uplift comment on it: live demo material.

### What testing the reference code taught us (already handled in the prompts)

The prompts contain reference code that was **run against a scratch copy of the demo app** before it went in. That caught real problems: `httpx` 0.28 breaks Starlette's TestClient (pin 0.27.2); `mcp` 2.x renamed `FastMCP` (pin `<2`); pytest aborts on a collection error unless `--continue-on-collection-errors`, and junit reports those with an empty classname; Windows git makes CRLF patches (patches are generated with `difflib`); callers' error paths must NOT be tested in the baseline, or S1 and S2 would not be invisible; the dashboard must carry its own copy of the schema because Render deploys only `dashboard/`.

## 7. Bob customization (the `.bob/` folder)

| Mode | Permissions (deterministic) | Job |
| --- | --- | --- |
| `uplift-impact-analyst` | read, execute, skill, subagent, edit only `.uplift/**` | Run the graph, spawn one parallel subagent per module to judge its candidates with the `impact-verdict-rubric` skill, write `.uplift/verdicts.json` |
| `uplift-prover` | read, execute, skill, edit only `sample-app/tests/uplift_proofs/**` | Write one failing test per will_break item using the `write-proof-test` skill |
| `uplift-migration-planner` | read, execute, skill, edit only `.uplift/**` | Read the guide PDF with the `migration-guide-reader` skill, write `.uplift/catalog.json` |
| `uplift-worker-users` / `-orders` / `-payments` | read, execute, edit only `sample-app/shop/<module>/**` | Fix that module only |
| `uplift-worker-core` | read, execute, edit only `sample-app/requirements.txt`, `sample-app/shop/*.py`, `sample-app/shop/admin/**`, `sample-app/shop/notifications/**` | Fix what the module workers cannot touch (app wiring, config, admin, notifications) |
| `uplift-convention-scanner` | read, execute, skill, edit only `.uplift/**` | Read 8-12 representative files with the `repo-conventions` skill, write `.uplift/conventions.json` |
| `uplift-verifier` | read, execute, edit only `reports/**` and `.uplift/**` | Re-run tests, check new lines against `.uplift/conventions.json`, write release notes, assemble the final report |

The demo line: "the analyzer literally cannot edit code, and each worker can only touch its own module, so three run in parallel without collisions."

**Verified against the Bob 2.0 install** (its bundled instructions in `extensions/bob-code/dist/extension.js`):
- Modes: `.bob/custom_modes.yaml`, top key `customModes`, fields `slug` (letters, numbers, dashes only), `name`, `roleDefinition`, `whenToUse`, `description`, `customInstructions`, `groups`, `allowedSubagents`. Groups: `read`, `edit`, `execute`, `mcp`, `skill`, `todo`, `subagent`, `mode`. **Shell access is `execute`, not `command`; a wrong group name silently grants nothing.** Restrict edits with a nested entry: `- - edit` then `  - fileRegex: "<regex>"`. Plain ASCII only; an invalid regex or a duplicate group drops the whole file.
- Skills: `.bob/skills/<skill-name>/SKILL.md`; the directory name is the skill name.
- MCP: `.bob/mcp.json` with `mcpServers`; a server can be limited to specific modes with `groups`. It hot-reloads on save.
- Rules: `.bob/rules/`, mode-specific `.bob/rules-<mode>/`, or an `AGENTS.md`. Bob also honours `.bobignore`.
- Subagents: the `subagent` group gives Bob a `spawn_subagent` tool; several calls in one turn run in parallel; subagents cannot spawn subagents. Custom worker modes are probably not spawnable as subagents (the presets are built in), so the workers run as **parallel tasks**, and the Impact Analyst uses real parallel subagents for its verdicts. Task A1 confirms this.

## 8. Ownership and order

Every member works only in their own folder and hands over through the schema.

- **B unblocks everyone.** First: sample-app + scenarios (B1, B2). Then the engine.
- **A** starts with `.bob/` (needs nothing), then runs modes as B's outputs land. Until the engine exists, A tests modes by letting Bob find callers itself.
- **C** starts from `schema/examples/*.mock.json` and never waits. Mocks are labelled `generatedBy: "mock"` and `scripts/verify.py` fails if any mock is still in `dashboard/reports` at the end.

Prompts: `prompts/A-brain.md`, `prompts/B-engine.md`, `prompts/C-face.md`.

## 9. Timeline (IST)

| When | Goal | Gate |
| --- | --- | --- |
| Sep 26, now to 5 PM | Everyone on hackathon Bob account, Python 3.12 venvs created; A0-A1, B1, C1 started | Repo public, this plan pushed |
| Sep 26, to 11 PM | B: sample-app, scenarios, diff + graph (B1-B4). A: modes, skills, first Impact run (A1-A3). C: dashboard renders the mocks (C1-C3) | **CP1**: `uplift graph` works on S1; Impact Analyst produced real verdicts |
| Sep 26 night to Sep 27, 10 AM | B: routes, tests, proof-run, report, migrate-scan (B5-B8). A: prover, workers, migration planner (A4-A6). C: migrate view, scenario picker (C4-C6). Sleep in shifts | **CP2**: S1 + S2 + S3 real reports; dashboard reads real reports |
| Sep 27, 10 AM to 2 PM | A: accuracy eval (A8), verifier (A7), then conventions (A11-A12) if coins allow. B: CLI polish, Action (B9-B10), then Docker (B13) only if CP2 was green. C: polish, deploy (C7-C8), then convention badge / Docker node (C10) | **Feature freeze 2 PM** |
| Sep 27, 2 to 4 PM | README, SOURCES.md, statements, screenshot check, `python scripts/verify.py` green | Everything but video and slides ready |
| Sep 27, by 5 PM | **Submit a complete version.** Refine after if time remains | Submitted |
| Sep 27, 5 to 8:30 PM | Buffer | Deadline 8:30 PM |

## 10. Bobcoin budget

40 per person. After your first task, look at Settings > General and note what one task cost, then plan the rest; the coin figures in the prompts are guesses.

| Gate | Max used per person |
| --- | --- |
| CP1 (Sep 26, 11 PM) | 14 |
| CP2 (Sep 27, 10 AM) | 30 |
| Feature freeze | 36 (keep 4 for repairs) |

If coins run short: merge tasks (each prompt file marks the ones that can be combined), or hand a task to a teammate with coins left.

## 11. Bob sessions protocol

After **every** Bob task:
1. Bob chat > Tasks > select the task > click the header to see the session summary; screenshot as PNG.
2. Save as `bob_sessions/uplift_<A|B|C>_task<NN>_<slug>_summary.png`.
3. Add a row to `bob_sessions/LOG.md` (member, task id, what Bob did, files, coins).
4. Commit Bob's files with the prefix `[bob A3] short message`.

`scripts/verify.py` counts screenshots per member, log rows per member and `[bob` commits.

### 11a. Who does what, and the honesty rule

### 11b. Integrity rules (what the strongest entries do, and what judges punish)

- **Hidden ground truth.** Bob must not see `sample-app/scenarios/*.expected.json` while predicting. `.bobignore` blocks Bob's file access. It is committed with the ground-truth line commented out; B uncomments it right after B2 finishes, and A comments it out again only for task A8. The toggle shows in git history and is our "hidden acceptance suite".
- **No invented numbers.** Every metric comes from a real run. Docker rebuild cost is either measured (`docker build` timings) or stated as "layers 3-7 rebuild" with no seconds.
- **Report misses.** The dashboard and statements show our false positives and false negatives.
- **Pre-existing code disclosure.** Nothing in this repo predates Sep 25, 2026. If anyone copies in older code, disclose it in the Bob Usage statement.
- **Say the four Bob features by name** in README, statements and video: Agent mode, parallel tasks, subagents, document understanding.

## 12. Definition of done, and what to cut

Winning bar:
- S1, S2, S3 all have real reports (`generatedBy: "bob"`), each with proofs and repairs.
- Accuracy numbers computed from ground truth, shown as they are (including misses).
- Dashboard live at a public URL; works on a phone; loads any dropped report.json.
- Repo public, `.bob/` committed, screenshots from all three members, `python scripts/verify.py` green.

If behind, cut in this order: F17 (Docker), F14 (MCP; modes fall back to the CLI), F11 (Action), F9 (release notes polish), S2, drag-drop report. Never cut: F5, F6, F7, F13, F15, or the dashboard.

Rigor bar (Cutover has 204 commits, 91 tests, CI, MIT, evidence folder; we match the shape): engine has unit tests; CI runs engine + sample-app tests on every push; LICENSE is MIT; real reports live in `evidence/`; small, frequent `[bob X#]` commits.

## 13. Being the most-liked

- **Submit a complete version early** (by 5 PM). Votes accumulate over time and the leaders started a day ago.
- The dashboard is the first thing voters see. Give the cover, first screen and the "predicted 5, confirmed 4, fixed 4, 0 regressions" card the most polish.
- Share the demo link in the lablab Discord and with friends. Ask for votes honestly; do not use bots or vote swaps.

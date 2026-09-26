# Uplift: master build plan (Python edition)

Working name: **Uplift**. Rename freely; nothing in the code depends on it.
Deadline: **Sep 27, 8:30 PM IST** (11:00 AM ET). Video and slides are handled outside this plan.
Everything is Python: engine, demo app, dashboard, MCP server, scripts, CI.

## 1. Positioning

**Tagline:** Know what a change will break before you merge — in your code, your containers, and your conventions. Then let Bob fix it.

**The pitch (memorize this):**
> Uplift tells you what a change will break — in your code, your tests, your API contracts, and your Docker build — before you merge it. Then it uses IBM Bob to fix everything safely, matching your team's coding conventions so the fixes look hand-written.

**Naming rule:** never use the phrase "blast radius" in any public-facing copy (README, tagline, pitch, demo narration, statements, dashboard/PR labels, lablab text). A rival submission is literally named *BlastRadius*, so the phrase both invites a "someone already built this" reaction and hands them the association. Say "what a change will break", "change impact" or "impact map" instead. The phrase is fine only in *this* document's competitive-analysis prose below, where we are discussing that lane and that rival by name.

**Four ideas, two modes, one graph.** The plan started with four ideas (blast-radius analysis, Docker optimization, repo-specific conventions, dependency migration). The winning move is not four features — it is recognising they are all aspects of the same problem, *understanding the full impact of a change before it ships*, and folding them into two modes over one shared engine:

| Original idea | Lives in | How it shows up |
| --- | --- | --- |
| Blast-radius analysis | **Impact Mode** (core) | 3-hop dependent graph, Bob verdict per item, risk score, untested-path flags |
| Docker optimization | **Impact Mode** (infra layer) | The graph extends into Dockerfiles: a change flags layer invalidation and cache-bust cost, shown as an "infra impact" node |
| Repo-specific conventions | **Migrate Mode** (quality layer) | A Convention Scanner reads the repo's patterns first, so Bob's fixes match the codebase style, not generic AI style |
| Dependency migration | **Migrate Mode** (core) | Migration guide -> catalog -> parallel Bob fixes per module -> before/after tests -> release notes |

Docker impact and convention-aware fixes are **not separate features and never pitched as such** (see fatal mistake 1 in section 14): they are layers inside Impact and Migrate, proof that the change impact is truly comprehensive.

Why not "a blast radius checker": a Python project called *BlastRadius* is already submitted (AST call graph, risk score, generated pytest). It stops at detection, has no visible Bob usage, no hosted demo and no repair. Uplift is the closed loop.

**Competitive position (from the 35+-submission landscape scan):** graph-based blast-radius analysis is an *uncrowded* lane (zero teams show affected callers/routes/tests before merge; the crowd is on "don't trust the green checkmark" post-merge). Docker-aware impact analysis is *uncontested* — no team connects code changes to container-level cost. Convention-aware migration is our line against MajorTom (#2 ranked): their fixes are correct but generic; ours are correct **and** idiomatic.

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
| F16 | **Convention-aware repair (Migrate Mode quality layer, differentiator vs MajorTom)**: a Convention Scanner mode reads the repo and writes `.uplift/conventions.json` (naming, imports, error handling, file layout); workers must follow it; the Verifier checks new lines against it and retries once on a mismatch. Demo: generic fix vs convention-aware fix side by side (this side-by-side is mandatory in the video — see section 14) | A (+ C badge) | SHOULD (headline differentiator) |
| F17 | **Docker impact (Impact Mode infra layer, uncontested lane)**: deterministic Dockerfile parser; if a changed file or `requirements.txt` sits in an early COPY layer, flag which layers rebuild and the cache-bust cost; shown as a container node in the graph. ~2-3h, regex-level parser that adds a node type to the existing graph, not a full Docker engine | B (+ C node) | SHOULD (differentiator; build after CP2 is green so it never risks the core loop) |

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

**Mode count, for the statements (do not miscount).** The `.bob/` folder ships **9 sandboxed modes** across **6 roles**: Impact Analyst, Prover, Migration Planner, Migration Worker (four module-scoped instances: `-users`, `-orders`, `-payments`, `-core`), Convention Scanner, Verifier. When a statement or pitch wants a short headline, say **"6 custom Bob modes, with the Migration Worker sandboxed into four module-scoped instances (9 modes total)"** — do not paste the round "5 modes" figure from any draft, because it omits the Prover and the worker split and will not match `.bob/custom_modes.yaml`. The four-way worker split *is* the least-privilege sandboxing story, so it is a selling point, not a footnote.

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

If behind, cut in this order: F14 (MCP; modes fall back to the CLI), F11 (Action), F9 (release notes polish), F17 (Docker), F16 (conventions), S2, drag-drop report. Never cut: F5, F6, F7, F13, F15, or the dashboard.

F16 and F17 are the two differentiators, so cut them only as a last resort **after the core Predict->Prove->Repair loop is proven on S1 and S2**, and cut them *silently* — if either is dropped, remove it from the pitch, the demo script and the statements too. Never present a half-built Docker node or a convention badge with no data behind it; a shown-but-empty differentiator reads worse than one that was never mentioned.

Rigor bar (Cutover has 204 commits, 91 tests, CI, MIT, evidence folder; we match the shape): engine has unit tests; CI runs engine + sample-app tests on every push; LICENSE is MIT; real reports live in `evidence/`; small, frequent `[bob X#]` commits.

## 13. Being the most-liked

- **Submit a complete version early** (by 5 PM). Votes accumulate over time and the leaders started a day ago.
- The dashboard is the first thing voters see. Give the cover, first screen and the "predicted 5, confirmed 4, fixed 4, 0 regressions" card the most polish.
- Share the demo link in the lablab Discord and with friends. Ask for votes honestly; do not use bots or vote swaps.

## 14. Fatal mistakes to avoid

1. **Presenting Docker and conventions as separate features.** They are NOT separate modes; they are layers within Impact and Migrate. The moment you say "we also have a Docker feature and a conventions feature" you sound like scope creep. Say: "Impact Mode shows what a change will break — code AND infrastructure. Migrate Mode fixes everything — matching your conventions."
2. **Claiming a confidence percentage with no methodology.** Show the formula, show the miss. "X of Y verdicts correct, here is the one we got wrong" beats "98.7% confidence" (that number is exactly what sank OpsPilot AI with the technical panel).
3. **Spending too long on Docker in the demo.** It is a ~10-second wow moment, not a 60-second deep dive. Show the Docker node, name the CI cost, move on. The code-level impact analysis is still the hero.
4. **Forgetting the convention side-by-side.** If you mention convention-aware fixes but do not show generic vs convention-aware output side by side, the judge cannot see the difference. Even a 5-second split-screen counts. This is the line against MajorTom.
5. **Not naming Bob's features aloud.** Agent mode, parallel tasks, subagents, document understanding — all four spoken in the narration and labelled on screen.
6. **Skipping pre-existing-code disclosure.** Nothing in this repo predates Sep 25, 2026. If anyone copies in older code, disclose it in the Bob Usage statement the way Cutover did (Cutover self-tagged "PreExistingProject" and it is a real scoring risk for them). Self-disclosure reads far better than a judge finding it.

## 15. The 3-minute demo script

Docker impact and convention-aware fixes are demo moments *within* the existing flow — no extra time, just richer content per segment. Keep the shape the strongest entries use: problem -> before (it lies/fails) -> Bob does the work -> after (proven, with a number) -> what is left unverified.

| Time | On screen | Narration | Bob feature |
| --- | --- | --- | --- |
| 0:00-0:15 | One-line change: `get_user` returns None. Its own test passes. Reviewers see green. | "This change compiles, its test passes. Reviewers see green. They do not see what it breaks." | — |
| 0:15-0:55 | PR opened. Graph renders: code nodes (red/yellow/green) + a container node (Docker icon, orange). One code node has an UNTESTED badge. | "Uplift walks the code graph 3 hops. 4 functions, 2 routes, 1 untested path. And — see the Docker icon — this change invalidates layer 3, adding ~2 min to every CI build. No reviewer saw that." | Agent mode (Impact Analyst) |
| 0:55-1:15 | Click a red node -> Bob verdict + fix. Click the Docker node -> layer detail + suggestion. Risk score with its formula. | "Bob says: will break, because it reads user.name. Fix: check for None. The Docker hit: split your COPY to preserve cache. Risk score 71, formula on screen." | Agent mode (verdict + infra reasoning) |
| 1:15-1:30 | Convention Scanner runs. Output: naming, imports, error-handling style. | "Before Bob fixes anything, Uplift scans the repo's conventions — how this team names things, imports, and handles not-found." | Agent mode (Convention Scanner) |
| 1:30-2:05 | Drop the Pydantic v2 guide. Bob extracts the catalog. Parallel workers fix modules; timer visible. Side-by-side: generic AI fix vs convention-aware fix. | "Migrate Mode. Bob reads the guide, extracts the breaking changes, fixes modules in parallel. Look at the fixes — they match YOUR conventions, not generic AI output." | Document understanding, parallel tasks, subagents |
| 2:05-2:25 | Tests: N red -> all green. Convention compliance: all pass. Release notes. Wall-clock time. | "Tests: N failing to N passing. Every fix matches the repo style. Release notes generated. Total time: X seconds." | Agent mode (Verifier + convention check) |
| 2:25-2:45 | Accuracy: X/Y verdicts correct, one miss shown with its reason. Docker layer invalidation correctly flagged. | "On our planted breaking changes: all affected code found. Verdicts X of Y correct — here is the one we missed and why. Docker layer hit: correctly flagged." | — |
| 2:45-3:00 | Bob task list, `.bob/` folder, custom modes, screenshot montage. | "Uplift ships as Bob custom modes — Impact Analyst, Convention Scanner, Migration Worker and more. Any team with Bob can run them. MIT licensed." | Custom modes (reusable) |

Keep total runtime 3:00 or under, with 90+ seconds of the product actually running.

## 16. Statement writing guide

**Problem & Solution (<=500 words).**
- *Problem:* a change passes its own tests but silently breaks callers, routes, contracts AND Docker cache layers no one looked at; risky dependency upgrades get postponed for months, and when AI finally does them the fixes do not match the team's style.
- *Solution:* Uplift computes a deterministic code graph, walks 3 hops of dependents, maps tests to affected code, checks Dockerfile layer invalidation, and hands each item to Bob for a verdict with a reason and a fix. Migrate Mode reads a vendor's migration guide (document understanding), extracts a breaking-change catalog, scans the repo's conventions, then runs parallel sandboxed Bob workers that fix each module — matching the team's naming, import and error-handling patterns.
- *Evidence:* state the A8 numbers with specifics, including what was missed, the wall-clock time, the convention-compliance rate, and the Docker layer invalidation correctly flagged.
- *Differentiator:* "Unlike linters that flag syntax and LLMs that guess, Uplift's change-impact map is computed from a real code graph that extends into your Docker build. Bob adds reasoning on top of structure and writes fixes that match your team's conventions."

**Bob Usage (<=500 words).**
- List every Bob task by ID from `bob_sessions/LOG.md` with what Bob did, files written and Bobcoins consumed. Lead with tasks A2-A8.
- Name the modes honestly using the count from section 7 (6 roles / 9 sandboxed modes; do not paste a round "5 modes" figure).
- List Claude Code's role separately: planning, README, statement drafts, glue code.
- Say the four Bob features by name: Agent mode, parallel tasks, subagents, document understanding.

## 17. Pre-submission checklist

**Video:** graph is the first visual after the problem; Docker/infra node visible and distinct; all four Bob feature phrases spoken; Convention Scanner output shown before Migrate fixes; generic-vs-convention side-by-side shown (even 5s); at least one honest miss reported; wall-clock timer visible during Migrate; untested-path node highlighted; total runtime <=3:00 with 90+ seconds of product running.

**Repo:** `.bob/` contains the modes from section 7; `engine/` has the Dockerfile parser (F17); `sample-app/` has a Dockerfile with a deliberate layer-ordering issue; `bob_sessions/` has screenshots from all three members + LOG.md; SOURCES.md complete; MIT LICENSE present; README has the risk-score formula AND the convention-detection explanation; real `report.json` for S1, S2, S3 committed (with `infraImpact` + `conventions` where applicable).

**Statements:** Problem & Solution under 500 words and mentions change impact + Docker impact + convention-aware fixes; Bob Usage lists every task with the correct mode count and a separate Claude Code role; no unexplained percentages.

**Dashboard:** live URL works with no backend (static site reading committed JSON); risk-score formula visible on hover/click; infra-impact nodes render with a container icon and layer detail on click; Migrate view shows the convention badge and compliance status; both Impact and Migrate views work on real data.

**lablab.ai form:** title, short description, tags; cover image = the impact graph WITH the Docker node; GitHub link, demo link, presentation and video attached; post-hackathon feedback form completed by all members ($100 reward).

## 18. Evidence we publish, and how to reproduce it locally

### 18a. What the strong entries published (and how we match it)

The landscape scan shows the winning entries do not just claim quality — they publish a small set of **reproducible numbers, including their own misses**. This is the single biggest scoring lever ("quantified honesty beats confident marketing"; "one real reproducible number beats a large vague one"). Here is what they reported and where ours comes from:

| Evidence type competitors showed | Example (from the landscape) | Where ours comes from | Shown where |
| --- | --- | --- | --- |
| Before/after test counts | Cutover 16/48 fail -> 116/116 pass; Spec2Code 17->22; MajorTom passing suite | `metrics.tests.before/after`, and `migration.modules[].testsBefore/After` per module | Dashboard summary card, report.json, eval.md |
| Precision/recall vs ground truth, **with the misses named** | Issue->PR 9/10 on a hidden acceptance suite, names the one missed; IBM-BOB2-HACK 8/10 diffs honest | Task A8: `accuracy()` over `sample-app/scenarios/*.expected.json` (hidden by `.bobignore` until A8) -> `metrics.accuracy` (precision, recall, TP, FP, FN) + `.uplift/eval.md` listing every miss and its cause | Dashboard "accuracy" card + "See what we missed", eval.md |
| Wall-clock time | MajorTom 19.5s | `metrics.secondsTaken` (engine-timed) | Dashboard, report.json, demo timer |
| Files/references scanned | LegacyFlow 31 references, 49 rules | `metrics.filesScanned` | Dashboard, report.json |
| Bobcoins consumed | Day-One Ready under 2 coins | `bob_sessions/LOG.md` coin column (per task) | Bob Usage statement; optionally a total on the dashboard Bob panel |
| Tested on a real, unmodified repo | Witnessed on 101 commits of python-tabulate; uncaught on 75M-download libs; Day-One Ready on 2 unmodified repos | See gap in 18b | drop-your-own-report (C7) |
| Live hosted demo | FORTIFY (Vercel), GraphWard (telemetry) | Dashboard on Render/HF Spaces (C8), no backend | Live URL |
| Docker layer invalidation correctly flagged | (uncontested — no competitor) | `infraImpact` from the deterministic Dockerfile parser (F17/B13); "layers 3-7 rebuild", seconds only if measured with `docker build` | Dashboard Docker node, report.json |
| Convention compliance rate | (our line vs MajorTom) | `conventions.compliance` (checkedLines, violations, retried) from the Verifier (A12) | Dashboard convention badge |

Rule for every number: it comes from a command someone ran (section 11b), the dashboard and statements show the misses, and Docker seconds are either measured or omitted (never invented).

### 18b. The one credibility gap, and how we close it

Unlike Witnessed/uncaught/Day-One Ready, our headline numbers come from **our own** `sample-app` with **planted** breaking changes, not a third-party repo. That is defensible and matches Issue->PR (the "benchmark for orchestration quality"): the scenarios are seeded, and the ground truth is **hidden from Bob** via `.bobignore` and revealed only for scoring — a real hidden acceptance suite, provable in git history. Say exactly that in the statements.

Optional credibility booster (only if CP2 is green and coins remain, not a blocker): run **Impact Mode, graph + verdicts only, no repair** on one small real third-party MIT-licensed repo, save the report, and load it through the dashboard's drop-your-own-report. Add it to SOURCES.md. This gives one "here it is on a repo we did not write" data point without risking the core demo. Do not attempt repair or migration on an external repo under time pressure.

### 18c. Local reproduction runbook (how you test everything yourself)

Anyone with the repo can regenerate every published number locally, in this order. Each step names the check that proves it worked.

0. **Setup** (section 5): Python 3.11/3.12; create `engine/.venv`, `sample-app/.venv`, `dashboard/.venv` and `pip install -r requirements.txt` in each. Confirm: `python --version`, and `engine/.venv` active -> `uplift --help` lists diff, graph, report, validate, proof-run, migrate-scan, upgrade-test, comment, run-all.
1. **Sample app is green at baseline:** `sample-app/.venv` -> `python -m pytest -q` in `sample-app/` (expect all pass; the planted breaks are invisible on `main` by design).
2. **Pick a scenario branch:** `git switch scenario/s1-null-user` (or s2/s3). The patch is already applied here, so engine commands take `--applied`.
3. **Predict (engine, deterministic):** `uplift run-all --repo sample-app --applied --scenario s1-null-user`. Writes `.uplift/graph.json`; prints which Bob mode/prompt to run next. Confirm the graph lists the affected callers/routes/tests.
4. **Verdicts, proofs, repairs (Bob):** run the A-brain prompts (A2 predict, A3 prove, A6 repair, A7 verify) for that scenario. Proof check: each proof test **passes on base and fails on head** (the engine records `passesOnBase`/`failsOnHead`); repair check: the suite goes red -> green with `regressions: 0`.
5. **Accuracy (the credibility number):** task A8 reveals ground truth, runs `python scripts/accuracy.py --report reports/s1-null-user.json --truth sample-app/scenarios/s1-null-user.expected.json`, writes `.uplift/eval.md` with precision, recall and **every miss**, then re-hides ground truth. Confirm `metrics.accuracy` is filled and eval.md names any FP/FN.
6. **Migrate (S3):** on `scenario/s3-pydantic2`, `uplift migrate-scan` + `upgrade-test` produce real Pydantic v2 before/after failures per module; the workers fix each module; the Verifier re-runs. Confirm `migration.modules[].testsBefore/After` are real counts.
7. **Docker impact (F17):** with a Dockerfile in `sample-app`, the run flags `infraImpact` (which layers rebuild). Any seconds must come from an actual `docker build`, else omit them.
8. **Validate + full readiness:** `uplift validate reports/*.json` (schema), then from the repo root `python scripts/verify.py --run` (static checks + engine and sample-app pytest). Green = everything the plan promises is present and the numbers reproduce.
9. **Dashboard:** `dashboard/.venv` -> `python dashboard/app.py`, open it, confirm all three scenarios render, the accuracy card and "See what we missed" work, and the Docker node + convention badge show for the scenarios that carry those fields.

If any number in the video, statements or dashboard cannot be regenerated by these steps, it does not ship.

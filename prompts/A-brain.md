# Member A: Brain (Bob modes, skills, reasoning, evaluation)

You own everything Bob **decides**: verdicts, proofs, repairs, migration plan, conventions, accuracy numbers. You also own `.bob/`, the folder that makes Bob part of the product.
Screenshot the task summary after every task (PLAN.md section 11). Log it in `bob_sessions/LOG.md`.

## How to use these prompts

- Paste the whole boxed prompt into a **new Bob task** (workspace = repo root). Use **Plan mode first** for A1 and A6, then Agent mode. Use the **mode the prompt names** for A2 onward.
- Every prompt has the exact file contents or formats Bob needs, plus a **Done when** command. Do not accept "done" without the command output. If a command fails, paste the failure into the same task and ask Bob to fix it.
- **Coin figures are guesses.** After your first task check Settings > General and recalibrate.
- **Branches.** Scenario work (A2 onward) happens on the scenario's branch, for example `git switch scenario/s1-null-user` (created by task B2). Reports return to `main` in A9. On a scenario branch the patch is already applied, so engine commands take `--applied`.
- **Engine.** The engine is the Python package `uplift` (task B3), venv `engine/.venv`. With that venv active, `uplift <command>` works. Where a prompt says "engine tools", use the MCP tools `uplift_graph`, `uplift_proof_run`, `uplift_migrate_scan`, `uplift_report` if B has shipped them (task B11); otherwise the CLI command. Output files are identical.
- **Demo app tests** run with the demo app's own interpreter: `sample-app/.venv/Scripts/python -m pytest` (Windows).
- **Hidden ground truth.** Until task A8, never read `sample-app/scenarios/*.expected.json` (it is in `.bobignore`).
- Do not fix core code by hand or with another tool; ask Bob. That keeps the session summaries honest.

---

## A0. Rules file  (about 1 coin)

````text
Read PLAN.md and schema/report.schema.json first.

Create .bob/rules/rules.md with EXACTLY this content (it loads into every Bob conversation, so keep it short):

```markdown
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
```

DONE WHEN: `.bob/rules/rules.md` exists and has fewer than 60 lines.
Commit: [bob A0] project rules
````


---

## A1. Modes and skills  (Plan mode first, about 3 coins)

Bob's format was verified from the Bob 2.0 install and this file was **checked with a script**: it parses, every group name is valid (`read`, `edit`, `execute`, `skill`, `subagent`; shell access is `execute`, NOT `command`), every regex compiles, and all 17 allow/deny path cases behave (Windows and POSIX paths). A wrong group name silently grants nothing and a bad regex drops the whole file, so do not edit it except to fix a check failure.

The four modes that call the engine tools (`uplift-impact-analyst`, `uplift-prover`, `uplift-migration-planner`, `uplift-verifier`) have the `mcp` group, which is what lets them use the MCP tools from task B11. Bob's own docs (built in) say: workspace modes live in `.bob/custom_modes.yaml`; skills live in `.bob/skills/<skill-name>/SKILL.md`; the directory name is the skill name.

````text
Read PLAN.md (sections 2 and 7) and schema/report.schema.json first. Use Plan mode first, then implement.

STEP 1. Read .bob/custom_modes.yaml if it exists (never overwrite blindly). Create it with EXACTLY this content (ASCII only, do not "improve" the regexes):

```yaml
customModes:
  - slug: uplift-impact-analyst
    name: Uplift Impact Analyst
    description: Judges what a code change will break. Cannot edit source code.
    whenToUse: Use to predict which callers, routes and tests a change breaks.
    roleDefinition: >-
      You are the Uplift Impact Analyst. You judge, for every code place a change could
      affect, whether it will break, might break, or is safe. You never edit source code or
      tests: your only writable folder is .uplift/. You never guess: every verdict cites the
      exact lines you read. Your final output is the file .uplift/verdicts.json.
    customInstructions: >-
      Procedure. 1) Run the engine graph command or MCP tool uplift_graph to produce
      .uplift/graph.json (candidates with snippets). 2) Group candidates by module. 3) In ONE
      turn, call spawn_subagent once per module so the modules are judged in parallel; give
      each subagent the candidate list for its module, the changed symbol, and the instruction
      to use the impact-verdict-rubric skill and read each caller's whole function. 4) Merge
      the subagent answers into .uplift/verdicts.json as a JSON array of objects with keys
      id, verdict, reason, fix. Use only the verdict values will_break, might_break, safe.
      5) Print a table of id, verdict, reason. Never read any file whose name ends in
      .expected.json.
    groups:
      - read
      - execute
      - mcp
      - skill
      - subagent
      - - edit
        - fileRegex: '(^|.*[/\\])\.uplift[/\\].*'
          description: Only files under .uplift/

  - slug: uplift-prover
    name: Uplift Prover
    description: Writes tests that prove a predicted break is real.
    whenToUse: Use after verdicts exist, to prove each will_break verdict with a failing test.
    roleDefinition: >-
      You are the Uplift Prover. For each will_break verdict you write one pytest file that
      states the OLD contract, passes on the code before the change and fails after it. You
      may only create or edit files under sample-app/tests/uplift_proofs/. You never mock
      the changed function, and you never change production code.
    customInstructions: >-
      Use the write-proof-test skill. First line of every proof file is a comment of the form
      "# uplift:item <id>" with the verdict id. Then run the engine proof-run command or MCP
      tool uplift_proof_run and report each proof as confirmed or unconfirmed, honestly.
    groups:
      - read
      - execute
      - mcp
      - skill
      - - edit
        - fileRegex: '(^|.*[/\\])sample-app[/\\]tests[/\\]uplift_proofs[/\\].*'
          description: Only proof tests

  - slug: uplift-migration-planner
    name: Uplift Migration Planner
    description: Reads a migration guide and produces a breaking-change catalog.
    whenToUse: Use to turn a vendor migration guide (PDF or markdown) into a catalog.
    roleDefinition: >-
      You are the Uplift Migration Planner. You read a dependency migration guide with
      document understanding and turn it into .uplift/catalog.json, then scan the repo for
      occurrences and write .uplift/migration-plan.md. You only write inside .uplift/.
    customInstructions: >-
      Use the migration-guide-reader skill. Every catalog entry quotes the exact guide
      heading it came from. Never invent a breaking change that is not in the guide.
    groups:
      - read
      - execute
      - mcp
      - skill
      - - edit
        - fileRegex: '(^|.*[/\\])\.uplift[/\\].*'
          description: Only files under .uplift/

  - slug: uplift-worker-users
    name: Uplift Worker Users
    description: Repairs the users module only.
    whenToUse: Use to fix broken code in sample-app/shop/users and nowhere else.
    roleDefinition: >-
      You are the Uplift worker for the users module. You may edit only files under
      sample-app/shop/users/. You make the smallest change that fixes each predicted break
      and you record anything that needs a change elsewhere as blocked instead of touching it.
    customInstructions: >-
      Read .uplift/verdicts.json, .uplift/proofs.json and, if present, .uplift/catalog.json
      and .uplift/occurrences.json. Fix only items whose file is in your module. Run the
      module tests and the matching proof tests with the sample-app virtual environment
      interpreter. Write .uplift/repair-users-<scenario>.json. Never read *.expected.json.
    groups:
      - read
      - execute
      - - edit
        - fileRegex: '(^|.*[/\\])sample-app[/\\]shop[/\\]users[/\\].*'
          description: Only the users module

  - slug: uplift-worker-orders
    name: Uplift Worker Orders
    description: Repairs the orders module only.
    whenToUse: Use to fix broken code in sample-app/shop/orders and nowhere else.
    roleDefinition: >-
      You are the Uplift worker for the orders module. You may edit only files under
      sample-app/shop/orders/. You make the smallest change that fixes each predicted break
      and you record anything that needs a change elsewhere as blocked instead of touching it.
    customInstructions: >-
      Read .uplift/verdicts.json, .uplift/proofs.json and, if present, .uplift/catalog.json
      and .uplift/occurrences.json. Fix only items whose file is in your module. Run the
      module tests and the matching proof tests with the sample-app virtual environment
      interpreter. Write .uplift/repair-orders-<scenario>.json. Never read *.expected.json.
    groups:
      - read
      - execute
      - - edit
        - fileRegex: '(^|.*[/\\])sample-app[/\\]shop[/\\]orders[/\\].*'
          description: Only the orders module

  - slug: uplift-worker-payments
    name: Uplift Worker Payments
    description: Repairs the payments module only.
    whenToUse: Use to fix broken code in sample-app/shop/payments and nowhere else.
    roleDefinition: >-
      You are the Uplift worker for the payments module. You may edit only files under
      sample-app/shop/payments/. You make the smallest change that fixes each predicted break
      and you record anything that needs a change elsewhere as blocked instead of touching it.
    customInstructions: >-
      Read .uplift/verdicts.json, .uplift/proofs.json and, if present, .uplift/catalog.json
      and .uplift/occurrences.json. Fix only items whose file is in your module. Run the
      module tests and the matching proof tests with the sample-app virtual environment
      interpreter. Write .uplift/repair-payments-<scenario>.json. Never read *.expected.json.
    groups:
      - read
      - execute
      - - edit
        - fileRegex: '(^|.*[/\\])sample-app[/\\]shop[/\\]payments[/\\].*'
          description: Only the payments module

  - slug: uplift-worker-core
    name: Uplift Worker Core
    description: Repairs app wiring, config, admin, notifications and requirements.
    whenToUse: Use for fixes outside the users, orders and payments modules.
    roleDefinition: >-
      You are the Uplift worker for everything the module workers cannot touch: the shop
      package top-level files, shop/admin, shop/notifications and sample-app/requirements.txt.
      You make the smallest change that fixes each predicted break.
    customInstructions: >-
      Read .uplift/verdicts.json, .uplift/proofs.json and, if present, .uplift/catalog.json
      and .uplift/occurrences.json. Fix only items in your paths. Run the tests with the
      sample-app virtual environment interpreter. Write .uplift/repair-core-<scenario>.json.
      Never read *.expected.json.
    groups:
      - read
      - execute
      - - edit
        - fileRegex: '(^|.*[/\\])sample-app[/\\](requirements\.txt|shop[/\\][^/\\]+\.py|shop[/\\]admin[/\\].*|shop[/\\]notifications[/\\].*)$'
          description: Top-level shop files, admin, notifications, requirements

  - slug: uplift-verifier
    name: Uplift Verifier
    description: Re-runs everything, checks conventions, writes release notes and the final report.
    whenToUse: Use after repairs, to verify and to assemble the final report.
    roleDefinition: >-
      You are the Uplift Verifier. You re-run the full sample-app test suite after repairs,
      report passed and failed counts honestly, write release notes, and assemble the final
      report. You may only write under reports/ and .uplift/.
    customInstructions: >-
      If tests still fail, say which and why; never mark verify as done unless every test
      passes. If .uplift/conventions.json exists, check every line the workers added against
      it and record checkedLines, violations and retried in the report's conventions.compliance.
    groups:
      - read
      - execute
      - mcp
      - - edit
        - fileRegex: '(^|.*[/\\])(reports|\.uplift)[/\\].*'
          description: Only reports and .uplift

  - slug: uplift-convention-scanner
    name: Uplift Convention Scanner
    description: Learns how this repo is written and records it as evidence.
    whenToUse: Use before repairs, so workers can match the repo's own style.
    roleDefinition: >-
      You are the Uplift Convention Scanner. You read 8 to 12 representative files and record
      the repo's naming, import, error-handling and file-layout conventions as evidence, never
      as taste. You only write inside .uplift/.
    customInstructions: >-
      Use the repo-conventions skill. Each finding cites at least two files. If a pattern is
      not consistent write "mixed". Output .uplift/conventions.json.
    groups:
      - read
      - execute
      - skill
      - - edit
        - fileRegex: '(^|.*[/\\])\.uplift[/\\].*'
          description: Only files under .uplift/
```

STEP 2. Run the checker (install PyYAML into any venv first: `pip install pyyaml`): `python scripts/check_modes.py .bob/custom_modes.yaml`. It must print "9 - parse ok" and "mismatches: 0". Paste its output.

STEP 3. Create the three skills with EXACTLY these contents:

.bob/skills/impact-verdict-rubric/SKILL.md
```markdown
---
name: impact-verdict-rubric
description: Judge whether a changed function, route or dependency breaks one of its dependents. Use when deciding will_break, might_break or safe for an affected place.
---

# Impact verdict rubric

You are given: the change (a patch or a dependency upgrade), one changed symbol with its changeType and hints, and one dependent (a "candidate": file, function, code snippet). Decide what happens to the dependent.

## Procedure
1. Read the change. Write one plain sentence: "Before, X. After, Y." (for example: "Before, get_user raised NotFoundError for an unknown id. After, it returns None.")
2. Open the dependent's FULL function in its file (not only the snippet). Find every line that uses the changed symbol's result or behaviour.
3. Ask: does this code rely on the OLD behaviour? Check each of these traps:
   - raise vs return None: code that no longer sees an exception, or dereferences None (AttributeError, TypeError).
   - try/except that used to catch the old exception and now silently continues.
   - units and scale (dollars vs cents), rounding, ordering, defaults, mutability.
   - truthiness: `if result:` treats 0, "" and None the same.
   - HTTP: an exception handler used to turn the exception into a status code; a response_model that now receives None or a different shape (validation error, 500) or a route whose status or body changes.
   - a caller that only calls the function for its side effect of raising (existence check).
4. Decide:
   - will_break: you can name the exact line and the exact wrong outcome for a realistic input.
   - might_break: it depends on data or a condition you cannot confirm from the code.
   - safe: it does not use the changed behaviour, or it already handles the new behaviour (for example an explicit `is None` check).
5. Rules:
   - The same signature does NOT mean safe. Python has no compiler to catch behaviour changes.
   - When unsure, choose might_break. Never choose will_break without naming the line and the outcome.
   - Never mark safe just because a test exists; tests may not cover the changed path.
   - A route (contract) whose status code or body changes for the same request is will_break.
6. Give a one-line reason (mention the line) and a one-line fix (the smallest change).

## Output (one JSON object per candidate)
{"id": "<candidate id>", "verdict": "will_break|might_break|safe", "reason": "<one line>", "fix": "<one line, empty for safe>"}

## Never
- Never edit files. Never invent callers that are not in the candidate list. Never read *.expected.json.
```

.bob/skills/write-proof-test/SKILL.md
```markdown
---
name: write-proof-test
description: Write a pytest test that proves a predicted break is real. Use after an impact verdict of will_break, to create a test that passes before the change and fails after it.
---

# Write a proof test

A proof test states the OLD contract of the dependent and is expected to PASS on the code before the change and FAIL on the code after the change.

## Rules
1. One file per predicted break, in sample-app/tests/uplift_proofs/, named test_<module>_<slug>.py where <module> is the module of the affected item (users, orders, payments, notifications, admin or core), for example test_orders_create_order_unknown_user.py. Parallel repair workers run only their own module's proofs, so the module prefix is required. The folder has an empty __init__.py.
2. First line of every file: `# uplift:item <candidate id>` (the id from verdicts.json).
3. The test exercises the REAL dependent (the function or the HTTP route through make_client). Never mock the changed function. Never patch or monkeypatch away the changed behaviour.
4. The test asserts the behaviour the dependent had before the change, for the situation that the change alters (for example: an unknown user id is rejected).
5. No sleeps, no randomness, no network, no file writes outside pytest's tmp_path. Use the fake data that already exists in the app.
6. Keep it under 25 lines. A docstring states the OLD contract in one sentence.
7. Never edit production code or any other test. You may only create files in sample-app/tests/uplift_proofs/.

## Template
```python
# uplift:item shop/orders/service.py#create_order
import pytest

from shop.errors import ValidationError
from shop.orders.schemas import OrderIn
from shop.orders.service import create_order


def test_create_order_rejects_unknown_user():
    """OLD contract: an order for a user that does not exist is rejected with ValidationError."""
    with pytest.raises(ValidationError):
        create_order(OrderIn(user_id=999, items=[1.0]))
```
For a route, build the client with `from tests.conftest import make_client` and the route module's router, then assert the HTTP status and body.

## After writing
Run the engine proof runner (MCP tool uplift_proof_run or `uplift proof-run ...`). A proof that does not fail on head is "unconfirmed": report it as such, and do not weaken the test to force a result.
```

.bob/skills/migration-guide-reader/SKILL.md
```markdown
---
name: migration-guide-reader
description: Turn a dependency migration guide (PDF or markdown) into a machine-checkable breaking-change catalog. Use when planning a library upgrade from its official migration guide.
---

# Migration guide reader

Read the guide with document understanding. Produce .uplift/catalog.json: a JSON array of catalog entries.

## Entry format
{"id": "<short-id>", "title": "<what changed>", "kind": "api_removed|api_changed|behavior_changed|syntax",
 "guideSection": "<the EXACT heading in the guide where this is described>",
 "detect": {"type": "call|identifier|import|regex", "pattern": "<pattern>"},
 "replacement": "<what to write instead>"}

## Rules
1. Only include changes that the guide actually states. Quote the section heading exactly. Never invent a breaking change.
2. Only include changes that could plausibly affect an ordinary web app that uses the library (skip niche features the app cannot be using).
3. detect must be machine-checkable:
   - import: a line-level pattern such as "from examplelib import OldName"
   - call: the called function or method name, for example "old_method"
   - identifier: a bare name
   - regex: a Python regular expression matched line by line (escape backslashes for JSON)
4. kind: api_removed (gone), api_changed (renamed or new signature), behavior_changed (same code, different result), syntax.
5. Aim for 8 to 15 entries. Prefer precise detect patterns over broad ones; a broad pattern creates false positives.
6. Also write .uplift/migration-plan.md: per module, the occurrences the scan found, and the order to fix them.

## Example of the FORMAT only (a made-up library; do not copy)
{"id": "ex-rename-fetch", "title": "fetch_all renamed to load_all", "kind": "api_changed", "guideSection": "Renamed functions",
 "detect": {"type": "call", "pattern": "fetch_all"}, "replacement": "load_all()"}
```

STEP 4. In Bob's mode picker confirm that all 9 "Uplift ..." modes appear (they hot-reload). Tell me which do not.
STEP 5. Confirm which of these are true in this Bob build and report them (this is research, do not change anything): (a) the `subagent` group gives a `spawn_subagent` tool; (b) multiple spawn_subagent calls in one turn run in parallel; (c) whether custom mode slugs can be named in `allowedSubagents` (probably not, presets are built in).

DONE WHEN: check_modes.py passes, 9 modes visible, 3 skill files exist.
Commit: [bob A1] add Uplift modes and skills
````


(The ninth mode, `uplift-convention-scanner`, is already in the YAML. Its skill `repo-conventions` is created in task A11.)

---

## A2. Impact Analyst on S1  (mode `uplift-impact-analyst`, about 2 coins; needs sample-app from B1 and the graph from B4)

Output format, so nothing is ambiguous. `.uplift/verdicts.json` is a JSON array:

```json
[
  {"id": "shop/orders/invoice.py#build_invoice", "verdict": "will_break",
   "reason": "Reads user.email on get_user's result, which is now None for an unknown user (line 8).",
   "fix": "Check for None and raise NotFoundError, as the rest of the repo does."}
]
```

````text
Switch to the uplift-impact-analyst mode. Branch: scenario/s1-null-user (run `git switch scenario/s1-null-user`; the patch is already applied there).

Change under analysis: sample-app/scenarios/s1-null-user.patch. Read it and state in one sentence what changed ("Before, X. After, Y.").

1. Get the candidate list: MCP tool uplift_graph, or `uplift graph --repo sample-app --patch sample-app/scenarios/s1-null-user.patch --applied --out .uplift/graph.json`. If the engine is not built yet, find every reference to the changed function yourself and say clearly in your answer that the graph was produced by you, not by the engine.
2. Group the candidates by module. In ONE turn, call spawn_subagent once per module so the modules are judged in parallel. Give each subagent exactly this instruction (fill in the placeholders): "You are judging module <M> for Uplift. Change: <one sentence>. Changed symbol: <id> (<changeType>, hints: <hints>). Candidates: <the candidate objects for this module, including snippets>. For each candidate open the whole function in its file, apply the impact-verdict-rubric skill, and return ONLY a JSON array of {id, verdict, reason, fix}. Do not edit files and do not read any *.expected.json file."
3. Merge the subagent answers into .uplift/verdicts.json (array format above). Include the safe ones. Every candidate id from graph.json must appear exactly once.
4. If `uplift report` exists: `uplift report --graph .uplift/graph.json --verdicts .uplift/verdicts.json --scenario s1-null-user --title "get_user returns None instead of raising" --bob-modes uplift-impact-analyst --out reports/s1-null-user.json` then `uplift validate reports/s1-null-user.json`.
5. Print a table: id, verdict, reason.

DONE WHEN: .uplift/verdicts.json has one entry per graph candidate; the validate command (if run) prints PASS. You edited nothing outside .uplift/ and reports/ is untouched unless step 4 ran through the engine.
Commit: [bob A2] impact verdicts for S1
````


---

## A3. Prover on S1  (mode `uplift-prover`, about 3 coins; needs A2)

Example proof (tested: passes on base, fails on head):

```python
# uplift:item shop/orders/service.py#create_order
import pytest

from shop.errors import ValidationError
from shop.orders.schemas import OrderIn
from shop.orders.service import create_order


def test_create_order_rejects_unknown_user():
    """OLD contract: an order for a user that does not exist is rejected with ValidationError."""
    with pytest.raises(ValidationError):
        create_order(OrderIn(user_id=999, items=[1.0]))
```

````text
Switch to the uplift-prover mode. Use the write-proof-test skill. Branch: scenario/s1-null-user.

Input: .uplift/verdicts.json and sample-app/scenarios/s1-null-user.patch.
For EVERY item whose verdict is will_break (including routes and indirect items) create ONE file in sample-app/tests/uplift_proofs/ named test_<module>_<slug>.py, where <module> is the module of the affected item (users, orders, payments, notifications, admin or core) for example test_orders_create_order_unknown_user.py (create an empty __init__.py in that folder first if missing). Each file:
- starts with `# uplift:item <id>`,
- states the OLD contract for the situation the change alters (for S1: "an unknown user id is rejected"; for a route: "GET /users/999 returns 404"),
- exercises the real code (route tests use `from tests.conftest import make_client` and the route module's router),
- never mocks get_user.
Then run, BEFORE any repair: MCP tool uplift_proof_run or `uplift proof-run --repo sample-app --patch sample-app/scenarios/s1-null-user.patch --applied --proofs sample-app/tests/uplift_proofs --out .uplift/proofs.json`.
If the engine command does not exist yet, do the same by hand: run the proofs on the current tree (head; expect failures) and on a temp copy with the patch reverse-applied (base; expect passes) using the demo app's interpreter, and write .uplift/proofs.json as {"proofs": [{"item", "testFile", "passesOnBase", "failsOnHead", "status"}]}.
Report honestly: a proof that does not fail on head is "unconfirmed"; do not weaken it to force a result. Also list the will_break items you could NOT prove and why.

DONE WHEN: sample-app/tests/uplift_proofs/ has one file per will_break item; .uplift/proofs.json exists; you paste the table of item, status.
Commit: [bob A3] proof tests for S1
````


---

## A4. Predict and prove S2, the subtle change  (about 4 coins)

````text
Run the whole predict and prove steps again for scenario S2 on branch scenario/s2-cents, exactly as in tasks A2 and A3 (mode uplift-impact-analyst, then mode uplift-prover), with:
- change: sample-app/scenarios/s2-cents.patch (payment amounts change from float dollars to integer cents in charge.py; nothing raises, no test fails)
- the situation to judge: "a dependent receives a Payment produced by the patched charge()"; for each dependent decide whether it treats the amount as dollars (will_break) or is unit-agnostic (safe, for example code that only stores or passes it along)
- outputs: .uplift/verdicts.json, .uplift/proofs.json (on the S2 branch)
Do NOT read any *.expected.json. When done, list your verdicts and the ones you are unsure about. The comparison with ground truth happens in task A8.
If you see a weakness in the rubric, propose an edit to .bob/skills/impact-verdict-rubric/SKILL.md (show the diff, do not apply it).
DONE WHEN: verdicts.json and proofs.json exist on scenario/s2-cents.
Commit: [bob A4] predict and prove S2
````


Apply a rubric edit only if it generalises and does not mention the demo app (fix prompt: "rewrite this rule so it works for any codebase").

---

## A5. Migration Planner, document understanding  (mode `uplift-migration-planner`, about 3 coins)

First, by hand: open https://docs.pydantic.dev/latest/migration/, print to PDF, save as `docs/migration/pydantic-v2-migration-guide.pdf`, and add the print date to SOURCES.md. Branch: `scenario/s3-pydantic2`.

````text
Switch to the uplift-migration-planner mode. Use the migration-guide-reader skill. Branch: scenario/s3-pydantic2 (its requirements.txt already upgrades pydantic and fastapi).

0. Create the Pydantic v2 interpreter for this branch (the default sample-app/.venv is Pydantic v1, where nothing fails): `python -m venv sample-app/.venv-v2` then `sample-app/.venv-v2/Scripts/python -m pip install -r sample-app/requirements.txt` (this branch's requirements already upgrade pydantic and fastapi). It is git-ignored. Confirm with `sample-app/.venv-v2/Scripts/python -c "import pydantic; print(pydantic.VERSION)"`: it must print 2.x.
Read docs/migration/pydantic-v2-migration-guide.pdf (document understanding: read the PDF itself).
1. Write .uplift/catalog.json following the skill: 8 to 15 entries covering what can affect a FastAPI app on Pydantic v1 (removed or renamed APIs, moved imports such as BaseSettings, validator changes, Optional-field semantics, Config class changes, custom root types, renamed Field arguments, constrained types, method renames, coercion changes). Each entry has the exact guide heading in guideSection and a precise detect pattern. Only changes the guide states.
2. Run MCP tool uplift_migrate_scan or `uplift migrate-scan --repo sample-app --catalog .uplift/catalog.json --out .uplift/occurrences.json`.
3. Record the BEFORE counts per module with the v2 interpreter: `uplift upgrade-test --repo sample-app --current --app-python sample-app/.venv-v2/Scripts/python.exe --out .uplift/baseline-s3-pydantic2.json` and include the per-module failure counts in the plan.
4. Write .uplift/migration-plan.md: per module (users, orders, payments, core): occurrences, failing tests, order of fixes; say which catalog entries had zero occurrences.
5. Quote the guide heading for every catalog entry so a reader can check us.
DONE WHEN: catalog.json has 8+ entries with guideSection headings; occurrences.json and baseline-s3-pydantic2.json exist (the baseline shows failures); migration-plan.md exists.
Commit: [bob A5] pydantic v2 catalog from guide
````


---

## A6. Repair with parallel workers  (Plan mode first, about 8 coins across four tasks)

Work on the scenario's branch. Open **three Bob tasks at once**, one per module worker, plus a fourth for `uplift-worker-core` if any affected item lives outside the three modules (app wiring, config, admin, notifications, requirements). Each mode may edit only its own paths (Bob enforces this), so they cannot collide. All commit to the same scenario branch.

**Step 0, once, before opening the worker tasks** (any Agent-mode task, or by hand): record ONE shared baseline so parallel workers do not measure each other. `uplift upgrade-test --repo sample-app --current --app-python <PY> --out .uplift/baseline-<id>.json` where <PY> is `sample-app/.venv/Scripts/python.exe` for S1 and S2 and `sample-app/.venv-v2/Scripts/python.exe` for S3 (with `--current` it just reports per-module test counts in that interpreter). Commit it.

**Interpreters.** S1 and S2 tests run with `sample-app/.venv`. **S3 must run with `sample-app/.venv-v2`** (Pydantic 2); running S3 on the v1 interpreter would show everything passing and make the numbers meaningless.

Git tip: workers commit only their own folder: `git add sample-app/shop/<module> && git commit -m "[bob A6] <module> repair for <scenario>"`. If git reports an index lock error because another worker is committing, wait 5 seconds and retry.

Repair result file format, `.uplift/repair-<module>-<scenario>.json`:

```json
{"module": "orders", "worker": "uplift-worker-orders", "scenario": "s1-null-user",
 "filesChanged": ["sample-app/shop/orders/service.py"], "fixesApplied": 2,
 "testsBefore": {"passed": 20, "failed": 2}, "testsAfter": {"passed": 22, "failed": 0},
 "blocked": []}
```

````text
Switch to the mode uplift-worker-<MODULE>. You may edit ONLY sample-app/shop/<MODULE>/ (Bob enforces it; for uplift-worker-core the allowed paths are the ones listed for it in PLAN.md section 7).

Scenario: <s1-null-user | s2-cents | s3-pydantic2>. Branch: scenario/<id>.
Inputs: .uplift/verdicts.json and .uplift/proofs.json (S1, S2), or .uplift/occurrences.json and .uplift/catalog.json (S3). If .uplift/conventions.json exists, follow it exactly. Do not read any *.expected.json.

1. List the items in your module with verdict will_break or might_break (S3: the occurrences in your module).
2. testsBefore = your module's numbers from .uplift/baseline-<id>.json. Interpreter <PY>: sample-app/.venv/Scripts/python for S1 and S2, sample-app/.venv-v2/Scripts/python for S3.
3. Fix each item with the SMALLEST change. For S1 and S2 fix the dependent (not the changed function). For S3 apply the catalog replacement exactly; do not refactor.
4. Run ONLY your module's tests and your module's proofs, AFTER the fix: `<PY> -m pytest sample-app/tests/<MODULE> sample-app/tests/uplift_proofs/test_<MODULE>_*.py -q --continue-on-collection-errors` (never the whole proofs folder: other workers' proofs are still failing while they work). Every proof for your module must now pass. For uplift-worker-core the module tests are tests/notifications and tests/uplift_proofs/test_notifications_*.py, test_admin_*.py and test_core_*.py; for S3 the core worker also adds `pydantic-settings` to sample-app/requirements.txt and installs it into .venv-v2.
5. Write .uplift/repair-<MODULE>-<scenario>.json in the format above. If a fix needs a change outside your folder, do NOT make it: list it under "blocked" with the reason.
6. Commit only your folder and your repair file.
DONE WHEN: your repair json exists; testsAfter.failed is 0 for your module (or blocked items explain why not).
Commit: [bob A6] <MODULE> repair for <scenario>
````


Run S1 repairs first (small) and check the result, then S3, the big parallel demo. Screenshot every task; they are the strongest "parallel tasks and subagents" evidence.

---

## A7. Verifier and release notes  (mode `uplift-verifier`, about 2 coins)

````text
Switch to the uplift-verifier mode. Scenario: <id>, branch scenario/<id>.

1. Run the full demo-app suite with the change applied and all repairs applied: `sample-app/.venv/Scripts/python -m pytest sample-app -q` (S3: with the Pydantic 2 interpreter, `sample-app/.venv-v2/Scripts/python`). Record passed and failed.
2. Read every .uplift/repair-*-<scenario>.json, .uplift/verdicts.json, .uplift/proofs.json.
3. Write reports/<scenario>.release-notes.md: what changed, what we predicted, what was proven, what was fixed (per module), what is still open, and the honest numbers.
4. Assemble the final report with MCP tool uplift_report or `uplift report --graph .uplift/graph.json --verdicts .uplift/verdicts.json --proofs .uplift/proofs.json --repairs ".uplift/repair-*-<id>.json" --scenario <id> --title "<title>" --bob-modes uplift-impact-analyst,uplift-prover,uplift-worker-users,uplift-worker-orders,uplift-worker-payments,uplift-worker-core,uplift-verifier --verified --out reports/<id>.json` (add `--catalog .uplift/catalog.json` for S3; drop `--verified` if any test still fails). Run `uplift validate reports/<id>.json`.
5. Be honest: if tests still fail, say which and why, and leave verify as pending.
DONE WHEN: reports/<id>.json validates; release notes exist; you paste the passed/failed counts.
Commit: [bob A7] verify and release notes for <id>
````


---

## A8. Accuracy evaluation  (about 3 coins, the credibility task)

First, by hand: in `.bobignore` comment out the line `sample-app/scenarios/*.expected.json` (Bob could not read the ground truth until now; that is the point). Commit `[A8] reveal ground truth for evaluation`. After the task, uncomment it again and commit `[A8] hide ground truth again`.

The math (tested): true positives are places we predicted broken that ground truth marks broken; false positives are predicted broken but ground truth says safe; false negatives are ground truth broken but we said safe or missed.

```python
# ---------------- accuracy ----------------
def accuracy(predicted_broken: set[str], truth_broken: set[str], truth_all: set[str]) -> dict:
    tp = len(predicted_broken & truth_broken)
    fp = len(predicted_broken - truth_broken)
    fn = len(truth_broken - predicted_broken)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(precision, 2), "recall": round(recall, 2), "truePositives": tp,
            "falsePositives": fp, "falseNegatives": fn}
```

````text
Read sample-app/scenarios/*.expected.json (ground truth) and the reports (reports/s1-null-user.json and reports/s2-cents.json on their scenario branches; check them out with `git show scenario/<id>:reports/<id>.json`).

1. For each of S1 and S2: predicted_broken = ids whose verdict is will_break or might_break (candidates only, not changed symbols); truth_broken = ids whose expected is will_break; compute truePositives, falsePositives, falseNegatives, precision and recall with the accuracy() function above (create scripts/accuracy.py with it, plus a CLI: `python scripts/accuracy.py --report R --truth T`). Missing candidates (in truth, absent from the report) count as false negatives.
2. Write .uplift/eval.md: a table per scenario (id, predicted, truth, correct?), the numbers, and EVERY miss with its cause. Add per scenario: predicted vs confirmed vs fixed.
3. Fill metrics.accuracy in each report ({precision, recall, truePositives, falsePositives, falseNegatives}); re-validate with `uplift validate`.
4. S3 has no expected.json: report the real Pydantic v2 test failures per module (before) and after the repairs, from .uplift/upgrade-before.json and the repair files.
5. Be unflattering: never adjust the ground truth to fit the predictions.
DONE WHEN: .uplift/eval.md exists with numbers for S1, S2 and S3; the reports have metrics.accuracy.
Commit: [bob A8] accuracy evaluation
````


---

## A9. Publish evidence  (about 1 coin)

````text
Switch to main. For each scenario id run `git checkout scenario/<id> -- reports/<id>.json reports/<id>.release-notes.md`, and save that scenario's work files under evidence/<id>/ WITHOUT overwriting the other scenarios: `git show scenario/<id>:.uplift/verdicts.json > evidence/<id>/verdicts.json` (same for proofs.json, catalog.json, occurrences.json, conventions.json and every repair-*-<id>.json that exists). Copy the final reports/*.json to evidence/ and dashboard/reports/ (create the folders if needed), plus .uplift/eval.md to evidence/eval.md and to dashboard/reports/eval.md. Every report must have provenance.generatedBy = "bob" (or "engine" for graph-only runs) and provenance.bobModes filled. Run `uplift validate evidence/*.json`. Do not touch dashboard/reports/index.json (Member C owns it) but tell C the scenario ids and titles.
DONE WHEN: evidence/ has three reports (s1-null-user, s2-cents, s3-pydantic2) that validate, and evidence/eval.md exists.
Commit: [bob A9] publish evidence
````


---

## A11. Convention Scanner  (F16, mode `uplift-convention-scanner`, about 3 coins; do after A6 works)

The mode is already in custom_modes.yaml; this task adds its skill and runs it.

````text
Read PLAN.md (F16). Create .bob/skills/repo-conventions/SKILL.md with EXACTLY this content:

```markdown
---
name: repo-conventions
description: Learn the coding conventions a repository already follows (naming, imports, error handling, file layout) and record them with evidence. Use before repairing code so the fixes match the repo's own style.
---

# Repo conventions

Goal: describe how THIS repo is written, as evidence, not taste.

## Procedure
1. Pick 8 to 12 representative files across modules: a service, a route file, a schema file, the errors file, requirements.txt, and 2 to 3 tests.
2. For each dimension below, write what you observed and cite at least TWO files as evidence. If the repo is not consistent, write "mixed" and cite one example of each style.
   - naming: variables and functions, classes, files and folders
   - imports: absolute vs relative, `from x import y` vs `import x`, ordering
   - errorHandling: raise typed exceptions vs return None vs result objects; which exception classes exist and where they live
   - fileLayout: one concern per module? where tests live and how they are named
3. Output .uplift/conventions.json: {"naming": "...", "imports": "...", "errorHandling": "...", "fileLayout": "...", "evidenceFiles": ["path", "..."]}.

## Never
- Never edit source files. Never state a convention you cannot cite.
```

Then switch to the uplift-convention-scanner mode, use the repo-conventions skill on sample-app (branch main), and write .uplift/conventions.json: {"naming", "imports", "errorHandling", "fileLayout", "evidenceFiles": [...]}, each finding citing at least two files.
DONE WHEN: the skill exists; conventions.json has four findings and 8+ evidence files; each finding cites files.
Commit: [bob A11] convention scanner skill and run
````


---

## A12. Convention-aware repair and compliance check  (F16, about 3 coins)

````text
Read .uplift/conventions.json and PLAN.md (F16).
1. In .bob/custom_modes.yaml (read first, edit carefully, re-run `python scripts/check_modes.py .bob/custom_modes.yaml`): append to the customInstructions of the four worker modes: "Before fixing, read .uplift/conventions.json if it exists and follow it exactly; a fix that is correct but does not match the repo's conventions is a failed fix."
2. Same file, uplift-verifier customInstructions already describe the compliance check; make it concrete: after the tests pass, list the lines the workers added (git diff between the scenario patch commit and HEAD), check each line against conventions.json, count checkedLines and violations; on a violation report the worker and the rule, allow exactly ONE retry, and write {"checkedLines", "violations", "retried"} into the report's conventions.compliance plus the conventions object itself (naming, imports, errorHandling, fileLayout, evidenceFiles).
3. Side-by-side evidence for the demo. On a scratch branch from scenario/s1-null-user before repairs (`git switch -c scratch/generic scenario/s1-null-user`): run ONE worker (uplift-worker-orders) with the instruction to IGNORE .uplift/conventions.json; save its diff as docs/convention-demo/generic.diff. Then on another scratch branch run the same worker WITH conventions; save docs/convention-demo/convention-aware.diff. Write docs/convention-demo/README.md explaining what differs (for example: raises NotFoundError like the rest of the repo vs returns None). Return to main and commit only docs/convention-demo/ there.
DONE WHEN: check_modes.py still passes; docs/convention-demo/ has generic.diff, convention-aware.diff and README.md.
Commit: [bob A12] convention-aware workers and verifier check
````


---

## A13. Fix prompts  (remaining coins)

Failures found by `python scripts/verify.py --run` or by reviewing Bob's output. Write the exact fix prompt and paste it into the mode that owns the file. Typical issues: a mode file that Bob silently dropped (run check_modes.py), a worker that edited outside its folder (Bob blocks it: record as blocked), a proof that is unconfirmed, verdicts missing for some candidate ids.

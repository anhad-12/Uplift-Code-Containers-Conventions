# How to use the prompts

Each file is a list of ready-to-paste prompts for Bob IDE, in the order to run them:

- `A-brain.md`: Bob modes, skills, verdicts, proofs, repairs, accuracy, conventions
- `B-engine.md`: demo app, scenario patches, code graph, proof runner, CLI, CI, MCP server
- `C-face.md`: Dash dashboard, deploy, real-report swap

## What is in a prompt

Every prompt is a boxed block you paste into a **new Bob task**. It contains the goal, the exact files or formats, **tested reference code**, the expected results, and a **Done when** command. The reference code was run against a scratch copy of the demo app before it went into these files Bob creates and adapts the real files inside the repo, and Bob's session summaries are what count as Bob usage.

Things that testing already caught, so Bob does not have to rediscover them:
- `httpx` must be `0.27.2` (0.28 breaks Starlette's TestClient).
- `mcp` must be `<2` (2.x renamed `FastMCP`).
- pytest needs `--continue-on-collection-errors`, and collection errors show up in junit with an empty classname.
- Patches are generated with `difflib` (LF only); Windows git can produce CRLF patches.
- The dashboard needs its own copy of the schema (Render deploys only `dashboard/`).
- Bob mode files: shell access is `execute`, not `command`; verify with `python scripts/check_modes.py`.

## Workflow for one task
1. In Bob IDE, confirm you are on the hackathon account (`ibm-coding-challenge-uat`, us-east) and that Python is 3.11 or 3.12 (`PYTHONUTF8=1` set on Windows).
2. Open a **new task**, pick the mode the prompt names (or Agent mode), paste the whole boxed prompt. Use Plan mode first when the prompt says so.
3. Review the diff in Source Control. Skim it; if something feels off, iterate in the same task.
4. Run the **Done when** command yourself and read the output. Do not accept "done" without it.
5. Screenshot the task summary (Tasks > select > click header) into `bob_sessions/`, add a row to `bob_sessions/LOG.md`.
6. Commit with the `[bob X#]` prefix from the prompt.
7. Repo root: `python scripts/verify.py` shows what is done and what is missing. If something fails, paste the output to your reviewer and ask for a **fix prompt**, then paste that into the same Bob task.

## Order across the team
- **B1 then B2 first**: they unblock everyone. After B2, B uncomments the ground-truth line in `.bobignore`.
- **A0 to A1 and C1 to C2** need nothing from B: start them at the same time as B1.
- Then A2 onward as B's engine lands (B3 to B7). C works from the mock reports the whole time.
- The two differentiators (A11/A12 conventions, B13 Docker, C10 dashboard for both) are built **after** the Sep 27 10 AM checkpoint is green — they are layers within Impact/Migrate mode, not optional bolt-ons, and they are mandatory demo moments (PLAN.md sections 3, 14, 15). Cut them only as a last resort and, if cut, drop them from the pitch and statements too (PLAN.md section 12).

See PLAN.md sections 8 and 9 for the timeline, sections 14-18 for the demo script, statements, checklist and the local-reproduction runbook. Never write "blast radius" in user-facing output (a rival is named BlastRadius); say "what a change will break" or "change impact".

## If Bob's output is wrong
Do not fix core code by hand or with another tool. Give Bob the failing output and ask it to fix it in the same task. That keeps the Bob usage real and the session summary honest.

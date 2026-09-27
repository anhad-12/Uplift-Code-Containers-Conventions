# Problem & Solution

## Problem

Every code review hides a silent question: *what else will this change break?*
A developer changes `get_user` to return `None` instead of raising an error.
The diff looks clean. The tests that exist all pass. But five callers across three
modules silently depend on the raise — and none of them have tests.
The bug ships. Production breaks.

The same gap exists at the dependency level: upgrading Pydantic v1 to v2 touches
dozens of call sites, and there is no tool that tells you which ones will fail
*before* you merge.

## Solution

**Uplift** closes the loop in four steps:

1. **Predict** — a deterministic code-graph engine traces every caller, route and
   test reachable from the changed symbol (up to 3 hops). Docker layer impact is
   computed as part of Impact Mode: a code change that triggers a layer rebuild
   shows up as an infra-impact node. Bob judges each candidate with a behaviour-
   change verdict (will_break / might_break / safe) using parallel subagents — one
   per module — so the analysis is fast and consistent.

2. **Prove** — for every `will_break` verdict Bob writes a failing pytest that
   states the old contract, passes on the code before the patch, and fails after.
   This is not a generated unit test; it is a proof that the break is real.

3. **Repair** — sandboxed Bob workers (one per module, with file-permission walls)
   fix only the code they own. Convention-aware fixes are part of Migrate Mode:
   a Convention Scanner reads the repo's naming, import and error-handling patterns
   first, so fixes match the codebase style, not generic AI style.

4. **Verify** — tests are re-run. A before/after count is recorded. The accuracy
   of the predictions is measured against a hidden ground-truth file
   (`sample-app/scenarios/*.expected.json`, blocked from Bob via `.bobignore`)
   and every miss is named in `evidence/eval.md`.

**Two modes, one engine:**
- *Impact Mode* — a code patch; output is a change-impact graph with risk score,
  verdicts, proofs, repairs and optional Docker layer analysis.
- *Migrate Mode* — a dependency upgrade; output adds a breaking-change catalog,
  per-module before/after test counts, convention-aware fixes and release notes.

The results are served through a Dash dashboard on a live URL, and posted as a
PR comment by a GitHub Action on every pull request.

---

*Replace this skeleton with the final polished statement before submission.
See PLAN.md sections 16 and 17 for the writing guide and pre-submission checklist.*

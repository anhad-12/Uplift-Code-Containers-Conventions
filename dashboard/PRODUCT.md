# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, held equally (confirmed with the user, not inferred):

1. **Hackathon judges and lablab voters** — open a live URL cold, with zero prior context, during the IBM Bob 2.0 Hackathon judging window (Sep 25-27, 2026). They decide in a few minutes per submission. They need the risk, the proof, and the fix to be legible on first scroll, with no explanation required.
2. **Engineering teams reviewing a real pull request** — a developer or reviewer who just opened a PR and wants to know, before merging, what it will break across code, tests, API contracts, and the Docker build, and whether the fix already applied is trustworthy. This audience returns repeatedly and cares about density, speed, and trust over spectacle.

Design must satisfy the cold 2-minute read and hold up under repeated, task-focused use — no single mode (pure Persuade or pure Operate) should be chosen at the other's expense.

## Product Purpose

Uplift predicts what a code change will break — in code, tests, API contracts, and Docker layers — before it merges, proves each prediction with a test that fails on the new code and passes on the old, then repairs it using sandboxed IBM Bob 2.0 workers that match the repo's own conventions. This dashboard is Uplift's visual proof surface: it shows the impact graph, the proofs, the repairs, convention compliance, and an honest accuracy scorecard (including what was missed) for a given change or dependency migration.

Success for this surface = a viewer with no prior context can, within one scroll, state what broke, see that it was proven with a real test (not just asserted), and see that it was fixed and re-verified.

## Positioning

Uplift is one engine, two modes, one shared report format — not four separate features bolted together. **Impact Mode** answers "what will this change break?" (code + tests + API contracts + Docker). **Migrate Mode** answers "upgrade this dependency safely, matching our style." Both run the same four-step pipeline (Predict → Prove → Repair → Verify) through IBM Bob 2.0, which does the actual reasoning: judging impact per item, writing the proof test, running parallel sandboxed repair workers each scoped to one module, and evaluating its own accuracy against ground truth. A competitor could build a static dependency graph; it could not truthfully claim the graph is proven by a passing/failing test and repaired by an isolated agent per module. The dashboard's job is to make that mechanism visible, not to hide it behind a generic "AI found issues" page.

## Operating Context

- Deployed as a static-data Python Dash app (Render primary, Hugging Face Spaces backup), self-contained: it ships its own copy of `schema/report.schema.json` because the hosting root directory is `dashboard/` only.
- Reports are JSON, validated client-side against the shared schema; a viewer can also drop or paste their own `report.json` and see it rendered exactly like a built-in scenario, or see the first schema errors if it's invalid.
- Demonstrated live on three real Impact scenarios (`s1-null-user`, `s2-cents`, `s3-pydantic2`-as-migrate) plus a Pydantic v1→v2 migration walkthrough.
- Everything on this surface was built through logged IBM Bob 2.0 task sessions (`bob_sessions/LOG.md`, with coin cost and a screenshot per task) — this is itself a fact the surface may reference (the "Powered by IBM Bob" panel), not an implementation detail to hide.
- Judging is a cold, unassisted, single-pass viewing; there is no one present to explain the UI.

## Capabilities and Constraints

- Stack: Python Dash + `dash-bootstrap-components` + `dash-cytoscape`, already built (not a greenfield choice). No backend, database, or secrets — must run from committed files only.
- Graph must stay legible and performant up to ~200 nodes; above ~60 nodes, only `will_break` nodes keep permanent labels.
- Every mock/demo report is explicitly labeled `generatedBy: "mock"`; before submission every mock must be replaced by a real, Bob-generated report (`scripts/verify.py` enforces this). The surface must never blur the line between a mock and a real result.
- Naming constraint: never use the phrase "blast radius" anywhere in this surface's copy (a named rival hackathon submission uses that name; the project uses "what a change will break" / "impact map" instead).
- Undecided / open: whether `dashboard/reports/eval.md` (the "what we missed" detail behind the accuracy card) exists yet depends on Member A's evaluation task; the surface must degrade gracefully (hide the button) when it's absent, never fabricate misses.

## Brand Commitments

- Name: **Uplift**. Tagline: "Know what a change will break — in your code, your containers, and your conventions. Then let Bob fix it."
- "Powered by IBM Bob 2.0" / "Built with IBM Bob 2.0" is a load-bearing, literal claim for this submission, not marketing flourish — the code, the reasoning, and this dashboard's own construction are attributed to Bob task sessions.
- Never use "blast radius" in any public-facing copy on this surface (see Constraints).

## Evidence on Hand

- Real report: `reports/s1-null-user.json`.
- Mock/demo reports (to be replaced before submission, not treated as real evidence): `schema/examples/impact-s1.mock.json`, `schema/examples/migrate-pydantic2.mock.json`.
- Real, dated Bob session log with per-task coin cost and a screenshot: `bob_sessions/LOG.md` and `bob_sessions/uplift_C_*` images.
- No testimonials, customer names, pricing, or benchmark claims exist and none should be invented; the "Accuracy" card's precision/recall/TP/FP/FN figures are the only quantitative claims this surface may show, and only when a report actually carries `metrics.accuracy`.

## Product Principles

1. **Prove, don't assert.** Every verdict, fix, or accuracy figure shown must trace to a runnable test, a cited guide quote, or a real code line — never decorative confidence.
2. **Honesty outranks polish.** False negatives and misses are shown as plainly as hits; hiding a miss to look more impressive is a worse failure than looking less impressive.
3. **One engine, two modes, visually unified.** Impact and Migrate share the same graph/verdict/proof/repair pipeline and should read as one system, not two disconnected products.
4. **Bob's reasoning stays visible.** The interface should make IBM Bob's process (verdict, proof, parallel repair, migration-guide reading) legible as a sequence of real steps, not hide it behind an opaque "AI did something" surface.
5. **Works cold, in under two minutes.** A first-time viewer with zero context must be able to state the risk and see the proof within one scroll of opening any scenario.

## Accessibility & Inclusion

- Minimum 4.5:1 text contrast on every surface (light cards and the dark page background alike) — this has been an active problem area and is a hard requirement, not an aspiration.
- Verdict/status state is never colour-only; every coloured badge, chip, or node carries text or an icon too.
- All interactive elements (filters, tabs, upload area, graph controls) are keyboard-reachable with a visible focus outline.
- `prefers-reduced-motion` is respected; hover/transition effects must not fire repeatedly or flicker on ordinary mouse movement.
- The impact graph has a plain-list accessible fallback for screen-reader and keyboard users, kept in sync with the visual graph.
- Layout holds at 375px width with no horizontal page scroll.

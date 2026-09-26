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

# Uplift Engine

Predict what a change will break, prove it with a failing test, repair it with sandboxed workers.

## Setup

```bash
# Python 3.11 or 3.12 only (3.13+ breaks Pydantic v1 in the demo app)
# Windows: set PYTHONUTF8=1

cd engine
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e ".[dev]"
```

Verify:

```bash
uplift --help
python -m pytest -q   # 62+ tests should pass
```

---

## Commands

| Command | What it does |
|---|---|
| `uplift diff` | Parse a patch, classify changed symbols |
| `uplift graph` | 3-hop reference graph from changed symbols |
| `uplift report` | Assemble a full report JSON from graph + verdicts + proofs + repairs |
| `uplift validate` | Validate report JSON against schema |
| `uplift proof-run` | Run proof tests, determine confirmed/unconfirmed |
| `uplift migrate-scan` | Scan repo for migration catalog occurrences |
| `uplift upgrade-test` | Run tests against upgraded requirements (temp venv) |
| `uplift comment` | Generate a Markdown PR comment from a report |
| `uplift run-all` | Run the full predict pipeline (diff + graph + routes + test-map) |
| `uplift mcp` | Start the MCP server (B11) |

---

### `uplift diff`

Parse a patch and classify each changed symbol.

```
Options:
  --repo PATH    Repository root
  --patch FILE   Unified diff patch file
  --out FILE     Output JSON
  --applied      Patch is already applied to repo
```

```bash
uplift diff --repo sample-app --patch sample-app/scenarios/s1-null-user.patch --out .uplift/diff.json
```

---

### `uplift graph`

Run diff + 3-hop reference graph. Finds every caller/route/test reachable from the change.

```
Options:
  --repo PATH    Repository root
  --patch FILE   Unified diff patch file
  --out FILE     Output graph.json
  --applied      Patch is already applied to repo
```

```bash
uplift graph --repo sample-app --patch sample-app/scenarios/s1-null-user.patch --out .uplift/graph.json
# Prints 9 candidates for s1-null-user
```

---

### `uplift report`

Assemble a schema-valid report from graph + optional verdict/proof/repair files.

```
Options:
  --graph FILE         .uplift/graph.json
  --scenario TEXT      Scenario ID (e.g. s1-null-user)
  --title TEXT         Human-readable title
  --out FILE           Output report JSON
  --verdicts FILE      .uplift/verdicts.json  (optional)
  --proofs FILE        .uplift/proofs.json    (optional)
  --repairs GLOB       Glob for .uplift/repair-*.json files (optional)
  --catalog FILE       .uplift/catalog.json   (migrate mode, optional)
  --occurrences FILE   .uplift/occurrences.json (migrate mode, optional)
  --library TEXT       Library name for dependency upgrade (e.g. pydantic)
  --from TEXT          Version upgrading from
  --to TEXT            Version upgrading to
  --bob-modes TEXT     Comma-separated Bob mode names for provenance
  --verified           Mark pipeline.verify as done
```

```bash
uplift report \
  --graph .uplift/graph.json \
  --verdicts .uplift/verdicts.json \
  --scenario s1-null-user \
  --title "get_user returns None instead of raising" \
  --bob-modes uplift-impact-analyst \
  --out reports/s1-null-user.json
```

---

### `uplift validate`

Validate one or more report JSON files against `schema/report.schema.json`.

```bash
uplift validate reports/s1-null-user.json
uplift validate reports/*.json
```

---

### `uplift proof-run`

Run proof tests in both base and head trees; determine confirmed/unconfirmed per proof.

```
Options:
  --repo PATH        Repository root
  --patch FILE       Patch file
  --proofs DIR       Directory containing proof test files
  --out FILE         Output .uplift/proofs.json
  --applied          Patch already applied
  --app-python PATH  Python interpreter to use (default: sample-app/.venv)
```

```bash
uplift proof-run \
  --repo sample-app \
  --patch sample-app/scenarios/s1-null-user.patch \
  --proofs sample-app/tests/uplift_proofs \
  --out .uplift/proofs.json \
  --applied
```

---

### `uplift migrate-scan`

Scan `repo/shop/` for every entry in a migration catalog (regex, import, call, identifier detect types).

```
Options:
  --repo PATH      Repository root
  --catalog FILE   Migration catalog JSON (list of entries with id + detect)
  --out FILE       Output .uplift/occurrences.json
```

```bash
uplift migrate-scan \
  --repo sample-app \
  --catalog .uplift/catalog.json \
  --out .uplift/occurrences.json
```

---

### `uplift upgrade-test`

Copy the repo to a temp dir, create a fresh venv, install upgraded requirements, run pytest, report results per module.

```
Options:
  --repo PATH           Repository root
  --requirements FILE   Upgraded requirements.txt
  --out FILE            Output JSON with passed/failed/byModule
  --current             Use existing interpreter instead of a temp venv
  --app-python PATH     Python interpreter path
```

```bash
# On scenario/s3-pydantic2 branch:
uplift upgrade-test \
  --repo sample-app \
  --requirements sample-app/requirements.txt \
  --out .uplift/upgrade-before.json
```

---

### `uplift comment`

Generate a Markdown PR comment from a report (risk line, verdict table, contracts, metrics).

```
Options:
  --report FILE   Report JSON to render
```

```bash
uplift comment --report reports/s1-null-user.json
# Pipe to clipboard or file:
uplift comment --report reports/pr.json > comment.md
```

---

### `uplift run-all`

Run the full predict pipeline for a scenario in one shot: diff + graph + routes + test-map. Prints next Bob steps.

```
Options:
  --repo PATH      Repository root
  --scenario TEXT  Scenario ID
  --applied        Patch already applied
```

```bash
# On scenario/s1-null-user branch:
uplift run-all --repo sample-app --scenario s1-null-user --applied
```

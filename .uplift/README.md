# Working artifacts

The former shared graph/verdict/proof/catalog files mixed scenarios and included
malformed proof JSON. They are preserved under a8-audit/original-working-tree/.

Current, verified artifacts live under evidence/<scenario>/ and final reports
under reports/. Pass an explicit scenario directory when consuming artifacts,
for example MCP uplift_report(work_dir="evidence/s1-null-user", ...).

Run scripts/reproduce.py to regenerate all three isolated scenarios. Read
eval.md for accuracy. conventions.json describes the restored baseline.

The old a8-audit/ snapshots and console output record the state before Codex's
repairs; they are not the final published evidence.

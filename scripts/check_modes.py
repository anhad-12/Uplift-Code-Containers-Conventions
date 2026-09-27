import re
import sys

import yaml

path = sys.argv[1] if len(sys.argv) > 1 else ".bob/custom_modes.yaml"
raw = open(path, encoding="utf-8").read()
d = yaml.safe_load(raw)
GROUPS = {"read", "edit", "execute", "mcp", "skill", "todo", "subagent", "mode"}
slugs = set()
for m in d["customModes"]:
    assert re.fullmatch(r"[a-zA-Z0-9-]+", m["slug"]), m["slug"]
    assert m["slug"] not in slugs
    slugs.add(m["slug"])
    assert m["roleDefinition"].strip()
    seen = set()
    for g in m["groups"]:
        name = g[0] if isinstance(g, list) else g
        assert name in GROUPS, (m["slug"], name)
        assert name not in seen, "duplicate group"
        seen.add(name)
        if isinstance(g, list):
            re.compile(g[1]["fileRegex"])
assert all(ord(c) < 128 for c in raw), "non-ascii characters present"
print("modes:", len(d["customModes"]), "- parse ok, group names ok, regexes compile, ascii ok")


def rx(slug):
    m = next(m for m in d["customModes"] if m["slug"] == slug)
    return next(re.compile(g[1]["fileRegex"]) for g in m["groups"] if isinstance(g, list))


TESTS = [
    ("uplift-worker-users", ".uplift/repair-users-s1-null-user.json", True),
    ("uplift-worker-users", ".uplift/repair-orders-s1-null-user.json", False),
    ("uplift-worker-orders", ".uplift/repair-orders-s2-cents.json", True),
    ("uplift-worker-payments", ".uplift/repair-payments-s2-cents.json", True),
    ("uplift-worker-core", ".uplift/repair-core-s3-pydantic2.json", True),
    ("uplift-impact-analyst", ".uplift/verdicts.json", True),
    ("uplift-impact-analyst", r"C:\Uplift\.uplift\graph.json", True),
    ("uplift-impact-analyst", "sample-app/shop/users/service.py", False),
    ("uplift-prover", "sample-app/tests/uplift_proofs/test_x.py", True),
    ("uplift-prover", "sample-app/tests/users/test_service.py", False),
    ("uplift-worker-users", "sample-app/shop/users/service.py", True),
    ("uplift-worker-users", r"C:\Uplift\sample-app\shop\users\routes.py", True),
    ("uplift-worker-users", "sample-app/shop/orders/service.py", False),
    ("uplift-worker-orders", "sample-app/shop/users/service.py", False),
    ("uplift-worker-core", "sample-app/requirements.txt", True),
    ("uplift-worker-core", "sample-app/shop/app.py", True),
    ("uplift-worker-core", "sample-app/shop/admin/reports.py", True),
    ("uplift-worker-core", "sample-app/shop/notifications/email.py", True),
    ("uplift-worker-core", "sample-app/shop/users/service.py", False),
    ("uplift-worker-core", "sample-app/shop/orders/invoice.py", False),
    ("uplift-verifier", "reports/s1.json", True),
    ("uplift-verifier", "sample-app/shop/app.py", False),
]
bad = 0
for slug, p, want in TESTS:
    got = bool(rx(slug).match(p))
    if got != want:
        bad += 1
        print("MISMATCH", slug, p, "expected", want, "got", got)
print("regex cases:", len(TESTS), "mismatches:", bad)
sys.exit(1 if bad else 0)

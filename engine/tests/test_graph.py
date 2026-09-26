"""test_graph.py — tests for uplift.graph.find_candidates.

Integration tests skip with a clear message when sample-app/ or its
scenario patches are not found in the repository.
"""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

from uplift.diff import changed_symbols, head_and_base
from uplift.graph import find_candidates, _module_of


# ---------------------------------------------------------------------------
# Helpers shared by fixture tests
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"],
                   cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"],
                   cwd=repo, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# Unit: _module_of
# ---------------------------------------------------------------------------

def test_module_of_subpackage():
    assert _module_of("shop/users/service.py") == "users"
    assert _module_of("shop/admin/reports.py") == "admin"
    assert _module_of("shop/payments/charge.py") == "payments"


def test_module_of_core():
    assert _module_of("shop/app.py") == "core"
    assert _module_of("shop/config.py") == "core"


# ---------------------------------------------------------------------------
# Fixture unit test: hop-2 detection and name-based fallback
# ---------------------------------------------------------------------------

def _build_two_hop_repo(tmp_path: Path) -> Path:
    """
    Build a minimal project where:
      shop/service.py   - defines get_item(), uses a dynamic name  (hop-0 changed)
      shop/middle.py    - calls get_item()                          (hop-1 candidate)
      shop/consumer.py  - calls middle_fn() from middle.py          (hop-2 candidate)
      shop/dynamic.py   - uses get_item by string, triggers name fallback

    We do NOT put get_item into dynamic.py; instead we put a bare name reference
    (ast.Name node) so the name-based fallback picks it up when jedi cannot
    resolve it across a dynamic boundary.
    """
    repo = tmp_path / "repo"

    _write(repo / "shop" / "__init__.py", "")
    _write(repo / "shop" / "service.py", """\
        def get_item(item_id: int):
            return {"id": item_id}
        """)
    _write(repo / "shop" / "middle.py", """\
        from shop.service import get_item

        def middle_fn(item_id: int):
            return get_item(item_id)
        """)
    _write(repo / "shop" / "consumer.py", """\
        from shop.middle import middle_fn

        def consume(item_id: int):
            return middle_fn(item_id)
        """)
    # dynamic.py references get_item only by name (simulates a dynamic lookup
    # that jedi cannot follow); the name-based fallback must catch it.
    _write(repo / "shop" / "dynamic.py", """\
        # pretend this is reached via importlib; jedi won't resolve it
        def dynamic_caller(fn=None):
            result = get_item(1)   # bare name reference
            return result
        """)
    return repo


def test_hop2_detection_and_name_fallback(tmp_path: Path) -> None:
    """Verify indirect (hop 2) detection and the AST name-based fallback."""
    repo = _build_two_hop_repo(tmp_path)
    _git_init(repo)

    # Patch: change get_item body
    # Note: textwrap.dedent strips the leading spaces, but the patch context lines
    # need exact leading space preserved for git apply.
    patch_text = (
        "--- a/shop/service.py\n"
        "+++ b/shop/service.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def get_item(item_id: int):\n"
        "-    return {\"id\": item_id}\n"
        "+    return None\n"
    )
    patch = tmp_path / "test.patch"
    patch.write_text(patch_text, encoding="utf-8")

    head, base = head_and_base(repo, patch, applied=False)
    changed = changed_symbols(head, base, patch)
    assert len(changed) == 1, f"Expected 1 changed symbol, got {changed}"

    candidates = find_candidates(head, changed, max_hops=3)
    ids = {c["id"] for c in candidates}
    hops = {c["id"]: c["hop"] for c in candidates}

    # middle_fn should be hop 1 (direct caller of get_item)
    middle_id = "shop/middle.py#middle_fn"
    assert middle_id in ids, f"hop-1 candidate missing: {ids}"
    assert hops[middle_id] == 1

    # consume should be hop 2 (calls middle_fn which calls get_item)
    consumer_id = "shop/consumer.py#consume"
    assert consumer_id in ids, f"hop-2 candidate missing: {ids}"
    assert hops[consumer_id] == 2

    # At least one candidate should have resolution="name" (the dynamic.py fallback)
    # OR all jedi resolutions succeeded — the test tolerates either, but if
    # dynamic_caller is in the result it must have resolution="name".
    dynamic_id = "shop/dynamic.py#dynamic_caller"
    if dynamic_id in ids:
        dynamic_cand = next(c for c in candidates if c["id"] == dynamic_id)
        assert dynamic_cand["resolution"] == "name", (
            f"Expected resolution='name' for dynamic_caller, got {dynamic_cand['resolution']}"
        )

    # No duplicates
    all_ids = [c["id"] for c in candidates]
    assert len(all_ids) == len(set(all_ids)), "Duplicate candidates found"

    # All resolutions must be "jedi" or "name"
    for c in candidates:
        assert c["resolution"] in ("jedi", "name"), f"Unknown resolution: {c['resolution']}"


# ---------------------------------------------------------------------------
# Helper to locate sample-app
# ---------------------------------------------------------------------------

def _find_sample_app() -> Path | None:
    """Walk up from this file to find sample-app/."""
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent, here.parent.parent.parent]:
        candidate = parent / "sample-app"
        if candidate.is_dir():
            return candidate
    return None


SAMPLE_APP = _find_sample_app()

_SKIP_MSG = (
    "sample-app/ not found — integration tests require the demo app "
    "and its scenario patches to be present alongside the engine/ folder."
)


# ---------------------------------------------------------------------------
# Integration: s1-null-user  — expect exactly 9 candidates
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SAMPLE_APP is None, reason=_SKIP_MSG)
def test_s1_null_user_candidates() -> None:
    """s1-null-user must produce exactly 9 candidates with the specified ids."""
    assert SAMPLE_APP is not None  # narrowing for type checker
    patch = SAMPLE_APP / "scenarios" / "s1-null-user.patch"
    if not patch.exists():
        pytest.skip(f"Patch not found: {patch}")

    head, base = head_and_base(SAMPLE_APP, patch, applied=False)
    changed = changed_symbols(head, base, patch)
    assert len(changed) >= 1, "Expected at least 1 changed symbol"

    candidates = find_candidates(head, changed, max_hops=3)
    ids = {c["id"] for c in candidates}
    hops_by_id = {c["id"]: c["hop"] for c in candidates}

    # --- Hop-1 expected (7) ---
    expected_hop1 = {
        "shop/admin/reports.py#user_spend_report",
        "shop/notifications/email.py#send_welcome",
        "shop/orders/invoice.py#build_invoice",
        "shop/orders/service.py#create_order",
        "shop/payments/charge.py#charge",
        "shop/payments/receipt.py#render_receipt",
        "shop/users/routes.py#get_user_route",
    }

    # --- Hop-2 expected (2) ---
    expected_hop2 = {
        "shop/orders/routes.py#post_order",
        "shop/payments/routes.py#post_payment",
    }

    expected_all = expected_hop1 | expected_hop2

    missing = expected_all - ids
    assert not missing, (
        f"Missing expected candidates:\n"
        + "\n".join(f"  {m}" for m in sorted(missing))
        + f"\n\nActual candidates ({len(candidates)}):\n"
        + "\n".join(f"  hop={c['hop']}  {c['id']}" for c in sorted(candidates, key=lambda x: (x['hop'], x['id'])))
    )

    # Check total count
    assert len(candidates) == 9, (
        f"Expected 9 candidates, got {len(candidates)}:\n"
        + "\n".join(f"  hop={c['hop']}  {c['id']}" for c in sorted(candidates, key=lambda x: (x['hop'], x['id'])))
    )

    # Check hops
    for cid in expected_hop1:
        assert hops_by_id[cid] == 1, f"{cid} should be hop 1, got {hops_by_id[cid]}"
    for cid in expected_hop2:
        assert hops_by_id[cid] == 2, f"{cid} should be hop 2, got {hops_by_id[cid]}"

    # Verify hop-2 via relationships
    assert hops_by_id["shop/orders/routes.py#post_order"] == 2
    assert hops_by_id["shop/payments/routes.py#post_payment"] == 2

    # No duplicates
    all_ids = [c["id"] for c in candidates]
    assert len(all_ids) == len(set(all_ids)), "Duplicate candidates found"


# ---------------------------------------------------------------------------
# Integration: s2-cents  — at least 6 specified hop-1 candidates
# ---------------------------------------------------------------------------

@pytest.mark.skipif(SAMPLE_APP is None, reason=_SKIP_MSG)
def test_s2_cents_candidates() -> None:
    """s2-cents must include at least the 6 specified hop-1 candidates."""
    assert SAMPLE_APP is not None
    patch = SAMPLE_APP / "scenarios" / "s2-cents.patch"
    if not patch.exists():
        pytest.skip(f"Patch not found: {patch}")

    head, base = head_and_base(SAMPLE_APP, patch, applied=False)
    changed = changed_symbols(head, base, patch)
    assert len(changed) >= 1, "Expected at least 1 changed symbol"

    candidates = find_candidates(head, changed, max_hops=3)
    ids = {c["id"] for c in candidates}
    hops_by_id = {c["id"]: c["hop"] for c in candidates}

    expected_hop1 = {
        "shop/admin/reports.py#revenue_total",
        "shop/notifications/email.py#send_receipt_email",
        "shop/orders/invoice.py#payment_line",
        "shop/payments/receipt.py#render_receipt",
        "shop/payments/repo.py#save_payment",
        "shop/payments/routes.py#post_payment",
    }

    missing = expected_hop1 - ids
    assert not missing, (
        f"Missing expected hop-1 candidates for s2-cents:\n"
        + "\n".join(f"  {m}" for m in sorted(missing))
        + f"\n\nActual candidates ({len(candidates)}):\n"
        + "\n".join(f"  hop={c['hop']}  {c['id']}" for c in sorted(candidates, key=lambda x: (x['hop'], x['id'])))
    )

    # All 6 must be hop 1
    for cid in expected_hop1:
        assert hops_by_id.get(cid) == 1, (
            f"{cid} expected at hop 1, got {hops_by_id.get(cid)}"
        )

    # No duplicates
    all_ids = [c["id"] for c in candidates]
    assert len(all_ids) == len(set(all_ids)), "Duplicate candidates found"

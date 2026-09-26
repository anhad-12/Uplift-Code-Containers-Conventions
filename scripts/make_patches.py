"""Generate the three scenario patches with difflib (LF only, no git config involved).

Run from the repo root:  python scripts/make_patches.py
Writes sample-app/scenarios/<id>.patch. Paths inside patches are relative to sample-app/ (a/shop/...).
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

APP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sample-app")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else APP / "scenarios"

# Each scenario: {relative path inside sample-app: [(old, new), ...]}. Every `old` must occur exactly once.
SCENARIOS = {
    "s1-null-user": {
        "shop/users/service.py": [
            ("from shop.errors import NotFoundError\n", ""),
            ('    user = repo.find_user(user_id)\n    if user is None:\n        raise NotFoundError("user", user_id)\n    return user\n',
             "    return repo.find_user(user_id)\n"),
        ],
        "tests/users/test_service.py": [
            ("import pytest\n\nfrom shop.errors import NotFoundError\nfrom shop", "from shop"),
            ("def test_get_user_missing_raises():\n    with pytest.raises(NotFoundError):\n        get_user(999)\n",
             "def test_get_user_missing_returns_none():\n    assert get_user(999) is None\n"),
        ],
    },
    "s2-cents": {
        "shop/payments/charge.py": [
            ("    amount: float  # dollars\n", "    amount: int  # cents\n"),
            ("    return Payment(user_id, round(amount + fee, 2))\n", "    return Payment(user_id, round((amount + fee) * 100))\n"),
        ],
        "tests/payments/test_charge.py": [("== 103.2", "== 10320")],
        "tests/payments/test_routes.py": [("== 103.2", "== 10320")],
    },
    "s3-pydantic2": {
        "requirements.txt": [("fastapi==0.99.1", "fastapi==0.115.0"), ("pydantic==1.10.13", "pydantic==2.9.2")],
    },
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, files in SCENARIOS.items():
        chunks: list[str] = []
        for rel, edits in files.items():
            old_text = (APP / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
            new_text = old_text
            for old, new in edits:
                if new_text.count(old) != 1:
                    raise SystemExit(f"{name}: {rel}: expected exactly one occurrence of {old[:50]!r}, found {new_text.count(old)}")
                new_text = new_text.replace(old, new)
            diff = difflib.unified_diff(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                                        fromfile=f"a/{rel}", tofile=f"b/{rel}")
            chunks.append("".join(diff))
        patch = "".join(chunks)
        assert "\r" not in patch
        (OUT / f"{name}.patch").write_text(patch, encoding="utf-8", newline="\n")
        print(f"{name}.patch: {len(files)} file(s), {len(patch.splitlines())} lines")


if __name__ == "__main__":
    main()

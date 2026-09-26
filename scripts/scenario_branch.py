"""Create the scenario branches: python scripts/scenario_branch.py <id> [<id> ...]   (ids: s1-null-user, s2-cents, s3-pydantic2)

For each id: branch scenario/<id> from main, apply sample-app/scenarios/<id>.patch, commit, return to main.
The patch paths are relative to sample-app/, so it is applied with --directory=sample-app.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDS = ("s1-null-user", "s2-cents", "s3-pydantic2")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result


def make_branch(sid: str) -> None:
    patch = ROOT / "sample-app" / "scenarios" / f"{sid}.patch"
    if not patch.exists():
        raise SystemExit(f"missing {patch}")
    branch = f"scenario/{sid}"
    if git("rev-parse", "--verify", branch, check=False).returncode == 0:
        print(f"{branch} already exists, skipping")
        return
    git("switch", "main")
    git("switch", "-c", branch)
    git("apply", "--directory=sample-app", str(patch))
    git("add", "-A")
    git("commit", "-m", f"scenario {sid}: apply patch")
    git("switch", "main")
    print(f"created {branch}")


def main() -> None:
    if git("status", "--porcelain").stdout.strip():
        raise SystemExit("commit or stash your changes first (working tree not clean)")
    for sid in sys.argv[1:] or IDS:
        if sid not in IDS:
            raise SystemExit(f"unknown scenario {sid}; expected one of {IDS}")
        make_branch(sid)


if __name__ == "__main__":
    main()

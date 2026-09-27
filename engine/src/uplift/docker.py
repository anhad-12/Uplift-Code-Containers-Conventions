"""Conservative, static Docker COPY/ADD cache-impact analysis.

Instruction positions are used as layer indices (not measured image layers).
Unknown variable expansions conservatively invalidate the containing stage.
No build duration is estimated. See docs/docker-impact.md for limitations.
"""
from __future__ import annotations

import fnmatch
import json
import re
import shlex
from pathlib import Path


def impact(root: Path, changed_files: list[str]) -> list[dict]:
    dockerfile = root / "Dockerfile"
    if not dockerfile.exists():
        return []
    logical = re.sub(r"\\\s*\n", " ", dockerfile.read_text(encoding="utf-8"))
    instructions = []
    for line in logical.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            command, _, args = line.partition(" ")
            instructions.append((command.upper(), args.strip()))
    stages = []
    current = None
    aliases = {}
    for index, (command, args) in enumerate(instructions, 1):
        if command == "FROM":
            parts = args.split()
            base = next((p for p in parts if not p.startswith("--")), "")
            current = {"start": index, "end": len(instructions), "copies": [], "dependencies": []}
            if stages:
                stages[-1]["end"] = index - 1
            stages.append(current)
            if base in aliases:
                current["dependencies"].append((index, aliases[base]))
            aliases[str(len(stages) - 1)] = current
            if len(parts) >= 3 and parts[-2].upper() == "AS":
                aliases[parts[-1]] = current
        elif current is not None and command in ("COPY", "ADD"):
            source_stage = re.search(r"--from=([^\s]+)", args)
            if source_stage:
                if source_stage[1] in aliases:
                    current["dependencies"].append((index, aliases[source_stage[1]]))
                continue
            args = re.sub(r"--[\w-]+(?:=\S+)?\s*", "", args)
            try:
                tokens = json.loads(args) if args.startswith("[") else shlex.split(args)
            except (ValueError, json.JSONDecodeError):
                tokens = ["$UNKNOWN", "."]
            current["copies"].append((index, tokens[:-1]))
    result = []
    for changed in sorted(set(p.replace("\\", "/").removeprefix("./") for p in changed_files)):
        affected = {}
        for stage in stages:
            earliest = stage["start"] if changed in {"Dockerfile", ".dockerignore"} else None
            for index, sources in stage["copies"]:
                for src in sources:
                    src = src.removeprefix("./").rstrip("/")
                    if "://" in src:
                        continue
                    if "$" in src or src in {"", "."} or changed == src or changed.startswith(src + "/") or fnmatch.fnmatchcase(changed, src):
                        earliest = min(earliest or index, index)
            for index, dependency in stage["dependencies"]:
                if id(dependency) in affected:
                    earliest = min(earliest or index, index)
            if earliest is not None:
                affected[id(stage)] = earliest
                result.append({"file": "Dockerfile", "layer": earliest,
                               "totalLayers": len(instructions),
                               "trigger": f"{changed} may invalidate COPY/ADD inputs or a dependent stage",
                               "layersRebuilt": f"{earliest}-{stage['end']}",
                               "suggestion": "Copy dependency manifests before application code. Indices are Dockerfile instructions; cache effects are conservative and build time is unmeasured."})
    return result

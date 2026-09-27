"""Portable launcher: re-execute the MCP server with the engine environment."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
python = root / 'engine/.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if not python.exists():
    raise SystemExit('Create engine/.venv and install engine[mcp] first.')
raise SystemExit(subprocess.call([str(python), '-m', 'uplift', 'mcp'], cwd=root))

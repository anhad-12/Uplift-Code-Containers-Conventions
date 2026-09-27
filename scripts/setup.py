"""Set up isolated project environments using Python 3.11 or 3.12."""
from pathlib import Path
import subprocess
import sys
import os

root = Path(__file__).resolve().parent.parent
if sys.version_info[:2] not in ((3,11),(3,12)):
    raise SystemExit('Run this script with Python 3.11 or 3.12.')
setups = [
    ('engine/.venv', ['-e', 'engine[dev,mcp]']),
    ('sample-app/.venv311', ['-r','scenarios/baseline-requirements.txt']),
    ('sample-app/.venv-v2-311', ['-r','scenarios/s3-pydantic2/requirements.txt']),
    ('dashboard/.venv311', ['-r','dashboard/requirements.txt']),
]
for folder, dependencies in setups:
    subprocess.run([sys.executable,'-m','venv',folder],cwd=root,check=True)
    python=root/folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run([str(python),'-m','pip','install',*dependencies],cwd=root,check=True)

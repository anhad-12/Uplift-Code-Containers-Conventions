"""Verify a materialized scenario; CI can then restore its baseline for engine tests."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from reproduce import ROOT, python_in, tree_hash


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-baseline',action='store_true')
    args=parser.parse_args()
    path=ROOT/'.uplift/scenario-branch.json'
    if not path.exists():
        print('Baseline branch: no scenario preparation needed.')
        return
    info=json.loads(path.read_text(encoding='utf8'))
    if args.prepare_baseline:
        if os.environ.get('CI')!='true':
            raise SystemExit('--prepare-baseline is restricted to disposable CI checkouts.')
        status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
        if status.strip():
            raise SystemExit('Refusing to restore a dirty CI checkout.')
    with tempfile.TemporaryDirectory(prefix='uplift_branch_verify_') as directory:
        snapshot=Path(directory)/'app'
        shutil.copytree(ROOT/'sample-app',snapshot,ignore=shutil.ignore_patterns('scenarios','.venv*','__pycache__','.pytest_cache'))
        if tree_hash(snapshot)!=info['verifiedSourceSha256']:
            raise SystemExit('Scenario source differs from the published verified snapshot; regenerate its evidence.')
    python=python_in('sample-app/.venv-v2-311' if info['scenario']=='s3-pydantic2' else 'sample-app/.venv311')
    subprocess.run([python,'-m','pytest','-q'],cwd=ROOT/'sample-app',check=True)
    if args.prepare_baseline:
        subprocess.run(['git','restore','--source='+info['baselineCommit'],'--worktree','--','sample-app'],cwd=ROOT,check=True)
        print('Verified scenario; CI now uses its committed baseline for engine/reproduction tests.')


if __name__=='__main__':
    main()

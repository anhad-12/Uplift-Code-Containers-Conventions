"""Append repaired scenario snapshots to existing branches without rewriting history.

Run after committing the baseline/completion branch. Each branch uses a fresh
worktree, receives the committed baseline plus exactly its scenario/repair, and
must match the already measured source hash before it can be committed.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tempfile
from reproduce import ROOT, IDS, tree_hash, python_in
from scenario_repairs import apply


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, encoding='utf-8').strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', default='HEAD')
    args=parser.parse_args()
    if git('status','--porcelain'):
        raise SystemExit('Commit the baseline working tree before materializing branches.')
    base=git('rev-parse',args.base_ref)
    records=[]
    area=ROOT/'.uplift/tmp/scenario-worktrees';area.mkdir(parents=True,exist_ok=True)
    for sid in IDS:
        branch='scenario/'+sid
        before=git('rev-parse',branch)
        worktree=area/sid
        if worktree.exists():
            raise SystemExit('Existing worktree requires inspection: '+str(worktree))
        git('worktree','add',str(worktree),branch)
        git('merge','--no-ff','--no-commit','-s','ours',base,cwd=worktree)
        # This restore is confined to a newly created worktree. No caller's dirty
        # files are touched and the old branch commit remains the new parent.
        git('restore','--source='+base,'--staged','--worktree','--','.',cwd=worktree)
        app=worktree/'sample-app'
        proofdir=app/'tests/uplift_proofs'
        for p in proofdir.glob('*'):
            if p.is_file(): p.unlink()
        git('apply','--directory=sample-app',str(ROOT/'sample-app/scenarios'/f'{sid}.patch'),cwd=worktree)
        if sid!='s3-pydantic2':
            shutil.copytree(ROOT/'scenarios'/sid/'proofs',proofdir,dirs_exist_ok=True)
        apply(app,sid)
        extras=ROOT/'scenarios'/sid/'after_tests'
        for p in extras.glob('test_*.py'):
            shutil.copy2(p,app/'tests/payments'/p.name)
        with tempfile.TemporaryDirectory(prefix='uplift_branch_hash_') as directory:
            snapshot=Path(directory)/'app'
            shutil.copytree(app,snapshot,ignore=shutil.ignore_patterns('scenarios','.venv*','__pycache__','.pytest_cache'))
            actual=tree_hash(snapshot)
        expected=json.loads((ROOT/'evidence'/sid/'manifest.json').read_text(encoding='utf8'))['repairedSha256']
        if actual!=expected:
            raise SystemExit(f'Branch tree does not match measured evidence: {sid}; retained {worktree} for inspection')
        interpreter=python_in('sample-app/.venv-v2-311' if sid=='s3-pydantic2' else 'sample-app/.venv311')
        subprocess.run([interpreter,'-m','pytest','-q'],cwd=app,check=True)
        (worktree/'.uplift/scenario-branch.json').write_text(json.dumps({'scenario':sid,'baselineCommit':base,'verifiedSourceSha256':actual},indent=2)+'\n',encoding='utf8')
        git('add','--all',cwd=worktree)
        git('commit','-m',f'[bob] restore isolated {sid} and verified repairs',cwd=worktree)
        after=git('rev-parse','HEAD',cwd=worktree)
        records.append({'scenario':sid,'before':before,'after':after,'baselineCommit':base,'verifiedSourceSha256':actual})
        print(sid,after,'matches verified source',flush=True)
        git('worktree','remove',str(worktree))
    target=ROOT/'docs/scenario-branches.json'
    target.write_text(json.dumps(records,indent=2)+'\n',encoding='utf8')
    print('Branch history preserved; wrote docs/scenario-branches.json')


if __name__=='__main__':
    main()

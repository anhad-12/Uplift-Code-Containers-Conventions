"""Regenerate isolated scenarios, repairs and evidence. Run with engine's Python.

No legacy scenario branch is changed. Predictions are preserved from the Bob
snapshots in scenarios/, including misses; new tests and repairs are part of the Bob workflow.
"""
from __future__ import annotations
import argparse
import ast
import collections
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from uplift.diff import changed_symbols, git_apply
from uplift.graph import find_candidates
from uplift.routes import contracts_for, route_map
from uplift.testmap import annotate_candidates
from uplift.docker import impact
from uplift.migrate import scan
from uplift.report import build_report
from accuracy import evaluate
from scenario_repairs import apply

ROOT = Path(__file__).resolve().parent.parent
IDS = ('s1-null-user', 's2-cents', 's3-pydantic2')
TITLES = ('Handle missing users safely', 'Preserve dollar contracts when charges use cents', 'Migrate Pydantic v1 to v2')


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def python_in(folder):
    suffix = 'Scripts/python.exe' if os.name == 'nt' else 'bin/python'
    result = ROOT / folder / suffix
    if not result.exists():
        raise SystemExit('Missing environment: ' + str(result))
    return str(result)


def run_tests(python, tree, target, output, name):
    output.mkdir(parents=True, exist_ok=True)
    xml = output / (name + '.xml')
    command = [python, '-m', 'pytest', '-q', '--continue-on-collection-errors', '--junitxml=' + str(xml), *target]
    result = subprocess.run(command, cwd=tree, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (output / (name + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode not in (0, 1) or not xml.exists():
        raise RuntimeError('Test invocation failed; see ' + str(output / (name + '.txt')))
    counts = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    modules = collections.defaultdict(lambda: dict(counts))
    cases = {}
    for case in ET.parse(xml).iter('testcase'):
        cls = case.get('classname') or case.get('name', '')
        parts = cls.replace('\\', '/').replace('.', '/').split('/')
        module = next((x for x in ('users', 'orders', 'payments') if x in parts), 'core')
        if 'uplift_proofs' in parts:
            filename = parts[-1]
            module = next((x for x in ('users', 'orders', 'payments') if filename.startswith('test_' + x + '_')), 'core')
        status = 'errors' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        counts[status] += 1
        modules[module][status] += 1
        cases[cls + '::' + case.get('name', '')] = status
    data = {**counts, 'exitCode': result.returncode, 'byModule': dict(modules), 'cases': cases,
            'command': command, 'pythonVersion': subprocess.check_output([python, '--version'], text=True).strip()}
    write(output / (name + '.json'), data)
    print(name, counts, flush=True)
    return data


def summary(result):
    return {k: result[k] for k in ('passed', 'failed', 'errors', 'skipped', 'exitCode') if k in result}


def copy_base(target):
    shutil.copytree(ROOT / 'sample-app', target, ignore=shutil.ignore_patterns('.venv*', '__pycache__', '.pytest_cache', 'scenarios', 'uplift_proofs'))


def tree_hash(tree):
    digest = hashlib.sha256()
    for p in sorted(tree.rglob('*')):
        if p.is_file() and not any(x.startswith('.') or x == '__pycache__' for x in p.relative_to(tree).parts):
            digest.update(p.relative_to(tree).as_posix().encode())
            digest.update(p.read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def differences(before, after):
    result, files, added = [], [], []
    names = {p.relative_to(t).as_posix() for t in (before, after) for p in t.rglob('*') if p.is_file() and p.suffix in ('.py', '.txt') and '__pycache__' not in p.parts}
    for name in sorted(names):
        a = (before / name).read_text(encoding='utf-8').splitlines(True) if (before / name).exists() else []
        b = (after / name).read_text(encoding='utf-8').splitlines(True) if (after / name).exists() else []
        if a != b:
            files.append(name)
            result.extend(difflib.unified_diff(a, b, fromfile='a/' + name, tofile='b/' + name))
            matcher = difflib.SequenceMatcher(a=a, b=b)
            for tag, _, _, j1, j2 in matcher.get_opcodes():
                if tag in ('insert', 'replace'):
                    added.extend({'file': name, 'line': j + 1, 'text': b[j].rstrip()} for j in range(j1, j2))
    return ''.join(result), files, added


def compliance(tree, added):
    issues = []
    added_set = {(x['file'], x['line']) for x in added}
    for name in sorted({x['file'] for x in added if x['file'].endswith('.py')}):
        parsed = ast.parse((tree / name).read_text(encoding='utf-8'))
        top_imports = {id(n) for n in parsed.body if isinstance(n, (ast.Import, ast.ImportFrom))}
        for node in ast.walk(parsed):
            if (name, getattr(node, 'lineno', 0)) not in added_set:
                continue
            rule = None
            if isinstance(node, ast.ImportFrom) and node.level:
                rule = 'absolute imports'
            elif isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) not in top_imports:
                rule = 'module-level imports'
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(c.isupper() for c in node.name):
                rule = 'snake_case functions'
            elif isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name) and node.exc.func.id in ('Exception', 'RuntimeError'):
                rule = 'typed domain exceptions'
            if rule:
                issues.append({'file': name, 'line': node.lineno, 'rule': rule})
    return {'checkedLines': len(added), 'violations': len(issues), 'retried': False, 'checks': ['absolute imports', 'module-level imports', 'snake_case functions', 'typed domain exceptions'], 'details': issues, 'addedLines': added}


def make_graph(base, head, patch):
    changed = changed_symbols(head, base, patch)
    candidates = find_candidates(head, changed)
    annotate_candidates(candidates, head)
    return {'changedSymbols': changed, 'candidates': candidates,
            'contracts': contracts_for(candidates, route_map(head)),
            'testsToRun': sorted({t for c in candidates for t in c.get('tests', [])}),
            'untested': [c['id'] for c in candidates if not c.get('tests')],
            'filesScanned': len(list(head.joinpath('shop').rglob('*.py'))), 'secondsTaken': 0,
            'infraImpact': impact(head, [x['id'].split('#')[0] for x in changed])}


def generate(scenario, title, python, v2_python, scratch):
    started = time.perf_counter()
    output = scratch / (scenario + '-evidence')
    output.mkdir(parents=True, exist_ok=True)
    base = scratch / (scenario + '-base'); copy_base(base)
    if scenario != 's3-pydantic2':
        shutil.copytree(ROOT / 'scenarios' / scenario / 'proofs', base / 'tests/uplift_proofs')
    head = scratch / (scenario + '-head'); shutil.copytree(base, head)
    patch = ROOT / 'sample-app/scenarios' / (scenario + '.patch')
    git_apply(head, patch)
    baseline = run_tests(python, base, ['tests'], output, 'base')
    if baseline['exitCode']:
        raise RuntimeError('Base suite failed for ' + scenario)
    interpreter = v2_python if scenario == 's3-pydantic2' else python
    before = run_tests(interpreter, head, ['tests'], output, 'before')
    if not before['failed'] and not before['errors']:
        raise RuntimeError('Scenario did not demonstrate a break: ' + scenario)
    if scenario == 's3-pydantic2':
        catalog = load(ROOT / 'scenarios/s3-pydantic2/catalog.json')
        occurrences = scan(head, catalog)
        for entry in catalog:
            entry['occurrences'] = sum(o['entry'] == entry['id'] for o in occurrences)
        write(output / 'catalog.json', catalog); write(output / 'occurrences.json', occurrences)
        files = sorted({o['file'] for o in occurrences})
        candidates = []
        for file in files:
            module = file.split('/')[1] if len(file.split('/')) > 2 else 'core'
            candidates.append({'id': file + '#migration', 'file': file, 'line': min(o['line'] for o in occurrences if o['file'] == file), 'hop': 1, 'layer': 'direct', 'module': module})
        graph = {'changedSymbols': [{'id': 'requirements.txt#pydantic', 'kind': 'dependency', 'changeType': 'dependency'}], 'candidates': candidates, 'filesScanned': len(list(head.joinpath('shop').rglob('*.py'))), 'contracts': [], 'untested': [], 'testsToRun': ['tests'], 'infraImpact': impact(head, ['requirements.txt'])}
        graph['change'] = {'kind': 'dependency-upgrade', 'summary': title, 'library': 'pydantic', 'from': '1.10.13', 'to': '2.9.2'}
        verdicts = [{'id': c['id'], 'verdict': 'will_break', 'reason': 'Pydantic v2 incompatibilities in this file; see catalog entries and before.xml collection errors.', 'fix': 'Apply the recorded guide replacements.'} for c in candidates]
        proofs = []
    else:
        catalog = None
        graph = make_graph(base, head, patch)
        verdicts = load(ROOT / 'scenarios' / scenario / 'verdicts.json')
        proofs = []
        for proof in sorted((base / 'tests/uplift_proofs').glob('test_*.py')):
            id = proof.read_text(encoding='utf-8-sig').splitlines()[0].split('uplift:item ', 1)[1]
            prefix = 'tests.uplift_proofs.' + proof.stem
            b = [v for k, v in baseline['cases'].items() if k.startswith(prefix + '::')]
            h = [v for k, v in before['cases'].items() if k.startswith(prefix + '::')]
            passes, fails = bool(b) and all(x == 'passed' for x in b), bool(h) and any(x in ('failed', 'errors') for x in h)
            proofs.append({'item': id, 'testFile': 'tests/uplift_proofs/' + proof.name, 'passesOnBase': passes, 'failsOnHead': fails, 'status': 'confirmed' if passes and fails else 'unconfirmed'})
        if any(p['status'] != 'confirmed' for p in proofs):
            raise RuntimeError('Unconfirmed scenario proof: ' + scenario)
    repaired = scratch / (scenario + '-repaired'); shutil.copytree(head, repaired)
    apply(repaired, scenario)
    extra_tests = ROOT / 'scenarios' / scenario / 'after_tests'
    if extra_tests.exists():
        for test in extra_tests.glob('test_*.py'):
            shutil.copy2(test, repaired / 'tests/payments' / test.name)
    after = run_tests(interpreter, repaired, ['tests'], output, 'after')
    if after['exitCode'] or after['passed'] == 0:
        raise RuntimeError('Repair failed: ' + scenario)
    diff, changed_files, added = differences(head, repaired)
    (output / 'repair.patch').write_text(diff, encoding='utf-8', newline='\n')
    (ROOT / 'scenarios' / scenario).mkdir(parents=True, exist_ok=True)
    (ROOT / 'scenarios' / scenario / 'repair.patch').write_text(diff, encoding='utf-8', newline='\n')
    check = compliance(repaired, added)
    write(output / 'compliance.json', check)
    if check['violations']:
        raise RuntimeError('Convention violations: ' + str(check['details']))
    convention = load(ROOT / 'scenarios/conventions.json'); convention['compliance'] = {k: check[k] for k in ('checkedLines', 'violations', 'retried')}
    repairs = []
    for module in ('users', 'orders', 'payments', 'core'):
        module_files = [f for f in changed_files if f.startswith('shop/' + module + '/') or module == 'core' and (f.startswith(('shop/admin/', 'shop/notifications/')) or f in ('requirements.txt', 'shop/config.py'))]
        if not module_files:
            continue
        fixed = [c['id'] for c in graph['candidates'] if (c.get('module') == module or module == 'core' and c.get('module') in ('admin', 'notifications', 'core')) and (scenario == 's3-pydantic2' or any(p['item'] == c['id'] for p in proofs))]
        repair = {'scenario': scenario, 'module': module, 'worker': 'uplift-worker-' + module, 'filesChanged': module_files, 'fixesApplied': len(fixed), 'fixedIds': fixed, 'testsBefore': before['byModule'].get(module, {'passed': 0, 'failed': 0, 'errors': 0}), 'testsAfter': after['byModule'].get(module, {'passed': 0, 'failed': 0, 'errors': 0}), 'blocked': []}
        repairs.append(repair); write(output / ('repair-' + module + '.json'), repair)
    report = build_report(graph, verdicts, {'proofs': proofs}, repairs, {'catalog': catalog} if catalog else None, scenario, title, ['uplift-impact-analyst'] if scenario != 's3-pydantic2' else ['uplift-migration-planner'], verified=True, generated_by='bob', verification=summary(after), conventions=convention)
    report['metrics']['secondsTaken'] = round(time.perf_counter() - started, 3)
    report['metrics']['tests'] = {'before': summary(before), 'after': summary(after)}
    report['metrics']['confirmed'] = sum(a['verdict'] == 'will_break' and a['proof']['status'] == 'confirmed' for a in report['affected'])
    report['provenance'].update({'predictionSource': 'archived Bob verdicts' if scenario != 's3-pydantic2' else 'Bob migration assessment using archived guide catalog', 'repairAgent': 'bob', 'baselineSha256': tree_hash(base), 'patchSha256': hashlib.sha256(patch.read_bytes()).hexdigest(), 'verificationPython': after['pythonVersion'], 'evidencePath': 'evidence/' + scenario})
    if scenario == 's3-pydantic2':
        report['pipeline']['prove'] = 'done'
        report['provenance']['proofMethod'] = 'Same full suite on Pydantic v1 base, v2 before repairs, and v2 after repairs; no individual code proof claims.'
    else:
        result = evaluate(report, load(ROOT / 'sample-app/scenarios' / (scenario + '.expected.json')))
        report['metrics']['accuracy'] = result['accuracy']; write(output / 'accuracy.json', result)
    note = '# ' + title + '\n\nGenerated from isolated scenario copies using Bob modes. Original Bob predictions are preserved.\n\n'
    note += f"Base: {summary(baseline)}\n\nBefore repairs: {summary(before)}\n\nAfter repairs: {summary(after)}\n\n"
    note += 'Repairs:\n' + '\n'.join('- ' + f for f in changed_files) + '\n\n'
    if scenario == 's2-cents':
        note += 'The three original safe verdicts that missed dollar contracts remain safe in the historical predictions. Additional diagnostic proofs demonstrate these misses. Direct Payment fixtures now supply integer cents; output expectations remain dollars. The patch-modified API assertion is restored to its original dollar contract. DollarPayment distinguishes persisted dollars from charged cents, preventing repeated conversion.\n\n'
    note += 'Verified: all collected tests pass; no collection errors. See the raw base/before/after JSON, XML and console logs for counts and commands.\n'
    if report['migration']:
        report['migration']['releaseNotes'] = note
    from jsonschema import Draft7Validator
    Draft7Validator(load(ROOT / 'schema/report.schema.json')).validate(report)
    for folder in ('reports', 'evidence', 'dashboard/reports'):
        write(ROOT / folder / (scenario + '.json'), report)
    (ROOT / 'reports' / (scenario + '.release-notes.md')).write_text(note, encoding='utf-8')
    write(output / 'graph.json', graph); write(output / 'verdicts.json', verdicts); write(output / 'proofs.json', {'proofs': proofs}); write(output / 'conventions.json', convention)
    write(output / 'manifest.json', {'scenario': scenario, 'baseSha256': tree_hash(base), 'headSha256': tree_hash(head), 'repairedSha256': tree_hash(repaired), 'python': after['pythonVersion'], 'generatedBy': 'bob'})
    shutil.copytree(output, ROOT / 'evidence' / scenario, dirs_exist_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-python'); parser.add_argument('--v2-python')
    parser.add_argument('--scenario', choices=IDS, action='append')
    args = parser.parse_args()
    python = str(Path(args.app_python).resolve()) if args.app_python else python_in('sample-app/.venv311')
    v2 = str(Path(args.v2_python).resolve()) if args.v2_python else python_in('sample-app/.venv-v2-311')
    for executable, expected in ((python, '1'), (v2, '2')):
        version = subprocess.check_output([executable, '-c', 'import sys,pydantic; print(str(sys.version_info.major)+"."+str(sys.version_info.minor), pydantic.VERSION)'], text=True).split()
        if version[0] not in ('3.11', '3.12') or not version[1].startswith(expected + '.'):
            raise SystemExit('Wrong interpreter or Pydantic version: ' + str(version))
    with tempfile.TemporaryDirectory(prefix='uplift_reproduce_') as directory:
        scratch = Path(directory)
        for scenario, title in zip(IDS, TITLES):
            if not args.scenario or scenario in args.scenario:
                try:
                    generate(scenario, title, python, v2, scratch)
                except Exception:
                    failed = scratch / (scenario + '-evidence')
                    if failed.exists():
                        shutil.copytree(failed, ROOT / '.uplift/reproduction-failure' / scenario, dirs_exist_ok=True)
                    raise
    if not args.scenario:
        write(ROOT / 'dashboard/reports/index.json', [{'id': s, 'title': t, 'file': s + '.json'} for s, t in zip(IDS, TITLES)])
    print('Scenario evidence regenerated and verified.', flush=True)


if __name__ == '__main__':
    main()

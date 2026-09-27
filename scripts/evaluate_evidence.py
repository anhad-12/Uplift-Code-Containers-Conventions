"""Evaluate frozen predictions and publish the transparent accuracy write-up."""
from pathlib import Path
import json
from accuracy import evaluate

ROOT = Path(__file__).resolve().parent.parent


def main():
    lines = ['# Measured scenario evaluation', '', 'Original S1/S2 Bob predictions are frozen in scenarios/<id>/verdicts.json. Scenario isolation and repairs were completed using Bob modes without changing those predictions or ground truth. S2 misses remain visible. Final reports identify generatedBy=bob; legacy Bob artifacts are retained in .uplift/a8-audit/.', '', '## Results', '', '| Scenario | Predicted candidates | Confirmed predicted candidates | Fixed items | Before passed / failed / errors | After passed / failed / errors |', '| --- | --- | --- | --- | --- | --- |']
    reports = {}
    for scenario in ('s1-null-user','s2-cents','s3-pydantic2'):
        report = json.loads((ROOT/'reports'/f'{scenario}.json').read_text(encoding='utf8'))
        reports[scenario] = report
        metrics = report['metrics']; tests = metrics['tests']
        predicted = sum(a['verdict'] in ('will_break','might_break') for a in report['affected'])
        counts = lambda x: ' / '.join(str(x.get(k,0)) for k in ('passed','failed','errors'))
        lines.append(f"| {scenario} | {predicted} | {metrics['confirmed']} | {metrics['fixed']} | {counts(tests['before'])} | {counts(tests['after'])} |")
    lines += ['', 'Counts distinguish test failures from collection errors. A collection error can block several tests, so before/after totals need not match. S1 metrics.predicted also includes one affected route contract (7); the table and accuracy use only candidate ids (6). S3 uses full-suite upgrade evidence, not individually confirmed code proofs.', '']
    for scenario in ('s1-null-user','s2-cents'):
        r = reports[scenario]
        truth = json.loads((ROOT/'sample-app/scenarios'/f'{scenario}.expected.json').read_text(encoding='utf8'))
        result = evaluate(r,truth)
        if result['accuracy'] != r['metrics']['accuracy']:
            raise ValueError('Stored metrics disagree with evaluation: '+scenario)
        lines += ['## '+scenario, '', ', '.join(f'{key}: {value}' for key,value in result['accuracy'].items()), '', '| id | predicted | truth | correct? |', '| --- | --- | --- | --- |']
        byid = {x['id']:x for x in r['affected']}
        for item in truth['items']:
            verdict=byid.get(item['id'],{}).get('verdict','missing')
            broken=verdict in ('will_break','might_break')
            good=broken == (item['expected']=='will_break')
            lines.append(f"| {item['id']} | {verdict} | {item['expected']} | {'yes' if good else 'NO'} |")
        for id in result['falsePositives']:
            lines.append('- False positive: '+id)
        if scenario=='s1-null-user':
            lines += ['', 'No false positives or false negatives. All six original predictions are reproduced by passing-on-base/failing-on-head proofs, and all pass after repair.']
        else:
            lines += ['', 'Three false negatives; no false positives:', '', '- save_payment: the analyst treated passive storage as safe, overlooking the persisted dollar-unit contract.', '- post_payment: the analyst treated echoing an amount as safe, overlooking the public API dollar-unit contract.', '- payment_line: the analyst treated dictionary passthrough as unit-agnostic, overlooking the invoice dollar-unit contract.', '', 'Three post-evaluation diagnostic proofs were added for these misses. They do not turn the original safe predictions into correct predictions. Fixed items can therefore exceed predicted or confirmed-prediction counts. The original admin proof was strengthened from a loose upper bound to the exact expected dollar amount.', '', 'S2 changes direct Payment test inputs to cents while keeping dollar-output expectations. Its patch had changed the route assertion to cents; repair restores the documented original dollar contract. Stored DollarPayment and charged Payment are distinct types, so converting a stored value twice does not shrink it again. One additional post-repair regression tests this round trip and all dollar consumers; this accounts for the increased final test count.']
    lines += ['', '## S3 migration', '', 'No expected.json exists and no precision/recall is assigned. A clean Pydantic v1 baseline is run first; the same source/tests then run on Pydantic 2.9.2 before and after repair. No S1 null-user or S2 cents patch is applied. The clean baseline passes 46 tests. Repairs cover users, orders, payments, and core.', '', '| Module | Before passed / failed / errors | After passed / failed / errors |', '| --- | --- | --- |']
    for module in reports['s3-pydantic2']['migration']['modules']:
        counts=lambda x:' / '.join(str(x.get(k,0)) for k in ('passed','failed','errors'))
        lines.append(f"| {module['module']} | {counts(module['testsBefore'])} | {counts(module['testsAfter'])} |")
    lines += ['', '## Provenance and reproduction', '', '- Run `engine/.venv/Scripts/python scripts/reproduce.py` then `engine/.venv/Scripts/python scripts/evaluate_evidence.py` (use bin/python on POSIX).', '- Each evidence/<scenario>/ directory contains base/before/after logs, JUnit XML, parsed counts, input graph/verdicts/proofs, repairs, added-line convention checks, and source/patch hashes.', '- New work was completed using Bob modes. Existing Bob screenshots and commit history are historical evidence only; missing screenshots are not fabricated.', '- The old contaminated branches are preserved for audit; the reproducible isolated runner is the supported scenario execution path.', '- Docker effects are conservative instruction invalidation estimates; no build duration or actual image-layer count is claimed.', '- The app is a deliberately small synthetic fixture. These precision/recall values measure two fixed scenarios, not general performance on arbitrary repositories.', '']
    content='\n'.join(lines)
    for folder in ('.uplift','evidence','dashboard/reports'):
        dest = ROOT/folder
        dest.mkdir(parents=True, exist_ok=True)
        (dest/'eval.md').write_text(content,encoding='utf8')
    print('Evaluated S1/S2 against unchanged truth; published measured S3 counts.')


if __name__=='__main__':
    main()

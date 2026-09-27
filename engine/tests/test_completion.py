import copy
import sys
from pathlib import Path
import pytest
from uplift.report import build_report
from uplift.docker import impact
from uplift.proof import parse_junit, run_pytest


def report_args():
    return dict(graph={'changedSymbols': [], 'candidates': [{'id': 'shop/users/a.py#f', 'file': 'shop/users/a.py', 'line': 1, 'hop': 1}]}, verdicts=[{'id': 'shop/users/a.py#f', 'verdict': 'will_break'}], proofs={'proofs': [{'item': 'shop/users/a.py#f', 'status': 'confirmed', 'passesOnBase': True, 'failsOnHead': True}]}, repair_files=[], catalog=None, scenario_id='s1', title='test', bob_modes=[])


def test_actual_proof_runner_shape_merges_and_input_unchanged():
    args = report_args(); before = copy.deepcopy(args)
    result = build_report(**args)
    assert result['metrics']['confirmed'] == 1
    assert args == before


def test_false_confirmation_downgraded():
    args = report_args(); args['proofs']['proofs'][0]['passesOnBase'] = False
    result = build_report(**args)
    assert result['affected'][0]['proof']['status'] == 'unconfirmed'
    assert result['metrics']['confirmed'] == 0


def test_verification_requires_successful_measurement():
    args = report_args()
    with pytest.raises(ValueError): build_report(**args, verified=True)
    with pytest.raises(ValueError): build_report(**args, verified=True, verification={'passed': 4, 'failed': 0, 'errors': 1})
    assert build_report(**args, verified=True, verification={'passed': 4, 'failed': 0, 'errors': 0, 'exitCode': 0})['pipeline']['verify'] == 'done'


def test_cross_scenario_repair_rejected():
    args = report_args(); args['repair_files'] = [{'scenario': 's2'}]
    with pytest.raises(ValueError): build_report(**args)


def test_migration_occurrences_keep_repairs_and_proofs():
    args = report_args()
    args['repair_files'] = [{'module': 'users', 'worker': 'uplift-worker-users', 'scenario': 's1', 'fixedIds': ['shop/users/a.py#f'], 'filesChanged': ['shop/users/a.py'], 'testsAfter': {'passed': 2, 'failed': 0}, 'blocked': []}]
    args['catalog'] = [{'id': 'c', 'title': 'change', 'kind': 'api_changed'}]
    result = build_report(**args, occurrences=[{'file': 'shop/users/a.py', 'line': 1, 'enclosing': 'f', 'module': 'users'}], library='pydantic', generated_by='bob')
    assert result['metrics']['fixed'] == 1
    assert result['metrics']['confirmed'] == 1
    assert len(result['migration']['modules']) == 1
    assert result['provenance']['generatedBy'] == 'bob'


def test_skipped_is_not_passed(tmp_path):
    xml = tmp_path / 'x.xml'
    xml.write_text('<testsuite><testcase classname="tests.a" name="x"><skipped/></testcase></testsuite>')
    assert parse_junit(xml)['passed'] == 0
    assert parse_junit(xml)['cases']['tests.a::x'] == 'skipped'


def test_pytest_missing_test_is_not_success(tmp_path):
    with pytest.raises(RuntimeError):
        run_pytest(sys.executable, tmp_path, ['nonexistent.py'])


def test_docker_manifest_and_source_have_different_rebuild_ranges(tmp_path):
    (tmp_path / 'Dockerfile').write_text('FROM python:3.11\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY shop/ shop/\nCMD ["python"]\n')
    manifest = impact(tmp_path, ['requirements.txt'])[0]
    source = impact(tmp_path, ['shop/a.py'])[0]
    assert manifest['layersRebuilt'] == '2-5'
    assert source['layersRebuilt'] == '4-5'
    assert 'measuredRebuildSeconds' not in source
    assert impact(tmp_path, ['tests/test_a.py']) == []


def test_docker_multistage_dependency_and_json_copy(tmp_path):
    (tmp_path / 'Dockerfile').write_text('FROM python AS build\nCOPY ["src/", "/src/"]\nRUN build\nFROM scratch\nCOPY --from=build /src /app\n')
    result = impact(tmp_path, ['src/a.py'])
    assert [x['layersRebuilt'] for x in result] == ['2-3', '5-5']


def test_cli_report_accepts_real_proof_envelope(tmp_path):
    import json
    from typer.testing import CliRunner
    from uplift.cli import app
    args = report_args()
    for name, data in [('graph', args['graph']), ('verdicts', args['verdicts']), ('proofs', args['proofs']), ('verification', {'passed': 2, 'failed': 0, 'errors': 0, 'exitCode': 0})]:
        (tmp_path / (name + '.json')).write_text(json.dumps(data))
    result = CliRunner().invoke(app, ['report', '--graph', str(tmp_path/'graph.json'), '--verdicts', str(tmp_path/'verdicts.json'), '--proofs', str(tmp_path/'proofs.json'), '--verification', str(tmp_path/'verification.json'), '--verified', '--generated-by', 'bob', '--scenario', 's1', '--title', 'S1', '--out', str(tmp_path/'report.json')])
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path/'report.json').read_text())
    assert report['metrics']['confirmed'] == 1
    assert report['pipeline']['verify'] == 'done'
    assert report['provenance']['generatedBy'] == 'bob'

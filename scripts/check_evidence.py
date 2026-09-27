"""Check published reports against raw measurements and frozen predictions."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from jsonschema import Draft7Validator
from accuracy import evaluate
from uplift.report import risk

ROOT = Path(__file__).resolve().parent.parent


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    schema = Draft7Validator(load(ROOT/'schema/report.schema.json'))
    for sid in ('s1-null-user','s2-cents','s3-pydantic2'):
        report = load(ROOT/'reports'/f'{sid}.json')
        schema.validate(report)
        assert report == load(ROOT/'evidence'/f'{sid}.json') == load(ROOT/'dashboard/reports'/f'{sid}.json'), sid + ': published copies differ'
        assert report['scenario']['id'] == sid
        assert report['provenance']['generatedBy'] == 'codex'
        assert report['risk']['score'] == risk(report['affected'], report.get('contracts',[]), report.get('untested',[]))['score']
        assert len({a['id'] for a in report['affected']}) == len(report['affected'])
        output = ROOT/'evidence'/sid
        for phase in ('base','before','after'):
            raw = load(output/f'{phase}.json')
            counts = {'passed':0,'failed':0,'errors':0,'skipped':0}
            for case in ET.parse(output/f'{phase}.xml').iter('testcase'):
                key = 'errors' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
                counts[key] += 1
            assert all(raw[k] == value for k,value in counts.items()), (sid,phase,'JUnit mismatch')
            if phase!='base':
                assert all(report['metrics']['tests'][phase].get(k,0)==v for k,v in counts.items()), (sid,phase,'report mismatch')
        after=load(output/'after.json')
        assert after['passed']>0 and after['failed']==after['errors']==after['exitCode']==0
        assert report['pipeline']['verify']=='done'
        assert report['metrics']['fixed']==sum(a.get('repair',{}).get('status')=='fixed' for a in report['affected'])
        for item in report['affected']:
            if item['proof']['status']=='confirmed':
                assert item['proof']['passesOnBase'] and item['proof']['failsOnHead']
        if sid!='s3-pydantic2':
            frozen=load(ROOT/'scenarios'/sid/'verdicts.json');byid={a['id']:a for a in report['affected']}
            assert all(byid[v['id']]['verdict']==v['verdict'] for v in frozen), 'Historical prediction changed'
            assert evaluate(report,load(ROOT/'sample-app/scenarios'/f'{sid}.expected.json'))['accuracy']==report['metrics']['accuracy']
        else:
            assert 'accuracy' not in report['metrics']
        print('PASS',sid,'schema, copies, measured counts, risk, proofs and accuracy')


if __name__=='__main__':
    main()

"""Render neutral Hebrew summaries from validated24Oct full/default audits."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-24'
ART = ROOT / 'artifacts/poll-checks' / DAY
STRICT = ROOT / 'artifacts/strict-post-close'
read = lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    manifest = read(ART / 'before/manifest.json')
    relative = 'scripts/build-trend-summaries-2026-10-20-evening.py'
    path = ROOT / relative
    assert sha(path) == manifest['files'][relative]
    spec = importlib.util.spec_from_file_location('_reviewed_summary_renderer_20',path)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    bloc,party,current,history,snapshot,validation = [read(p) for p in [STRICT/'analysis.json',STRICT/'party-analysis.json',
        ROOT/'data/current-polls.json',ROOT/'data/poll-history.json',ROOT/'data/strict-party-trends.json',ART/'strict-validation.json']]
    assert all(d['asOf'] == DAY for d in [bloc,party,current,history,snapshot,validation])
    assert validation['passed'] and validation['status'] == 'PASS'
    assert validation['allPriorStrictCohortRowsUnchanged'] and validation['newPollsIncludedInForecast']
    for family in ['inputHashes','sourceEvidenceHashes','candidateHashes','preservedCodeHashes','exactArithmeticRepairInputHashes']:
        for rel,digest in validation[family].items():
            assert sha(ROOT/rel) == digest, ('Validated input changed',rel)
    default_path = ROOT/'data/strict-party-trends-without-channel14.json'
    default = read(default_path)
    assert default['asOf'] == DAY and default['includeChannel14'] is False
    matches = [p for p in (STRICT/'without-channel14'/DAY).glob('*/party-analysis.json') if sha(p) == default['provenance']['analysisSha256']]
    assert len(matches) == 1
    audit_path = matches[0]
    audit = read(audit_path)
    receipt = read(audit_path.parent/'validation.json')
    inputs = read(audit_path.parent/'inputs-manifest.json')
    assert receipt['status'] == 'PASS' and receipt['asOf'] == inputs['asOf'] == DAY
    assert receipt['snapshotSha256'] == sha(default_path) and receipt['analysisSha256'] == sha(audit_path)
    assert default['provenance']['sourceAnalysisSha256'] == sha(STRICT/'party-analysis.json')
    for rel,digest in inputs['sourceHashes'].items():
        assert sha(ROOT/rel) == digest
    assert bloc['cohort'] == party['cohort']
    for name,title,doc,is_party in [('summary-he.md','מגמות הגושים',bloc,False),('party-summary-he.md','מגמות המפלגות',party,True)]:
        text = renderer.make_summary(title,doc,bloc,party,current,history,snapshot,validation,default,audit,is_party)
        text = text.replace('artifacts/poll-checks/2026-10-20-evening/','artifacts/poll-checks/2026-10-24/')
        (STRICT/name).write_text(text,encoding='utf-8')
        print('Built',name,'from actual',DAY,'validated audits')


if __name__ == '__main__':
    main()

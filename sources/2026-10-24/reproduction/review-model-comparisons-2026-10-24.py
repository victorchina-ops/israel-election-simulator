"""Reuse reviewed arithmetic checks with dynamic24Oct dates and cohort counts."""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'artifacts/poll-checks/2026-10-24'
read = lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
original = ROOT/'scripts/review-model-comparisons-2026-10-20-evening.py'
manifest = read(ART/'before/manifest.json')
assert hashlib.sha256(original.read_bytes()).hexdigest() == manifest['files'][original.relative_to(ROOT).as_posix()]
source = original.read_text(encoding='utf-8-sig')
def patch(old,new):
    global source
    assert source.count(old) == 1, (old,source.count(old))
    source = source.replace(old,new,1)
patch("ART=ROOT/'artifacts/poll-checks/2026-10-20-evening'","ART=ROOT/'artifacts/poll-checks/2026-10-24'")
patch("plan['asOf']=='2026-10-20'","plan['asOf']=='2026-10-24'")
patch("assert set(candidates)=={'maagar_mochot','direct_polls','next_data'}","assert set(candidates)=={s['pollsterId'] for s in plan['polls']}")
patch("assert {d['key'] for d in report['controlDifferences']}==set()","assert {d['key'] for d in report['controlDifferences']}==({'asOf'} if before_input['current']['asOf']!=after_input['current']['asOf'] else set())")
patch("cfg['asOf']==source['current']['asOf']=='2026-10-20'","cfg['asOf']==source['current']['asOf']==inputs[phase]['current']['asOf']")
patch("assert len(active)==7 and len(source['current']['polls'])==8","assert len(active)==checkpoint['activePollCount']-1 and len(source['current']['polls'])==checkpoint['activePollCount']")
patch("assert len(set(ids))==7 and 'next_data' not in ids","assert len(set(ids))==len(active) and 'next_data' not in ids")
patch("assert len(source['history']['polls'])==135","assert len(source['history']['polls'])==len(after_input['history']['polls'])")
patch("assert poll['date']=='2026-10-20'","assert poll['date']==candidate['date']")
patch("assert len(source['history']['polls'])==132","assert len(source['history']['polls'])==len(before_input['history']['polls'])")
patch("assert len(weights)==7 and [p['pollsterId'] for p in weights]==ids","assert len(weights)==len(active) and [p['pollsterId'] for p in weights]==ids")
patch("for i in range(7))","for i in range(len(ids)))")
patch("for i in range(7) for j in range(i+1,7))","for i in range(len(ids)) for j in range(i+1,len(ids)))")
patch("'asOf':'2026-10-20'","'asOf':'2026-10-24'")
patch("'all3SourceCandidatesBound':True,'actualActiveInstitutes':7","'allReviewedSourceCandidatesBound':len(candidates)==len(plan['polls']),'actualActiveInstitutes':len(ids)")
if __name__ == '__main__':
    exec(compile(source,str(original),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})

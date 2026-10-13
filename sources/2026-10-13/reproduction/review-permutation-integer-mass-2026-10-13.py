"""Bind the narrowly scoped integer overflow repair to frozen originals and regression evidence."""
from pathlib import Path
import ast,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-13'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=read(ART/'before/manifest.json')
approved={
 'artifacts/strict-post-close/compressed_searchsorted_exact.py':{'_cartesian_sums','compressed_searchsorted_tail'},
 'artifacts/strict-post-close/independent-compressed-counts.py':{'sums_with_multiplicities','direct_tail_counts'},
}
review=[]
for relative,allowed in approved.items():
    old=ART/'before'/relative;current=ROOT/relative
    assert sha(old)==manifest['files'][relative]
    before=ast.parse(old.read_text(encoding='utf-8-sig'));after=ast.parse(current.read_text(encoding='utf-8-sig'))
    assert len(before.body)==len(after.body)
    changed=[]
    for a,b in zip(before.body,after.body):
        if ast.dump(a)!=ast.dump(b):
            assert isinstance(a,ast.FunctionDef) and isinstance(b,ast.FunctionDef) and a.name==b.name in allowed
            changed.append(a.name)
    assert set(changed)==allowed
    review.append({'path':relative,'beforeSha256':sha(old),'afterSha256':sha(current),'changedFunctions':changed})
log=ART/'integer-mass-tests-final.txt'
body=log.read_text(encoding='utf-8-sig');assert 'Ran 5 tests' in body and body.rstrip().endswith('OK')
analysis=read(ROOT/'artifacts/strict-post-close/analysis.json')
assert analysis['asOf']=='2026-10-13'
total=int(analysis['primary']['exactCounting']['nPermutationsExact'])
assert total>2**63-1
output={'status':'PASS','asOf':'2026-10-13','scope':'Exact multiplicity storage and tail accumulation only; statistic, null, tolerance, weights and original sources unchanged.',
 'reason':'The updated factorial permutation universe exceeds signed64; previous bounded array accumulation overflowed.',
 'nPermutationsExact':str(total),'signed64Maximum':str(2**63-1),'helpers':review,
 'regressionTests':5,'testLogSha256':sha(log),'testScriptSha256':sha(ROOT/'scripts/test-permutation-integer-mass-2026-10-13.py'),
 'testedCases':['ordinary counts','large counts below signed64','complete universe above signed64','one Cartesian half above signed64','zero observed whole-universe tail'],
 'frozenOriginalsPreserved':True,'primaryAndIndependentAlgorithmsRemainSeparate':True}
dest=ART/'integer-mass-repair-review.json';assert not dest.exists()
dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(output))

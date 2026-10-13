"""Review the exact-counter optimization against the immutable pre-update code."""
from pathlib import Path
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/poll-checks/2026-10-13'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=read(ART/'before/manifest.json');stage1=read(ART/'integer-mass-repair-review.json')
tests=read(ART/'independent-sweep-tests.json');assert tests['status']=='PASS' and tests['tests']==50
functions={
 'artifacts/strict-post-close/compressed_searchsorted_exact.py':{'_cartesian_sums','compressed_searchsorted_tail'},
 'artifacts/strict-post-close/independent-compressed-counts.py':{'sums_with_multiplicities','direct_tail_counts'}}
descriptions={'artifacts/audit-strict-full-series-2026-09-28.py':1,'artifacts/strict-post-close/party-independent.py':2}
rows=[]
for relative in [*functions,*descriptions]:
    old=ART/'before'/relative;new=ROOT/relative;assert sha(old)==manifest['files'][relative]
    a=ast.parse(old.read_text(encoding='utf-8-sig'));b=ast.parse(new.read_text(encoding='utf-8-sig'))
    changes=[]
    if relative in functions:
        assert len(a.body)==len(b.body)
        for old_node,new_node in zip(a.body,b.body):
            if ast.dump(old_node)==ast.dump(new_node):continue
            if isinstance(old_node,ast.Expr) and isinstance(new_node,ast.Expr):
                assert isinstance(old_node.value,ast.Constant) and isinstance(new_node.value,ast.Constant)
                assert isinstance(old_node.value.value,str) and isinstance(new_node.value.value,str)
                changes.append('module documentation');continue
            assert isinstance(old_node,ast.FunctionDef) and isinstance(new_node,ast.FunctionDef)
            assert old_node.name==new_node.name in functions[relative]
            changes.append(old_node.name)
        assert set(changes)-{'module documentation'}==functions[relative]
    else:
        old_nodes=list(ast.walk(a));new_nodes=list(ast.walk(b));assert len(old_nodes)==len(new_nodes)
        for old_node,new_node in zip(old_nodes,new_nodes):
            if isinstance(old_node,ast.Constant) and isinstance(new_node,ast.Constant) and old_node.value!=new_node.value:
                assert isinstance(old_node.value,str) and isinstance(new_node.value,str)
                assert old_node.value.startswith('Independent') and new_node.value.startswith('Independent')
                assert 'two-pointer' in new_node.value
                changes.append('method description only');new_node.value=old_node.value
        assert len(changes)==descriptions[relative]
        assert ast.dump(a)==ast.dump(b),'Any computation change is outside scope'
    rows.append({'path':relative,'beforeSha256':sha(old),'afterSha256':sha(new),'changes':changes})
assert rows[0]['afterSha256']==stage1['helpers'][0]['afterSha256']
assert 'searchsorted(' not in (ROOT/'artifacts/strict-post-close/independent-compressed-counts.py').read_text(encoding='utf-8')
output={'status':'PASS','asOf':'2026-10-13','scope':'Same exact null/statistic/multiplicities/tolerance/weights; independent inclusive tail evaluation uses monotone pointer sweep instead of dense Cartesian masks.',
 'helpers':rows,'primaryAndIndependentAlgorithmsRemainSeparate':True,'frozenOriginalsPreserved':True,
 'nPermutationsExact':stage1['nPermutationsExact'],'stage1ReviewSha256':sha(ART/'integer-mass-repair-review.json'),
 'supersededIntermediateIndependentHelperSha256':stage1['helpers'][1]['afterSha256'],
 'regressionTests':50,'testReceiptSha256':sha(ART/'independent-sweep-tests.json'),
 'testScriptSha256':sha(ROOT/'scripts/test-independent-sweep-2026-10-13.py'),
 'registeredTolerance':1e-12,'tailInclusivity':'abs(permuted)>=abs(observed)-tolerance',
 'independentReview':'Root and ingestion reviewer read pointer inequalities and mass accounting; source reviewer compared 50 cases to frozen dense/direct/analytic references.'}
dest=ART/'independent-sweep-repair-review.json';assert not dest.exists()
dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','helpers':rows,'tests':50}))

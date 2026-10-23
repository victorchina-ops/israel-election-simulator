"""Independent review: do not edit the backend or any canonical audit."""
from pathlib import Path
from collections import Counter
from itertools import permutations
import importlib.util,hashlib,json,math,sys

ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'artifacts/poll-checks/2026-10-20'
HERE=Path(__file__).parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
import exact_scalar_marginals_2026_10_20 as backend

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compare(old,new,path=''):
    if isinstance(old,dict):
        assert isinstance(new,dict) and old.keys()==new.keys(),path
        for key in old:compare(old[key],new[key],path+'/'+key)
    elif isinstance(old,list):
        assert isinstance(new,list) and len(old)==len(new),path
        for i,(a,b) in enumerate(zip(old,new)):compare(a,b,path+'/'+str(i))
    elif isinstance(old,(int,float)) and not isinstance(old,bool):
        if isinstance(old,int) and isinstance(new,int):assert old==new,(path,old,new)
        else:assert math.isclose(old,new,rel_tol=0,abs_tol=1e-12),(path,old,new)
    else:assert old==new,(path,old,new)

assert sha(ROOT/'scripts/exact_scalar_marginals_2026_10_20.py')=='ac501943965cfeaba1105f1e2f06a792e4a4183c87210757b4cd531ee75cc035'
assert sha(ROOT/'scripts/run-exact-trends-2026-10-20.py')=='05c5f67926a5b5bb936e24266d0d9eb5d92753cc9f98f046a68ad6c4e7d9f85a'
toy=read(HERE/'toy-equivalence.json');archive=read(HERE/'archive19-equivalence.json')
assert toy['status']==archive['status']=='PASS'
assert sha(HERE/'toy-equivalence.json')=='13ac3bbdaa181f81bb9c0470524401eb10095616bbe618a9e312cd7bb055e13a'
assert sha(HERE/'archive19-equivalence.json')=='0964a717fb92c33366a39d1e0f3107cd6cbf173ea4f62420bc3aa53d059b624a'
assert toy['backendSha256']==archive['backendSha256']==sha(Path(backend.__file__))
assert archive['wrapperSha256']==sha(ROOT/'scripts/run-exact-trends-2026-10-20.py')
assert toy['validatorSha256']==archive['validatorSha256']==sha(ROOT/'scripts/validate-exact-scalar-backend-2026-10-20.py')
assert archive['checkpointManifestSha256']==sha(ART/'before/manifest.json')
backend.verify_frozen_counters()

checks=[]
for n in range(2,8):
    times=[(i*i+i%3)/2 for i in range(n)]
    values=[(i*5)%4-2 for i in range(n)]
    u=tuple(round(2*t) for t in times)
    c=[sum(ui-uj for uj in u) for ui in u]
    oracle=Counter(sum(ci*yi for ci,yi in zip(c,order)) for order in permutations(values))
    a=backend.unique_distribution(u,tuple(sorted(values)))
    b=backend.dp_distribution(u,tuple(sorted(values)))
    assert dict(a[0])==dict(b[0])==dict(oracle)
    assert a[1]==b[1]==sum(oracle.values())==math.factorial(n)
    denom=sum((u[i]-u[j])**2 for i in range(n) for j in range(i))
    assert a[2]==b[2]==denom
    for order in [values,list(reversed(values))]:
        average=sum(times)/n
        ols=7*sum((t-average)*y for t,y in zip(times,order))/sum((t-average)**2 for t in times)
        score=sum(ci*y for ci,y in zip(c,order))
        assert math.isclose(ols,14*score/denom,rel_tol=0,abs_tol=1e-12)
    checks.append({'n':n,'exactMass':str(a[1]),'uniqueScores':len(oracle),'labeledBruteForceMatchesBothBuilders':True})

# Raw single-block mass itself exceeds signed64; there are only21 unique assignments.
n=21;u=tuple(range(n));values=tuple([0]*20+[1])
a=backend.unique_distribution(u,values);b=backend.dp_distribution(u,values)
expected=Counter({n*ui-sum(u):math.factorial(20) for ui in u})
assert dict(a[0])==dict(b[0])==dict(expected)
assert a[1]==b[1]==math.factorial(21)>2**63-1
block=backend.score_blocks([x/2 for x in u],values)[0]
assert block.multiplicities.dtype==object
assert sum(int(x) for x in block.multiplicities)==math.factorial(21)
assert all(type(mass) is int for _,mass in a[0])
assert backend.individual_pvalues([block],[0])[0]==1

bench=HERE/'archive19';base=ART/'before/artifacts/strict-post-close'
for name in ['analysis.json','party-analysis.json']:
    old,new=read(base/name),read(bench/name)
    for key in ['cohort','normalizedHistoricalWeights','closure','primary','publicationDateSensitivity']:
        compare(old[key],new[key],name+'/'+key)
    for axis in ['primary','publicationDateSensitivity']:
        assert old[axis]['exactCounting']['extremeCountsExact']==new[axis]['exactCounting']['extremeCountsExact']
for name in ['independent-strict-numeric-audit.json','party-independent.json']:
    old,new=read(base/name),read(bench/name)
    for key in old:
        if name=='party-independent.json' and key=='cohortSha256':
            assert new[key]==sha(bench/'analysis.json')
        else:compare(old[key],new[key],name+'/'+key)
for name,digest in archive['benchmarkLineageHashes'].items():
    assert sha(bench/name)==digest
    row=read(bench/name)
    assert row['frozenAnalyzerSha256']==sha(ROOT/row['frozenAnalyzer'])
    assert row['scalarBackendSha256']==sha(Path(backend.__file__))
    assert row['wrapperSha256']==sha(ROOT/'scripts/run-exact-trends-2026-10-20.py')
    assert row['inputHistorySha256']==sha(ART/'before/data/poll-history.json')
    assert row['outputSha256']==sha(bench/row['outputFile'])

report={
 'status':'PASS','asOf':'2026-10-20','reviewer':'independent-c13-source-agent',
 'backendSha256':sha(Path(backend.__file__)),'wrapperSha256':sha(ROOT/'scripts/run-exact-trends-2026-10-20.py'),
 'toyProofSha256':sha(HERE/'toy-equivalence.json'),'archive19ProofSha256':sha(HERE/'archive19-equivalence.json'),
 'independentExhaustiveChecks':checks,
 'singleBlockBeyondInt64':{'n':n,'massExact':str(math.factorial(n)),'uniqueAssignments':21,'objectMassArrayVerified':True,'bothBuildersAgreeWithAnalyticHistogram':True},
 'mathematicalReview':{
  'null':'Marginal distribution for each tested outcome equals projecting the same complete-vector within-institute time-permutation null. No cross-outcome maximum or joint-tail statistic is substituted.',
  'multiplicity':'Each distinct scalar assignment represents product(frequency!) labeled permutations; primary streams assignments and restores this constant factor. Independent DP instead multiplies each branch by remaining labeled choices, with factorial suffix for a sole remaining outcome.',
  'statistic':'With u=2t, c_i=n*u_i-sum(u), weekly OLS slope is14*sum(c_i*y_i)/(n*sum(u_i^2)-sum(u_i)^2). Independent pairwise-square denominator equals the same quantity.',
  'independence':'Primary unique-assignment recursion and independent remaining-count/score DP use separate count recurrences; frozen combined tails still use searchsorted versus direct monotone-sweep algorithms. Common input validation and class carrier do not generate either recurrence.',
  'tolerance':'Frozen combined tails retain1e-12 inclusive cutoff. Primary individual1e-12 and legacy independent-party1e-10 are preserved by exact textual substitutions.',
  'weightsCohortBhSignFlips':'Frozen analyzers pinned by SHA; wrapper substitutions replace distribution construction and output/input destinations only, preserving statistic, fieldwork cohort, weights, BH families and sign flips.',
  'mass':'Python integer histogram counts and totals; object multiplicity arrays whenever rawmass exceeds signed64; frozen combined counters promote products and tail accumulation beyond signed64.'},
 'archive19AllIndividualAndOverallPqBothAxesAgree':True,'archive19ExactTailIntegerStringsAgree':True,'archive19CohortWeightsEffectsAgree':True,
 'frozenCodeNotModified':True,'canonicalDataNotModifiedByReviewer':True,'reviewScriptSha256':sha(Path(__file__))
}
path=HERE/'independent-backend-review.json';content=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert not path.exists() or path.read_bytes()==content
path.write_bytes(content)
print(json.dumps({'status':'PASS','receipt':path.relative_to(ROOT).as_posix(),'sha256':sha(path)},ensure_ascii=False))

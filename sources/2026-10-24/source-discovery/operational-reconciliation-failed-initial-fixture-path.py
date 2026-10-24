
"""Small negative/positive reconciliation regressions; no score or tail counters."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[4]
DAY='2026-10-24'
ART=ROOT/'artifacts/poll-checks'/DAY
BOUND=ART/'numeric-boundaries'
OUT=BOUND/'operational-reconciliation-r1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    relative='scripts/verify-operational-tail-reconciliation-2026-10-24-r1.py'
    spec=importlib.util.spec_from_file_location('_fixture_operational24',ROOT/relative)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    results=[]
    def rejected(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):
            results.append({'id':label,'expected':'REJECT','actual':'REJECT'})
        else:raise AssertionError(('Mutation accepted',label))
    for name in ['bloc-coalition','bloc-opposition','party-yashar']:
        proof=read(BOUND/(name+'-band-diagnosis.json'))
        expected={k:proof[k] for k in ['primaryObservedHex','independentObservedHex','primaryExtremeCountExact','independentExtremeCountExact','totalExact','inputHashes','kind']}
        expected['identity']=proof['outcome']
        assert len(mod.validate_four_counts(proof,expected))==4
        results.append({'id':name+'-actual-four-counts','expected':'ACCEPT','actual':'ACCEPT'})
        mutations=[]
        for key in mod.COUNT_KEYS:
            mutations.append((key,lambda d,k=key:d.__setitem__(k,str(int(d[k])+1))))
        for i in range(4):
            mutations.append(('signed-delta-'+str(i),lambda d,j=i:d['screening']['signedDifferencesFromAdditionOwn'].__setitem__(j,str(int(d['screening']['signedDifferencesFromAdditionOwn'][j])+1))))
        for key in proof['signedCountDecomposition']:
            mutations.append(('decomposition-'+key,lambda d,k=key:d['signedCountDecomposition'].__setitem__(k,str(int(d['signedCountDecomposition'][k])+1))))
        for key in ['primaryExtremeCountExact','independentExtremeCountExact','totalExact']:
            mutations.append(('anchor-'+key,lambda d,k=key:d.__setitem__(k,str(int(d[k])+1))))
        mutations.extend([
            ('old-date',lambda d:d.__setitem__('asOf','2026-10-23')),
            ('stale-input',lambda d:d['inputHashes'].__setitem__('data/poll-history.json','0'*64)),
            ('false-common-equality',lambda d:d.__setitem__('originalDirectCommonThresholdIntegerMatch',not d['originalDirectCommonThresholdIntegerMatch'])),
            ('false-operational-anchor',lambda d:d.__setitem__('commonSubtractionPredicateIntegerMatch',False)),
            ('false-own-anchor',lambda d:d.__setitem__('originalDirectOwnThresholdIntegerMatch',False)),
            ('false-status',lambda d:d.__setitem__('status','PASS' if d['status']=='INVESTIGATE' else 'INVESTIGATE')),
            ('tolerance',lambda d:d.__setitem__('toleranceUnchanged',1e-11)),
            ('primary-cutoff',lambda d:d.__setitem__('primaryCutoffHex','0x1.0p-1')),
            ('independent-cutoff',lambda d:d.__setitem__('independentCutoffHex','0x1.0p-1')),
            ('partial-screen',lambda d:d['screening'].__setitem__('aRowsExhaustivelyScreened',1)),
            ('half-mass',lambda d:d['rawHalfMasses'].__setitem__(0,'1')),
            ('p-effect-float',lambda d:d.__setitem__('probabilityDifference',0)),
            ('frozen-output-mutated',lambda d:d.__setitem__('outputsOrFrozenHelpersModified',True)),
            ('support-identity-unproved',lambda d:d.__setitem__('allScalarSupportsAndLabeledMassesEqual',False)),
            ('screening-proof-missing',lambda d:d.__setitem__('allPairsOutsideOutwardBandsProvablyAgree',False)),
            ('witness-predicate',lambda d:d['screening']['witnesses'][0]['predicates'].__setitem__(0,9)),
        ])
        for label,mutation in mutations:
            value=copy.deepcopy(proof);mutation(value)
            rejected(name+'-'+label,lambda v=value:mod.validate_four_counts(v,expected))
    # The actual runtime gate checks current dated source hashes, not a permissive marker.
    proposal=read(OUT/'proposal.json')
    fake_gate={'status':'PASS_SOURCE_GATE','asOf':DAY,'adaptedFiles':proposal['adaptedFiles'],
        'baseFiles':proposal['baseFiles'],'regressionFixturesSha256':'fixture-proof',
        'checks':{'sourceExact':True}}
    oldread,oldsha=mod.read,mod.sha
    def gate_case(value,fixture_status='PASS'):
        gatepath=BOUND/'operational-reconciliation-r1/independent-source-review.json'
        fixturepath=OUT/'regression-fixtures.json'
        mod.read=lambda p:value if p==gatepath else {'status':fixture_status,'actualCountersExecuted':False}
        mod.sha=lambda p:'fixture-proof' if p==fixturepath else oldsha(p)
        try:return mod.source_gate()
        finally:mod.read,mod.sha=oldread,oldsha
    gate_case(copy.deepcopy(fake_gate));results.append({'id':'hash-bound-source-gate-positive','expected':'ACCEPT','actual':'ACCEPT'})
    for label,mutation in [
        ('gate-old-date',lambda d:d.__setitem__('asOf','2026-10-23')),
        ('gate-false-status',lambda d:d.__setitem__('status','PASS')),
        ('gate-stale-adapter',lambda d:d['adaptedFiles'].__setitem__(relative,'0'*64)),
        ('gate-stale-original-validator',lambda d:d['baseFiles'].__setitem__('scripts/validate-strict-trends-2026-10-24.py','0'*64)),
        ('gate-empty-checks',lambda d:d.__setitem__('checks',{})),
        ('gate-failed-check',lambda d:d['checks'].__setitem__('sourceExact',False)),
        ('gate-stale-fixture-hash',lambda d:d.__setitem__('regressionFixturesSha256','bad')),
    ]:
        value=copy.deepcopy(fake_gate);mutation(value);rejected(label,lambda v=value:gate_case(v))
    rejected('gate-failed-fixtures',lambda:gate_case(copy.deepcopy(fake_gate),'FAIL'))
    result={'status':'PASS','asOf':DAY,'actualCountersExecuted':False,
        'scope':'Pure arithmetic and isolated source-gate mutations only; no actual source gate or canonical writes',
        'testScriptSha256':sha(Path(__file__)),'verifierSha256':sha(ROOT/relative),
        'testCount':len(results),'positiveTests':sum(r['actual']=='ACCEPT' for r in results),
        'rejectionTests':sum(r['actual']=='REJECT' for r in results),'results':results}
    output=OUT/'regression-fixtures.json';assert not output.exists()
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='results'}))


if __name__=='__main__':main()


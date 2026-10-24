"""Fresh24Oct hash-bound verification of all four original operational tail predicates.

No counters execute and no p/q, statistic or fixed1e-12 decision threshold changes.
Original common-addition mismatches and INVESTIGATE diagnostics remain explicit.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-24'
ART=ROOT/'artifacts/poll-checks'/DAY
BOUND=ART/'numeric-boundaries'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()



COUNT_KEYS=['subtractionAtPrimaryObservedCountExact','directAtPrimaryObservedCountExact',
    'subtractionAtOwnObservedCountExact','directAtOwnObservedCountExact']
KIND='exact-operational-predicate-reconciliation'


def validate_four_counts(proof, expected):
    """Pure exact checks: neither a generic epsilon exception nor a counter."""
    assert proof['asOf']==DAY
    assert proof['kind']==expected['kind'] and proof['outcome']==expected['identity']
    for key in ['primaryObservedHex','independentObservedHex','primaryExtremeCountExact',
                'independentExtremeCountExact','totalExact']:
        assert proof[key]==expected[key],key
    for rel,digest in expected['inputHashes'].items():assert proof['inputHashes'][rel]==digest
    assert proof['toleranceUnchanged']==1e-12
    pc,ic,total=[int(expected[k]) for k in ['primaryExtremeCountExact','independentExtremeCountExact','totalExact']]
    assert 0<=pc<=total and 0<=ic<=total and pc!=ic
    pobs,iobs=[float.fromhex(expected[k]) for k in ['primaryObservedHex','independentObservedHex']]
    assert proof['primaryCutoffHex']==(abs(pobs)-1e-12).hex()
    assert proof['independentCutoffHex']==(abs(iobs)-1e-12).hex()
    delta=[int(v) for v in proof['screening']['signedDifferencesFromAdditionOwn']]
    assert len(delta)==4 and delta[3]==0
    actual=[int(proof[k]) for k in COUNT_KEYS]
    assert actual==[ic+v for v in delta]
    sp,dp,si,own=actual
    assert sp==pc and own==ic
    assert all(0<=v<=total for v in actual)
    assert proof['commonSubtractionPredicateIntegerMatch'] is True
    assert proof['originalDirectOwnThresholdIntegerMatch'] is True
    assert proof['originalDirectCommonThresholdIntegerMatch'] is (dp==pc)
    assert proof['status']==('PASS' if dp==pc else 'INVESTIGATE')
    expected_decomposition={'predicateAtPrimary':str(dp-sp),'directObservedShift':str(own-dp),
        'subtractionObservedShift':str(si-sp),'predicateAtIndependent':str(own-si),
        'totalDifference':str(ic-pc)}
    assert proof['signedCountDecomposition']==expected_decomposition
    assert (dp-sp)+(own-dp)==(si-sp)+(own-si)==ic-pc
    assert proof['probabilityDifference']==(ic-pc)/total
    assert proof['outputsOrFrozenHelpersModified'] is False
    for flag in ['allFourOriginalPredicatesPreserved','allPairsOutsideOutwardBandsProvablyAgree',
        'allScalarSupportsAndLabeledMassesEqual','screeningUsesOutwardCutoffNeighborsBeforeOutwardSubtraction',
        'screeningPaddingChangesNoDecisionThreshold']:
        assert proof[flag] is True,flag
    assert proof['screening']['aRowsExhaustivelyScreened']==proof['halfSizes'][0][0]
    assert math.prod(int(v) for v in proof['rawHalfMasses'])==total
    assert 0<=len(proof['screening']['witnesses'])<=int(proof['screening']['changedPairs'])<=int(proof['screening']['candidatePairsDirectlyEvaluated'])
    for witness in proof['screening']['witnesses']:
        a,b=float.fromhex(witness['aHex']),float.fromhex(witness['bHex'])
        cp,ci=[float.fromhex(proof[k]) for k in ['primaryCutoffHex','independentCutoffHex']]
        sub=lambda c:int(b>=c-a)+int(b<=-c-a)
        add=lambda c:int(a+b>=c)+int(a+b<=-c)
        assert witness['predicates']==[sub(cp),add(cp),sub(ci),add(ci)]
        assert int(witness['aMass'])>0 and int(witness['bMass'])>0
    return actual


def source_gate():
    path=BOUND/'operational-reconciliation-r1/independent-source-review.json'
    gate=read(path)
    assert gate['status']=='PASS_SOURCE_GATE' and gate['asOf']==DAY
    for rel,digest in gate['adaptedFiles'].items():assert sha(ROOT/rel)==digest
    assert gate['adaptedFiles'][Path(__file__).resolve().relative_to(ROOT).as_posix()]==sha(Path(__file__))
    assert sha(BOUND/'operational-reconciliation-r1/regression-fixtures.json')==gate['regressionFixturesSha256']
    fixtures=read(BOUND/'operational-reconciliation-r1/regression-fixtures.json')
    assert fixtures['status']=='PASS' and fixtures['actualCountersExecuted'] is False
    for rel,digest in gate['baseFiles'].items():assert sha(ROOT/rel)==digest
    assert gate['checks'] and all(v is True for v in gate['checks'].values())
    return path,gate


def verify(kind, identity):
    self_path=Path(__file__).resolve();source_gate_path,gate_value=source_gate()
    pipeline=read(ART/'pipeline-source-compatibility/independent-root-review.json')
    assert pipeline['status']=='PASS_SOURCE_GATE' and pipeline['asOf']==DAY
    assert pipeline['proposalSha256']==sha(ART/'pipeline-source-compatibility/proposal.json')
    reviewed={r['candidate']:r['candidateSha256'] for r in pipeline['reviewedFiles']}
    validator='scripts/validate-strict-trends-2026-10-24.py';promoter='scripts/promote-strict-validation-2026-10-24.py'
    assert sha(ROOT/validator)==reviewed[validator]==gate_value['baseFiles'][validator]
    assert sha(ROOT/promoter)==reviewed[promoter]==gate_value['baseFiles'][promoter]
    path=BOUND/(kind+'-'+identity+'-band-diagnosis.json');proof=read(path)
    review_path=BOUND/'operational-reconciliation-r1/independent-execution-review.json';review=read(review_path)
    assert review['status']=='PASS' and review['validationKind']==KIND and proof['asOf']==review['asOf']==DAY
    assert proof['kind']==kind and proof['outcome']==identity
    assert review['diagnosisHashes'][path.name]==sha(path)
    assert review['reproducerSha256']==proof['reproducerSha256']
    assert review['inputHashes']==proof['inputHashes']
    assert review['checks'] and all(v is True for v in review['checks'].values())
    assert review['pOrQChanged'] is False and review['outputsOrFrozenHelpersModified'] is False
    assert review['heavyCountersExecutedByReviewer'] is False
    assert review['sourceGateSha256']==sha(source_gate_path)
    assert review['operationalCounts'][path.name]=={k:proof[k] for k in COUNT_KEYS}
    assert review['signedCountDecompositions'][path.name]==proof['signedCountDecomposition']
    assert review['commonAdditionMatchesPrimary'][path.name] is proof['originalDirectCommonThresholdIntegerMatch']
    assert set(review['diagnosisHashes'])=={'bloc-coalition-band-diagnosis.json','bloc-opposition-band-diagnosis.json','bloc-opposition_raam-band-diagnosis.json','party-yashar-band-diagnosis.json'}
    for basename,digest in review['diagnosisHashes'].items():assert sha(BOUND/basename)==digest
    reproducer=ROOT/proof['reproducerPath'];assert sha(reproducer)==proof['reproducerSha256']
    gate_path=BOUND/'band-source-review-r1/independent-source-review.json';gate=read(gate_path)
    assert gate['status']=='PASS_SOURCE_GATE' and gate['asOf']==DAY
    assert gate['scriptSha256']==proof['reproducerSha256']==review['reproducerSha256']
    assert sha(gate_path)==proof['sourceReviewSha256'] and gate['fixturesSha256']==proof['fixturesSha256']
    assert proof['toleranceUnchanged']==1e-12 and proof['outputsOrFrozenHelpersModified'] is False
    for flag in ['allFourOriginalPredicatesPreserved','allPairsOutsideOutwardBandsProvablyAgree',
            'allScalarSupportsAndLabeledMassesEqual','screeningUsesOutwardCutoffNeighborsBeforeOutwardSubtraction',
            'screeningPaddingChangesNoDecisionThreshold']:
        assert proof[flag] is True
    for rel,digest in proof['inputHashes'].items():assert sha(ROOT/rel)==digest
    paths=['data/current-polls.json','data/poll-history.json','data/strict-party-trends.json',
        'data/calibration.json','data/parties.json','artifacts/strict-post-close/analysis.json',
        'artifacts/strict-post-close/party-analysis.json','artifacts/strict-post-close/independent-strict-numeric-audit.json',
        'artifacts/strict-post-close/party-independent.json','artifacts/poll-checks/'+DAY+'/source-plan.json',
        'artifacts/poll-checks/'+DAY+'/ingestion-validation.json',
        *['artifacts/strict-post-close/'+n for n in ['lazar-fieldwork.json','n12-kan-c13-fieldwork.json',
        'c14-i24-fieldwork.json','c16-tatika-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']]]
    hashes={r:sha(ROOT/r) for r in paths}
    for rel,digest in hashes.items():
        if rel in proof['inputHashes']:assert proof['inputHashes'][rel]==digest
    p=read(ROOT/paths[5 if kind=='bloc' else 6]);audit=read(ROOT/paths[7 if kind=='bloc' else 8])
    assert p['asOf']==DAY
    key,values=('group','groups') if kind=='bloc' else ('partyId','parties')
    j=next(i for i,r in enumerate(p['primary']['overall']) if r[key]==identity);row=p['primary']['overall'][j]
    if kind=='bloc':ownobs=float(audit['slopes'][j]);ic=int(audit['countsExact'][j]);total=int(audit['totalExact'])
    else:
        other=next(r for r in audit['overall'] if r['partyId']==identity)
        ownobs=float(other['slopePerWeek']);ic=int(other['extremeCountExact']);total=int(audit['nPermutationsExact'])
    pc=int(p['primary']['exactCounting']['extremeCountsExact'][j]);assert pc!=ic
    assert int(p['primary']['exactCounting']['nPermutationsExact'])==total
    expected={'primaryObservedHex':float(row['slopePerWeek']).hex(),'independentObservedHex':ownobs.hex(),
        'primaryExtremeCountExact':str(pc),'independentExtremeCountExact':str(ic),'totalExact':str(total)}
    assert all(proof[k]==v for k,v in expected.items())
    assert proof['primaryCutoffHex']==(abs(float(row['slopePerWeek']))-1e-12).hex()
    assert proof['independentCutoffHex']==(abs(ownobs)-1e-12).hex()
    expected.update({'kind':kind,'identity':identity,'inputHashes':hashes})
    actual=validate_four_counts(proof,expected)
    assert proof['unchangedReportedValues']=={'primaryP':row['pValue'],'primaryQ':row['qValue']}
    assert math.prod(int(v) for v in proof['rawHalfMasses'])==total
    assert proof['halfSizes']==[p['primary']['exactCounting']['halfSizes'][j]]
    series=p['primary']['byPollster'];assert len(series)==len(proof['support'])
    for i,(support,item) in enumerate(zip(proof['support'],series)):
        seats=next(v['seats'] for v in item[values] if v[key]==identity)
        assert support['pollsterId']==item['pollsterId'] and support['pollIds']==item['pollIds']
        assert support['timeDays']==item['timeDaysFromFirst'] and support['weight']==item['weight'] and support['seats']==seats
        assert support['uniqueScores']==p['primary']['exactCounting']['uniqueStatesBySeries'][j][i]
        assert int(support['rawMass'])==math.factorial(len(seats))
    archived=BOUND/'operational-reconciliation-r1'/self_path.name;assert sha(archived)==sha(self_path)

    adapted=gate_value['adaptedFiles']
    materializer='scripts/materialize-tail-boundary-bands-2026-10-24-r1.py'
    adapted_validator='scripts/validate-strict-trends-2026-10-24-r1.py'
    adapted_promoter='scripts/promote-strict-validation-2026-10-24-r1.py'
    result={**expected,'inputHashes':hashes,'status':'PASS','validationKind':KIND,'asOf':DAY,
        'toleranceUnchanged':1e-12,
        'primaryOperationalPredicateExactIntegerMatch':True,'ownThresholdExactIntegerMatch':True,
        'commonThresholdExactIntegerMatch':actual[1]==pc,
        'commonAdditionThresholdMatchesPrimary':actual[1]==pc,
        'operationalPredicatesDistinct':actual[0]!=actual[1] or actual[2]!=actual[3],
        'allScalarSupportsAndLabeledMassesEqual':True,
        'primaryOperationalCountExact':str(actual[0]),
        'commonThresholdCountExact':str(actual[1]),'ownThresholdCountExact':str(actual[3]),
        'operationalCounts':{k:proof[k] for k in COUNT_KEYS},
        'signedDifferencesFromAdditionOwn':proof['screening']['signedDifferencesFromAdditionOwn'],
        'signedCountDecomposition':proof['signedCountDecomposition'],
        'support':proof['support'],'commonHalfSizes':proof['halfSizes'],'ownHalfSizes':proof['halfSizes'],
        'probabilityDifference':(ic-pc)/total,'outputsOrFrozenHelpersModified':False,
        'statisticalToleranceWidened':False,'pOrQChanged':False,
        'operationalPredicateReconciliationUsed':True,'ordinaryValidatorAndPromoterUnchanged':False,
        'diagnosisStatusPreserved':proof['status'],
        'diagnosisPath':path.relative_to(ROOT).as_posix(),'diagnosisSha256':sha(path),
        'independentReviewPath':review_path.relative_to(ROOT).as_posix(),'independentReviewSha256':sha(review_path),
        'reproducerPath':proof['reproducerPath'],'reproducerSha256':proof['reproducerSha256'],
        'verifierPath':self_path.relative_to(ROOT).as_posix(),'verifierSha256':sha(self_path),
        'verifierArchivedPath':archived.relative_to(ROOT).as_posix(),
        'materializerPath':materializer,'materializerSha256':adapted[materializer],
        'materializerArchivedPath':(BOUND/'operational-reconciliation-r1'/Path(materializer).name).relative_to(ROOT).as_posix(),
        'adapterPath':adapted_validator,'adapterSha256':adapted[adapted_validator],
        'promoterPath':adapted_promoter,'promoterSha256':adapted[adapted_promoter],
        'baseValidatorSha256':reviewed[validator],'basePromoterSha256':reviewed[promoter],
        'sourceGatePath':source_gate_path.relative_to(ROOT).as_posix(),'sourceGateSha256':sha(source_gate_path),
        'explanation':'Exact signed boundary masses reconcile all four original binary predicates. Primary subtraction at its statistic and independent addition at its own statistic match their original integer audits. Common-statistic addition equality is recorded honestly, including false. Original inputs, counter code, fixed1e-12 tolerance and p/q remain unchanged.'}
    return result


def validate_receipt(path, expected=None):
    receipt=read(path);actual=verify(receipt['kind'],receipt['identity'])
    assert receipt==actual,('Operational reconciliation receipt changed',str(path))
    if expected:
        assert all(receipt[k]==v for k,v in expected.items())
    assert receipt['validationKind']==KIND
    return receipt

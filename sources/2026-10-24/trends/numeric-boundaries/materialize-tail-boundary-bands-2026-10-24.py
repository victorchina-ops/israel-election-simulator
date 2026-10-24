"""Materialize ordinary24Oct boundary receipts from independently reviewed proof.

No numerical counter executes. Each current own-addition anchor and the exact
signed boundary-band differences must establish both ordinary integer equalities.
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=['bloc','party'],required=True)
    parser.add_argument('--identity',required=True)
    args=parser.parse_args();assert re.fullmatch('[a-z_]+',args.identity)
    self_path=Path(__file__).resolve();source_gate=read(BOUND/'band-source-review-r1/materializer-independent-source-review.json')
    assert source_gate['status']=='PASS_SOURCE_GATE' and source_gate['asOf']==DAY
    assert source_gate['materializerSha256']==sha(self_path)
    pipeline=read(ART/'pipeline-source-compatibility/independent-root-review.json')
    assert pipeline['status']=='PASS_SOURCE_GATE' and pipeline['asOf']==DAY
    assert pipeline['proposalSha256']==sha(ART/'pipeline-source-compatibility/proposal.json')
    reviewed={r['candidate']:r['candidateSha256'] for r in pipeline['reviewedFiles']}
    validator='scripts/validate-strict-trends-2026-10-24.py';promoter='scripts/promote-strict-validation-2026-10-24.py'
    assert sha(ROOT/validator)==reviewed[validator]==source_gate['validatorSha256']
    assert sha(ROOT/promoter)==reviewed[promoter]
    path=BOUND/(args.kind+'-'+args.identity+'-band-diagnosis.json');proof=read(path)
    review_path=BOUND/'band-independent-execution-review.json';review=read(review_path)
    assert proof['status']==review['status']=='PASS' and proof['asOf']==review['asOf']==DAY
    assert proof['kind']==args.kind and proof['outcome']==args.identity
    assert review['diagnosisHashes'][path.name]==sha(path)
    assert review['reproducerSha256']==proof['reproducerSha256']
    assert review['inputHashes']==proof['inputHashes']
    assert review['checks'] and all(v is True for v in review['checks'].values())
    assert review['pOrQChanged'] is False and review['outputsOrFrozenHelpersModified'] is False
    assert review['heavyCountersExecutedByReviewer'] is False
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
    p=read(ROOT/paths[5 if args.kind=='bloc' else 6]);audit=read(ROOT/paths[7 if args.kind=='bloc' else 8])
    assert p['asOf']==DAY
    key,values=('group','groups') if args.kind=='bloc' else ('partyId','parties')
    j=next(i for i,r in enumerate(p['primary']['overall']) if r[key]==args.identity);row=p['primary']['overall'][j]
    if args.kind=='bloc':ownobs=float(audit['slopes'][j]);ic=int(audit['countsExact'][j]);total=int(audit['totalExact'])
    else:
        other=next(r for r in audit['overall'] if r['partyId']==args.identity)
        ownobs=float(other['slopePerWeek']);ic=int(other['extremeCountExact']);total=int(audit['nPermutationsExact'])
    pc=int(p['primary']['exactCounting']['extremeCountsExact'][j]);assert pc!=ic
    assert int(p['primary']['exactCounting']['nPermutationsExact'])==total
    expected={'primaryObservedHex':float(row['slopePerWeek']).hex(),'independentObservedHex':ownobs.hex(),
        'primaryExtremeCountExact':str(pc),'independentExtremeCountExact':str(ic),'totalExact':str(total)}
    assert all(proof[k]==v for k,v in expected.items())
    assert proof['primaryCutoffHex']==(abs(float(row['slopePerWeek']))-1e-12).hex()
    assert proof['independentCutoffHex']==(abs(ownobs)-1e-12).hex()
    delta=[int(v) for v in proof['screening']['signedDifferencesFromAdditionOwn']]
    assert len(delta)==4 and delta[3]==0
    reconstructed=[ic+v for v in delta]
    actual=[int(proof[k]) for k in ['subtractionAtPrimaryObservedCountExact','directAtPrimaryObservedCountExact',
        'subtractionAtOwnObservedCountExact','directAtOwnObservedCountExact']]
    assert reconstructed==actual and reconstructed[0]==reconstructed[1]==pc and reconstructed[3]==ic
    assert all(0<=v<=total for v in actual)
    assert proof['commonSubtractionPredicateIntegerMatch'] and proof['originalDirectCommonThresholdIntegerMatch']
    assert proof['originalDirectOwnThresholdIntegerMatch']
    assert proof['unchangedReportedValues']=={'primaryP':row['pValue'],'primaryQ':row['qValue']}
    assert math.prod(int(v) for v in proof['rawHalfMasses'])==total
    assert proof['halfSizes']==[p['primary']['exactCounting']['halfSizes'][j]]
    series=p['primary']['byPollster'];assert len(series)==len(proof['support'])
    for i,(support,item) in enumerate(zip(proof['support'],series)):
        seats=next(v['seats'] for v in item[values] if v[key]==args.identity)
        assert support['pollsterId']==item['pollsterId'] and support['pollIds']==item['pollIds']
        assert support['timeDays']==item['timeDaysFromFirst'] and support['weight']==item['weight'] and support['seats']==seats
        assert support['uniqueScores']==p['primary']['exactCounting']['uniqueStatesBySeries'][j][i]
        assert int(support['rawMass'])==math.factorial(len(seats))
    archived=BOUND/self_path.name;assert sha(archived)==sha(self_path)
    result={'kind':args.kind,'identity':args.identity,**expected,'inputHashes':hashes,'status':'PASS','asOf':DAY,
        'toleranceUnchanged':1e-12,'commonThresholdExactIntegerMatch':True,'ownThresholdExactIntegerMatch':True,
        'allScalarSupportsAndLabeledMassesEqual':True,'commonThresholdCountExact':str(reconstructed[1]),
        'ownThresholdCountExact':str(reconstructed[3]),'support':proof['support'],
        'commonHalfSizes':proof['halfSizes'],'ownHalfSizes':proof['halfSizes'],
        'probabilityDifference':(ic-pc)/total,'outputsOrFrozenHelpersModified':False,
        'diagnosisPath':path.relative_to(ROOT).as_posix(),'diagnosisSha256':sha(path),
        'independentReviewPath':review_path.relative_to(ROOT).as_posix(),'independentReviewSha256':sha(review_path),
        'reproducerPath':proof['reproducerPath'],'reproducerSha256':proof['reproducerSha256'],
        'materializerPath':self_path.relative_to(ROOT).as_posix(),'materializerArchivedPath':archived.relative_to(ROOT).as_posix(),
        'materializerSha256':sha(self_path),'baseValidatorSha256':reviewed[validator],
        'ordinaryValidatorAndPromoterUnchanged':True,'noPredicateExceptionUsed':True,
        'diagnosisMethod':'Exact anchored signed boundary-band differences, not a full whole-tail recount',
        'explanation':'Current independently certified own-addition count plus exhaustive exact signed boundary mass proves the original common/own integer equalities. All original source inputs, counter code, tolerance and p/q values remain unchanged.'}
    out=BOUND/(args.kind+'-'+args.identity+'.json');assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','kind':args.kind,'identity':args.identity,'sha256':sha(out),'numericalCountersExecuted':False}))


if __name__=='__main__':main()

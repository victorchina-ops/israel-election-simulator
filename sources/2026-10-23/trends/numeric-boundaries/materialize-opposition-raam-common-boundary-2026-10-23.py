"""Materialize the original common-threshold receipt from the reviewed23Oct proof.

No numerical counters execute here. Both original addition-predicate counts
must exactly match the official integers; ordinary23 validation stays unchanged.
"""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-23'
ART=ROOT/'artifacts/poll-checks'/DAY
BASE=ROOT/'scripts/validate-strict-trends-2026-10-23.py'
BASE_SHA='0ff3a67e0ac83b8750f67e9d736a650e9a874d7e8fb5fc2ce81256683bce5410'
DIAGNOSIS=ART/'numeric-boundaries/opposition-raam-predicate-diagnosis.json'
DIAGNOSIS_SHA='fb25115e8f18e4ec795418ae4f81b3de0b63328f1ea9646e21387b4bb4ce2f8a'
REVIEW=ART/'numeric-boundaries/opposition-raam-predicate-independent-review.json'
REVIEW_SHA='4b6384443d522039eb39a92e0af9bb560a9b2c10e48da5a00462c1ea70edf3d8'
REPRODUCER=ROOT/'scripts/diagnose-opposition-raam-boundary-2026-10-23.py'
REPRODUCER_SHA='a5da460bc358280c53647f58a9be7f953a25951b9ae915fe38066e10769e7341'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert sha(BASE)==BASE_SHA==sha(ART/'numeric-boundaries/failed'/BASE.name)
    assert sha(DIAGNOSIS)==DIAGNOSIS_SHA and sha(REVIEW)==REVIEW_SHA
    assert sha(REPRODUCER)==REPRODUCER_SHA
    proof,review=read(DIAGNOSIS),read(REVIEW)
    assert proof['status']==review['status']=='PASS' and proof['asOf']==review['asOf']==DAY
    assert proof['outcome']==review['outcome']=='opposition_raam'
    assert review['diagnosisSha256']==DIAGNOSIS_SHA and review['reproducerSha256']==REPRODUCER_SHA
    assert review['inputHashes']==proof['inputHashes']
    assert review['checks'] and all(v is True for v in review['checks'].values())
    assert not review['pOrQChanged'] and not review['outputsOrFrozenHelpersModified']
    assert review['heavyCountersExecutedByReviewer'] is False
    assert proof['toleranceUnchanged']==review['toleranceUnchanged']==1e-12
    assert not proof['outputsOrFrozenHelpersModified'] and proof['allScalarSupportsAndLabeledMassesEqual']
    for rel,digest in proof['inputHashes'].items():assert sha(ROOT/rel)==digest
    paths=['data/current-polls.json','data/poll-history.json','data/strict-party-trends.json',
        'data/calibration.json','data/parties.json','artifacts/strict-post-close/analysis.json',
        'artifacts/strict-post-close/party-analysis.json','artifacts/strict-post-close/independent-strict-numeric-audit.json',
        'artifacts/strict-post-close/party-independent.json','artifacts/poll-checks/2026-10-23/source-plan.json',
        'artifacts/poll-checks/2026-10-23/ingestion-validation.json',
        *['artifacts/strict-post-close/'+name for name in ['lazar-fieldwork.json','n12-kan-c13-fieldwork.json',
        'c14-i24-fieldwork.json','c16-tatika-fieldwork.json','new-unverified-fieldwork-2026-09-30.json']]]
    hashes={rel:sha(ROOT/rel) for rel in paths}
    for rel,digest in hashes.items():
        if rel in proof['inputHashes']:assert proof['inputHashes'][rel]==digest
    primary,independent=read(ROOT/paths[5]),read(ROOT/paths[7])
    assert primary['asOf']==DAY
    j=independent['groups'].index('opposition_raam');row=primary['primary']['overall'][j]
    assert row['group']=='opposition_raam'
    pc=int(primary['primary']['exactCounting']['extremeCountsExact'][j]);ic=int(independent['countsExact'][j])
    total=int(independent['totalExact'])
    assert int(primary['primary']['exactCounting']['nPermutationsExact'])==total
    expected={'primaryObservedHex':float(row['slopePerWeek']).hex(),
        'independentObservedHex':float(independent['slopes'][j]).hex(),
        'primaryExtremeCountExact':str(pc),'independentExtremeCountExact':str(ic),'totalExact':str(total)}
    assert all(proof[k]==review[k]==v for k,v in expected.items())
    common=int(proof['directAtPrimaryObservedCountExact']);own=int(proof['directAtOwnObservedCountExact'])
    assert common==pc and own==ic, 'Original common/own addition conditions must hold exactly'
    assert proof['halfSizes']==proof['subtractionHalfSizes']
    import math
    assert math.prod(int(v) for v in proof['rawHalfMasses'])==total
    series=primary['primary']['byPollster'];assert len(proof['support'])==len(series)
    for support,item in zip(proof['support'],series):
        seats=next(v['seats'] for v in item['groups'] if v['group']=='opposition_raam')
        assert support['pollsterId']==item['pollsterId'] and support['pollIds']==item['pollIds']
        assert support['timeDays']==item['timeDaysFromFirst'] and support['weight']==item['weight'] and support['seats']==seats
        assert int(support['rawMass'])==math.factorial(len(seats))
    archived=ART/'numeric-boundaries'/Path(__file__).name
    assert sha(archived)==sha(Path(__file__))
    result={'kind':'bloc','identity':'opposition_raam',**expected,'inputHashes':hashes,
        'status':'PASS','asOf':DAY,'toleranceUnchanged':1e-12,
        'commonThresholdExactIntegerMatch':True,'ownThresholdExactIntegerMatch':True,
        'allScalarSupportsAndLabeledMassesEqual':True,'commonThresholdCountExact':str(common),
        'ownThresholdCountExact':str(own),'support':proof['support'],
        'commonHalfSizes':proof['halfSizes'],'ownHalfSizes':proof['halfSizes'],
        'probabilityDifference':(ic-pc)/total,'outputsOrFrozenHelpersModified':False,
        'diagnosisPath':DIAGNOSIS.relative_to(ROOT).as_posix(),'diagnosisSha256':DIAGNOSIS_SHA,
        'independentReviewPath':REVIEW.relative_to(ROOT).as_posix(),'independentReviewSha256':REVIEW_SHA,
        'reproducerPath':REPRODUCER.relative_to(ROOT).as_posix(),'reproducerSha256':REPRODUCER_SHA,
        'materializerPath':Path(__file__).resolve().relative_to(ROOT).as_posix(),
        'materializerArchivedPath':archived.relative_to(ROOT).as_posix(),
        'materializerSha256':sha(Path(__file__)),'baseValidatorSha256':BASE_SHA,
        'ordinaryValidatorAndPromoterUnchanged':True,'noPredicateExceptionUsed':True,
        'explanation':'The unchanged independent addition counter reproduces the primary exact count at the common primary statistic and the independent exact count at its own statistic. The independently reviewed four-count proof also isolates operational predicate and observed-statistic effects. Both original integers and p/q values remain unchanged.'}
    target=ART/'numeric-boundaries/bloc-opposition_raam.json'
    body=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if target.exists():assert target.read_bytes()==body
    else:target.write_bytes(body)
    print(json.dumps({'status':'PASS','path':target.relative_to(ROOT).as_posix(),'sha256':sha(target),
        'originalCommonThresholdExactMatch':True,'originalOwnThresholdExactMatch':True,'countersExecuted':False}))


if __name__=='__main__':main()

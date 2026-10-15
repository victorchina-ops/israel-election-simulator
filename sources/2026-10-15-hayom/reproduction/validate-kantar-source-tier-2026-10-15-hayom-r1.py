"""Independently review the documented metadata-only Kantar source-tier normalization.

No repair implementation is imported. Compare complete before/after JSON, allow
only the explicit new-observation tier fields, and bind original frozen receipts.
"""
from pathlib import Path
import copy, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/poll-checks/2026-10-15-hayom'
DEST=ART/'metadata-normalization-r1'
PUBLIC=ROOT/'github-pages/sources/2026-10-15-hayom'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OLD='original-publisher-with-user-supplied-original-report'
NEW='original-publisher'
POLL='kantar_2026-10-15'


def main():
    preflight,receipt=[read(DEST/p) for p in ['preflight.json','receipt.json']]
    ingestion=read(ART/'ingestion-receipt.json')
    ingestion_review=read(ART/'ingestion-validation.json')
    candidate=read(ART/'source/reviewed-kantar-poll.json')
    assert receipt['status']=='PASS' and receipt['phase']=='applied-awaiting-independent-review'
    assert receipt['fromSourceTier']==OLD and receipt['toSourceTier']==NEW and receipt['observationId']==POLL
    assert receipt['preflightSha256']==sha(DEST/'preflight.json')
    assert receipt['ingestionReceiptSha256']==sha(ART/'ingestion-receipt.json')==ingestion_review['ingestionReceiptSha256']
    assert receipt['ingestionValidationSha256']==sha(ART/'ingestion-validation.json')
    assert receipt['sourcePlanSha256']==sha(ART/'source-plan.json')==ingestion['sourcePlanSha256']
    assert receipt['candidateSha256']==sha(ART/'source/reviewed-kantar-poll.json')
    assert candidate['sourceTier']==OLD and candidate['id']==POLL
    assert receipt['files']==preflight['files'] and receipt['publicDerivativeChanges']==preflight['publicDerivativeChanges']
    assert len(receipt['files'])==6
    for relative,digest in receipt['preservedHashes'].items():
        assert sha(ROOT/relative)==digest,('Preserved input changed',relative)
    changes={}
    for row in receipt['files']:
        relative=row['path'];path=ROOT/relative;before=DEST/row['beforeCopy']
        assert sha(before)==row['beforeSha256'] and sha(path)==row['afterSha256']
        old,new=read(before),read(path)
        reverted=copy.deepcopy(new)
        locations=[]
        if relative=='data/current-polls.json':
            locations += [p for p in reverted['polls'] if p['id']==POLL]
            locations += [p for p in reverted['documentReview']['reports'] if p['id']=='kantar-2026-10-15']
            assert len(locations)==2
        elif relative=='data/poll-history.json':
            locations=[p for p in reverted['polls'] if p.get('sourcePollId')==POLL]
            assert len(locations)==1
        elif relative=='data/survey-documents-2026-09-14.json':
            locations=[p for p in reverted['reports'] if p['id']=='kantar-2026-10-15']
            assert len(locations)==1
        elif relative=='data/sources.json':
            locations=[p for p in reverted['sources'] if p.get('id')=='kantar']
            assert len(locations)==1 and locations[0]['type']==NEW
            locations[0]['type']=OLD
        else:
            assert relative in [str((PUBLIC/'hayom/reviewed-poll.json').relative_to(ROOT)).replace('\\','/'),
                                str((PUBLIC/'hayom/ingested-poll.json').relative_to(ROOT)).replace('\\','/')]
            assert reverted['id']==POLL
            locations=[reverted]
        for location in locations:
            if relative!='data/sources.json':
                assert location['sourceTier']==NEW
                location['sourceTier']=OLD
        assert reverted==old,('Change exceeds explicit tier normalization',relative)
        if relative in ingestion['changedCanonicalFiles']:
            assert row['beforeSha256']==ingestion['changedCanonicalFiles'][relative]
        else:
            public_relative=path.relative_to(PUBLIC).as_posix()
            assert row['beforeSha256']==ingestion['publicEvidenceFiles'][public_relative]
            assert receipt['publicDerivativeChanges'][public_relative]=={'beforeSha256':row['beforeSha256'],'afterSha256':row['afterSha256']}
        changes[relative]={'beforeSha256':row['beforeSha256'],'afterSha256':row['afterSha256']}
    current=read(ROOT/'data/current-polls.json')
    history=read(ROOT/'data/poll-history.json')
    documents=read(ROOT/'data/survey-documents-2026-09-14.json')
    assert current['documentReview']==documents and len(current['polls'])==8 and len(history['polls'])==124
    active=next(p for p in current['polls'] if p['id']==POLL)
    archived=next(p for p in history['polls'] if p.get('sourcePollId')==POLL)
    # Original ingestion legitimately added archive URLs to the sourceDocument.
    # The complete before/after comparison above proves those also stayed intact.
    for key,value in candidate['sourceDocument'].items():
        assert active['sourceDocument'][key]==value,('Original report provenance changed',key)
    assert active['sourceDocument']['kind']=='user-provided-original-pollster-numerical-report-image-crosschecked-with-live-original-publisher'
    assert active['seats']==archived['seats']==candidate['seats']
    assert active['reportedPercentages']==archived['reportedPercentages']==candidate['reportedPercentages']
    assert read(PUBLIC/'hayom/reviewed-poll.json')==read(PUBLIC/'hayom/ingested-poll.json')==active
    for relative,digest in ingestion['publicEvidenceFiles'].items():
        if relative in receipt['publicDerivativeChanges']:
            assert digest==receipt['publicDerivativeChanges'][relative]['beforeSha256']
        else:
            assert sha(PUBLIC/relative)==digest,('Original public evidence changed',relative)
    result={'status':'PASS','asOf':'2026-10-15','runId':'hayom','revision':'metadata-normalization-r1',
            'observationId':POLL,'fromSourceTier':OLD,'toSourceTier':NEW,
            'files':changes,'publicDerivativeChanges':receipt['publicDerivativeChanges'],
            'receiptSha256':sha(DEST/'receipt.json'),'preflightSha256':sha(DEST/'preflight.json'),
            'ingestionReceiptSha256':sha(ART/'ingestion-receipt.json'),
            'ingestionValidationSha256':sha(ART/'ingestion-validation.json'),
            'sourcePlanSha256':sha(ART/'source-plan.json'),'candidateSha256':sha(ART/'source/reviewed-kantar-poll.json'),
            'candidateAndOriginalReceiptsUnchanged':True,'onlyNewObservationTierFieldsChanged':True,
            'detailedSourceDocumentProvenanceUnchanged':True,'allPollValuesFieldworkWeightsAndPriorRowsUnchanged':True,
            'activePolls':8,'historyPolls':124,'validatorSha256':sha(Path(__file__))}
    body=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    target=DEST/'validation.json'
    if target.exists():assert target.read_bytes()==body,'Changed immutable metadata validation'
    else:target.write_bytes(body)
    print(json.dumps({'status':'PASS','files':len(changes),'validationSha256':sha(target),
                      'publicDerivativeChanges':result['publicDerivativeChanges']},ensure_ascii=False))


if __name__=='__main__':main()

"""Promote the exact validated21Oct receipt to its mutable canonical pointer."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/poll-checks/2026-10-21'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source=ART/'strict-validation.json';target=ROOT/'artifacts/strict-post-close/party-validation.json'
    value=read(source);manifest=read(ART/'before/manifest.json')
    assert value['passed'] and value['status']=='PASS' and value['asOf']=='2026-10-21'
    assert value['validatorSha256']==sha(ROOT/'scripts/validate-strict-trends-2026-10-21-predicate-r1.py')
    for family in ['inputHashes','candidateHashes','sourceEvidenceHashes','preservedCodeHashes','numericLineageHashes','boundaryReviewHashes','exactArithmeticRepairInputHashes']:
        for rel,digest in value[family].items():assert sha(ROOT/rel)==digest
    for rel,digest in value['boundaryReviewHashes'].items():
        boundary=read(ROOT/rel)
        assert sha(ROOT/boundary['diagnosisPath'])==boundary['diagnosisSha256']
        assert sha(ROOT/boundary['independentReviewPath'])==boundary['independentReviewSha256']
        assert read(ROOT/boundary['independentReviewPath'])['status']=='PASS'
        assert boundary['primarySubtractionPredicateIntegerMatch'] and boundary['independentAdditionOwnThresholdIntegerMatch']
        assert boundary['commonAdditionThresholdMatchesPrimary'] is False
    old_rel=target.relative_to(ROOT).as_posix();old_sha=manifest['files'][old_rel]
    assert sha(ART/'before'/old_rel)==old_sha
    if target.read_bytes()!=source.read_bytes():
        assert sha(target)==old_sha,'Only the frozen prior operational pointer may be replaced'
        shutil.copy2(source,target)
    assert source.read_bytes()==target.read_bytes()
    report={'status':'PASS','asOf':'2026-10-21','source':source.relative_to(ROOT).as_posix(),
        'canonical':old_rel,'sourceAndCanonicalSha256':sha(source),'previousCanonicalSha256':old_sha,
        'previousCanonicalPreservedInCheckpoint':True,'sourceBytesCopiedExactly':True,
        'probabilitiesOrNumericalOutputsEdited':False,'promoterSha256':sha(Path(__file__))}
    out=ART/'strict-validation-promotion.json';body=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if out.exists():assert out.read_bytes()==body
    else:out.write_bytes(body)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

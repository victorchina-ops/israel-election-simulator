"""Copy the exact dated24Oct validated receipt to its operational pointer.

The prior pointer is preserved in before/. Only fresh fully reviewed24Oct
four-predicate reconciliation is accepted; no prior-day proof is inherited.
"""
from pathlib import Path
import hashlib
import json
import shutil
import importlib.util
import sys
sys.dont_write_bytecode=True

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-24'
ART = ROOT / 'artifacts/poll-checks' / DAY
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source = ART / 'strict-validation.json'
    target = ROOT / 'artifacts/strict-post-close/party-validation.json'
    value = read(source)
    manifest = read(ART / 'before/manifest.json')
    assert value['passed'] and value['status'] == 'PASS' and value['asOf'] == DAY
    assert value['validatorSha256'] == sha(ROOT / 'scripts/validate-strict-trends-2026-10-24-r1.py')
    for family in ['inputHashes', 'candidateHashes', 'sourceEvidenceHashes',
                   'preservedCodeHashes', 'numericLineageHashes',
                   'boundaryReviewHashes', 'exactArithmeticRepairInputHashes']:
        for relative, digest in value[family].items():
            assert sha(ROOT / relative) == digest
    gate_path=ART/'numeric-boundaries/operational-reconciliation-r1/independent-source-review.json'
    gate=read(gate_path)
    assert gate['status']=='PASS_SOURCE_GATE' and gate['asOf']==DAY
    assert gate['adaptedFiles'][Path(__file__).resolve().relative_to(ROOT).as_posix()]==sha(Path(__file__))
    assert value['operationalPredicateSourceGateSha256']==sha(gate_path)
    assert value['validationKind']=='exact-operational-predicate-reconciliation'
    assert value['pOrQChanged'] is False and value['statisticalToleranceWidened'] is False and value['ordinaryChecksPreserved'] is True
    relative='scripts/verify-operational-tail-reconciliation-2026-10-24-r1.py'
    assert gate['adaptedFiles'][relative]==sha(ROOT/relative)
    spec=importlib.util.spec_from_file_location('_fresh24_promoter_verifier',ROOT/relative)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    for relative in value['boundaryReviewHashes']:
        verifier.validate_receipt(ROOT/relative)
    relative = target.relative_to(ROOT).as_posix()
    previous = manifest['files'][relative]
    assert sha(ART / 'before' / relative) == previous
    if target.read_bytes() != source.read_bytes():
        assert sha(target) == previous, 'Only the frozen prior pointer may be replaced'
        shutil.copy2(source, target)
    assert target.read_bytes() == source.read_bytes()
    result = {'status': 'PASS', 'asOf': DAY,
              'source': source.relative_to(ROOT).as_posix(), 'canonical': relative,
              'sourceAndCanonicalSha256': sha(source), 'previousCanonicalSha256': previous,
              'previousCanonicalPreservedInCheckpoint': True, 'sourceBytesCopiedExactly': True,
              'probabilitiesOrNumericalOutputsEdited': False,
              'promoterSha256': sha(Path(__file__)),
              'validationKind':'exact-operational-predicate-reconciliation',
              'sourceGateSha256':sha(gate_path),'statisticalToleranceWidened':False}
    output = ART / 'strict-validation-promotion.json'
    body = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if output.exists():
        assert output.read_bytes() == body
    else:
        output.write_bytes(body)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

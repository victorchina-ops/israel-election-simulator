"""Copy the exact dated24Oct validated receipt to its operational pointer.

The prior pointer is preserved in before/. A new operational-predicate diagnosis
would need its own reviewed adapter; no21Oct predicate exception is accepted here.
"""
from pathlib import Path
import hashlib
import json
import shutil

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
    assert value['validatorSha256'] == sha(ROOT / 'scripts/validate-strict-trends-2026-10-24.py')
    for family in ['inputHashes', 'candidateHashes', 'sourceEvidenceHashes',
                   'preservedCodeHashes', 'numericLineageHashes',
                   'boundaryReviewHashes', 'exactArithmeticRepairInputHashes']:
        for relative, digest in value[family].items():
            assert sha(ROOT / relative) == digest
    for relative in value['boundaryReviewHashes']:
        boundary = read(ROOT / relative)
        assert boundary['status'] == 'PASS' and boundary['asOf'] == DAY
        assert boundary['toleranceUnchanged'] == 1e-12
        assert boundary['commonThresholdExactIntegerMatch']
        assert boundary['ownThresholdExactIntegerMatch']
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
              'promoterSha256': sha(Path(__file__))}
    output = ART / 'strict-validation-promotion.json'
    body = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if output.exists():
        assert output.read_bytes() == body
    else:
        output.write_bytes(body)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

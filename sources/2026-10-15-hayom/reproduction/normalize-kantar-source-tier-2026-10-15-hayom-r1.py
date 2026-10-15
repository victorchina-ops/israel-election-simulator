"""Normalize a verified primary-source tier for the existing UI's standard enum.

Only the new Kantar observation's sourceTier (and the active source's type) is
changed. Detailed provenance remains in the original frozen candidate and the
unchanged sourceDocument.kind. No author, weighting, poll value or old row changes.
"""
from pathlib import Path
import argparse, copy, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/poll-checks/2026-10-15-hayom'
DEST = ART / 'metadata-normalization-r1'
PUBLIC = ROOT / 'github-pages/sources/2026-10-15-hayom'
DAY = '2026-10-15'
POLL = 'kantar_2026-10-15'
OLD = 'original-publisher-with-user-supplied-original-report'
NEW = 'original-publisher'
CANONICAL = ['data/current-polls.json', 'data/poll-history.json',
             'data/sources.json', 'data/survey-documents-2026-09-14.json']
DERIVATIVES = ['hayom/reviewed-poll.json', 'hayom/ingested-poll.json']
FILES = CANONICAL + [(PUBLIC / p).relative_to(ROOT).as_posix() for p in DERIVATIVES]
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
encoded = lambda v: (json.dumps(v, ensure_ascii=False, indent=2)+'\n').encode('utf-8')


def immutable(path, body):
    if not isinstance(body, bytes):
        body = encoded(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == body, ('Immutable normalization evidence changed', str(path))
    else:
        path.write_bytes(body)


def transformed(relative, document):
    revised = copy.deepcopy(document)
    if relative == 'data/current-polls.json':
        matches = [p for p in revised['polls'] if p['id'] == POLL]
    elif relative == 'data/poll-history.json':
        matches = [p for p in revised['polls'] if p['sourcePollId'] == POLL]
    elif relative == 'data/sources.json':
        matches = [p for p in revised['sources'] if p.get('id') == 'kantar']
    elif relative == 'data/survey-documents-2026-09-14.json':
        matches = [p for p in revised['reports'] if p['id'] == 'kantar-2026-10-15']
    else:
        assert relative in FILES[-2:] and revised['id'] == POLL
        matches = [revised]
    assert len(matches) == 1
    key = 'type' if relative == 'data/sources.json' else 'sourceTier'
    assert matches[0][key] == OLD
    matches[0][key] = NEW
    # current.documentReview is an embedded exact copy of the report register.
    if relative == 'data/current-polls.json':
        reports = [p for p in revised['documentReview']['reports'] if p['id'] == 'kantar-2026-10-15']
        assert len(reports) == 1 and reports[0]['sourceTier'] == OLD
        reports[0]['sourceTier'] = NEW
    return revised


def preservation():
    manifest = read(ART / 'before/manifest.json')
    hashes = {}
    for family in ['authorContentHashes', 'protectedRuntimeHashes', 'frozenEvidenceHashes',
                   'frozenConditionalAndArtisticHashes', 'reviewedExactHelpers']:
        for relative, digest in manifest[family].items():
            assert sha(ROOT / relative) == digest, ('Preserved input changed', relative)
            hashes[relative] = digest
    for relative in ['data/calibration.json', 'data/parties.json',
                     'artifacts/strict-post-close/n12-kan-c13-fieldwork.json']:
        hashes[relative] = sha(ROOT / relative)
    for relative in ['source-plan.json', 'ingestion-preflight.json', 'ingestion-receipt.json',
                     'ingestion-validation.json', 'source/reviewed-kantar-poll.json',
                     'source/kantar-verification-summary-r1.json']:
        path = ART / relative
        hashes[path.relative_to(ROOT).as_posix()] = sha(path)
    return hashes


def prepare():
    ingested = read(ART / 'ingestion-receipt.json')
    reviewed = read(ART / 'ingestion-validation.json')
    assert reviewed['status'] == 'PASS' and reviewed['historyPollCount'] == 124
    assert reviewed['ingestionReceiptSha256'] == sha(ART / 'ingestion-receipt.json')
    assert ingested['sourcePlanSha256'] == sha(ART / 'source-plan.json')
    rows, values = [], {}
    for relative in FILES:
        source = ROOT / relative
        if relative in CANONICAL:
            assert sha(source) == ingested['changedCanonicalFiles'][relative]
        else:
            public_relative = source.relative_to(PUBLIC).as_posix()
            assert sha(source) == ingested['publicEvidenceFiles'][public_relative]
        original = source.read_bytes()
        revised = transformed(relative, read(source))
        body = encoded(revised)
        assert body != original
        rows.append({'path':relative, 'beforeSha256':sha(source),
                     'afterSha256':hashlib.sha256(body).hexdigest(),
                     'beforeCopy':('before/'+relative)})
        values[relative] = (original, body)
    preservation_hashes = preservation()
    public_changes = {Path(row['path']).relative_to(PUBLIC.relative_to(ROOT)).as_posix():
                      {'beforeSha256':row['beforeSha256'], 'afterSha256':row['afterSha256']}
                      for row in rows if row['path'].startswith('github-pages/')}
    preflight = {'status':'PASS', 'asOf':DAY, 'runId':'hayom', 'revision':'metadata-normalization-r1',
                 'observationId':POLL, 'fromSourceTier':OLD, 'toSourceTier':NEW,
                 'reason':'The frozen UI recognizes the standard original-publisher enum; detailed original report provenance remains in unchanged sourceDocument.kind and frozen original candidate.',
                 'files':rows, 'publicDerivativeChanges':public_changes,
                 'ingestionReceiptSha256':sha(ART / 'ingestion-receipt.json'),
                 'ingestionValidationSha256':sha(ART / 'ingestion-validation.json'),
                 'sourcePlanSha256':sha(ART / 'source-plan.json'),
                 'candidateSha256':sha(ART / 'source/reviewed-kantar-poll.json'),
                 'preservedHashes':preservation_hashes, 'scriptSha256':sha(Path(__file__)),
                 'noPollValuesWeightsFieldworkAuthorOrHistoricalObservationChanged':True}
    return preflight, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    preflight, values = prepare()
    if args.check:
        for relative, (original, _) in values.items():
            immutable(DEST / 'before' / relative, original)
        immutable(DEST / 'preflight.json', preflight)
        print(json.dumps({'status':'PASS','phase':'preflight','files':len(values),
                          'publicDerivativeChanges':preflight['publicDerivativeChanges'],
                          'preflightSha256':sha(DEST / 'preflight.json')}, ensure_ascii=False))
        return
    assert read(DEST / 'preflight.json') == preflight
    for row in preflight['files']:
        assert sha(DEST / row['beforeCopy']) == row['beforeSha256']
        assert sha(ROOT / row['path']) == row['beforeSha256']
    for relative, (_, body) in values.items():
        (ROOT / relative).write_bytes(body)
    for row in preflight['files']:
        assert sha(ROOT / row['path']) == row['afterSha256']
    assert preservation() == preflight['preservedHashes']
    receipt = {**preflight, 'phase':'applied-awaiting-independent-review',
               'preflightSha256':sha(DEST / 'preflight.json'),
               'changedCanonicalFiles':{r['path']:r['afterSha256'] for r in preflight['files'] if r['path'] in CANONICAL}}
    immutable(DEST / 'receipt.json', receipt)
    print(json.dumps({'status':'PASS','phase':receipt['phase'],'receiptSha256':sha(DEST / 'receipt.json')},ensure_ascii=False))


if __name__ == '__main__':
    main()

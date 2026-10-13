"""Verify new Maagar fieldwork and supplement existing polls from official PDFs.

Original broadcasts and filed reports establish collection dates. Filing dates
are retained separately and never counted as new survey publications.
"""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

history = read(ROOT / 'data/poll-history.json')
assert history['asOf'] == '2026-10-06', 'Wait until canonical ingestion is complete.'
history_by_id = {row['id']: row for row in history['polls']}

def verified_filing(row, directory, reviewed_name='reviewed-original.json'):
    report = read(directory / reviewed_name)
    document = report['sourceDocument']
    source = directory / document['fileName']
    assert sha(source) == document['sha256']
    assert report['fieldworkVerified'] and report['fieldworkStart'] >= '2026-09-09'
    historical = history_by_id[row['pollId']]
    assert report['publicationDate'] == row['publicationDate'] == historical['date']
    assert all(historical['seats'].get(party_id, 0) == seats
               for party_id, seats in report['reportedSeats'].items())
    previous = copy.deepcopy(row)
    row.update({
        'previousDecision': previous,
        'revisionReviewedAt': '2026-10-07',
        'fieldworkStart': report['fieldworkStart'], 'fieldworkEnd': report['fieldworkEnd'],
        'fieldworkStartTime': report['fieldworkStartTime'],
        'fieldworkEndTime': report['fieldworkEndTime'], 'fieldworkTimeZone': 'Asia/Jerusalem',
        'eligibleStrict': True, 'includeInStrictPostClose': True, 'crossesClosureDate': False,
        'status': 'verified-after-closure-original-filing', 'sampleSize': report['sampleSize'],
        'collectionMode': report['samplingMethod'], 'marginOfErrorPct': report['reportedMarginOfErrorPct'],
        'sourceUrl': report['sourceUrl'],
        'evidencePath': source.relative_to(ROOT).as_posix(), 'evidenceSha256': sha(source),
        'evidence': [{
            'file': source.relative_to(ROOT).as_posix(), 'url': report['sourceUrl'],
            'kind': 'original-pollster-election-committee-submission',
            'quote': f"Original fieldwork {report['fieldworkStart']} {report['fieldworkStartTime']}–{report['fieldworkEnd']} {report['fieldworkEndTime']}; actual respondents{report['sampleSize']}.",
            'locator': f"Original report methodology page{report['fieldworkSourcePage']}, independently visually inspected.",
            'sha256': sha(source),
        }, {
            'file': (directory / reviewed_name).relative_to(ROOT).as_posix(),
            'url': report['sourceUrl'], 'kind': 'review-of-primary-official-submission',
            'quote': None, 'locator': 'fieldworkVerified and discrepancyResolution',
            'sha256': sha(directory / reviewed_name),
        }],
        'reason': 'Official original filing newly verifies the entire fieldwork interval after list closure. This supplements the existing poll, not a second survey; previous exclusion and conflicting metadata are retained in previousDecision.',
    })
    return row

kan_path = HERE / 'n12-kan-c13-fieldwork.json'
kan_audit = read(kan_path)
kan = next(row for row in kan_audit['rows'] if row['pollId'] == 'history_kantar_2026-10-04_current')
assert kan['fieldworkStart'] is None and kan['fieldworkEnd'] is None
verified_filing(kan, ROOT / 'artifacts/sources/2026-10-04-kan-original-review')
assert kan['fieldworkStart'] == kan['fieldworkEnd'] == '2026-10-04' and kan['sampleSize'] == 553
kan_audit['auditedAt'] = '2026-10-07'
kan_audit['counts'] = {'records': len(kan_audit['rows']),
    'verifiedEligible': sum(row['eligibleStrict'] for row in kan_audit['rows']),
    'unknown': sum(not row['eligibleStrict'] for row in kan_audit['rows'])}
kan_audit['limitations'].append('On October7 the official filed KanOctober4 report was obtained. It explicitly verifies October4 fieldwork11:30–16:15 and n553; this supersedes the earlier unknown-fieldwork exclusion and broadcast n554. The earlier exclusion remains archived; no duplicate poll is created.')
write(kan_path, kan_audit)

old_maagar_path = HERE / 'new-unverified-fieldwork-2026-09-30.json'
old_maagar_audit = read(old_maagar_path)
old_maagar = next(row for row in old_maagar_audit['polls'] if row['pollId'] == 'history_maagar_mochot_2026-09-29_current')
assert old_maagar['fieldworkStart'] is None and old_maagar['fieldworkEnd'] is None
verified_filing(old_maagar, ROOT / 'artifacts/sources/2026-09-29-maagar-original-review')
assert old_maagar['fieldworkStart'] == old_maagar['fieldworkEnd'] == '2026-09-29' and old_maagar['sampleSize'] == 550
old_maagar_audit['supplementReviewedAt'] = '2026-10-07'
old_maagar_audit['supplementNote'] = 'Original MaagarSeptember29 submission verifies collection29September07:00–12:00; the existing poll becomes eligible and provides a verified predecessor to October6.'
write(old_maagar_path, old_maagar_audit)

new_maagar_path = HERE / 'c16-tatika-fieldwork.json'
new_maagar_audit = read(new_maagar_path)
new_id = 'history_maagar_mochot_2026-10-06_current'
assert new_id not in {row['pollId'] for row in new_maagar_audit['polls']}
new = history_by_id[new_id]
assert new['fieldworkStart'] == '2026-10-05' and new['fieldworkEnd'] == '2026-10-06'
assert new['sampleSize'] == 550 and sum(new['seats'].values()) == 120
frame = ROOT / 'artifacts/poll-checks/2026-10-07/c16/primary-frame-006s.png'
assert sha(frame) == '0b82c0fa1704305f0e56ded37ffd36da8669854ca175b09b2faec0c7835ea3ec'
frame_receipts = ROOT / 'artifacts/poll-checks/2026-10-07/c16/primary-frame-receipts.json'
source_url = 'https://www.ch16.co.il/vod/6ac52db1be11035fe627ec5a'
new_maagar_audit['polls'].append({
    'pollId': new_id, 'sourcePollId': 'maagar_mochot_2026-10-06',
    'pollsterId': 'maagar_mochot', 'publisher': 'ערוץ 16', 'publicationDate': '2026-10-06',
    'fieldworkStart': '2026-10-05', 'fieldworkEnd': '2026-10-06',
    'eligibleStrict': True, 'includeInStrictPostClose': True, 'crossesClosureDate': False,
    'status': 'verified-after-closure-original-broadcast', 'sampleSize': 550,
    'collectionMode': None, 'marginOfErrorPct': 4.2, 'sourceUrl': source_url,
    'evidencePath': frame.relative_to(ROOT).as_posix(), 'evidenceSha256': sha(frame),
    'evidence': [{
        'file': frame.relative_to(ROOT).as_posix(), 'url': source_url,
        'kind': 'original-publisher-broadcast-frame',
        'quote': 'נערך אתמול והיום וכלל 550 משיבים, טעות הדגימה המרבית 4.2%',
        'locator': 'Original October6 broadcast at6s; relative days refer explicitly to collection, establishing October5–6. The publication date is independently printed on the original broadcast graphic.',
        'sha256': sha(frame),
    }, {
        'file': frame_receipts.relative_to(ROOT).as_posix(), 'url': source_url,
        'kind': 'original-broadcast-hashed-segment-and-frame-receipts',
        'quote': None, 'locator': 'seg_2169650_1.ts, primary-frame-006s.png and70s corroborating frame',
        'sha256': sha(frame_receipts),
    }],
    'reason': 'Original broadcast explicitly states collection yesterday and today, referenced to the independently dated October6 publication. Thus the interval is October5–6, wholly after closure; no publication-only imputation. Official September29 predecessor establishes a two-observation within-Maagar series.',
    'accessNote': 'Primary broadcast resolves secondary News1 metadata conflicts: n550, not552; collectionOctober5–6, not onlyTuesday. Sampling mode and population remain missing unless separately verified.',
})
new_maagar_audit['auditDate'] = '2026-10-07'
new_maagar_audit['summary'] = {
    'assignedPolls': len(new_maagar_audit['polls']),
    'verifiedEligible': sum(row['eligibleStrict'] for row in new_maagar_audit['polls']),
    'excludedUnverified': sum(not row['eligibleStrict'] for row in new_maagar_audit['polls']),
}
write(new_maagar_path, new_maagar_audit)
print('Added MaagarOctober6 and verified existing KanOctober4 / MaagarSeptember29 with primary evidence; prior decisions preserved.')

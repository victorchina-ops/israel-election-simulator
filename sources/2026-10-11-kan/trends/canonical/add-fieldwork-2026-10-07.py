"""Document C13 October 7 exclusion and the primary September 30 fieldwork revision."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'artifacts/sources/2026-10-07-hamadad-update'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


history = read(ROOT / 'data/poll-history.json')
assert history['asOf'] == '2026-10-07', 'Wait for stable canonical ingestion.'
by_id = {row['id']: row for row in history['polls']}
report = read(SOURCE / 'reviewed-rosner-sep30-original.json')
pdf = SOURCE / report['sourceFileName']
assert sha(pdf) == report['sourceSha256'] == 'f3d9ccad37ee833ba64e01b0f8d64aac57ec0af58ad641df1e9fe9a286718081'
assert report['fieldworkStart'] == '2026-09-29' and report['fieldworkEnd'] == '2026-09-30'
assert report['fieldworkStartTime'] == '10:00' and report['fieldworkEndTime'] == '09:00'
assert report['sampleSize'] == 1013 and report['reportedMarginOfErrorPct'] == 3.1
old_id = 'history_hamadad_consortium_2026-09-30_current'
old_historical = by_id[old_id]
assert old_historical['fieldworkStart'] == report['fieldworkStart']
assert old_historical['fieldworkEnd'] == report['fieldworkEnd']
assert sum(old_historical['seats'].values()) == 120
for row in report['tables'][0]['rows']:
    if row.get('partyId') is not None and row.get('seats') is not None:
        assert old_historical['seats'].get(row['partyId'], 0) == row['seats']
path = HERE / 'new-unverified-fieldwork-2026-09-30.json'
audit = read(path)
old = next(row for row in audit['polls'] if row['pollId'] == old_id)
assert old['fieldworkStart'] is None and old['fieldworkEnd'] is None and not old['eligibleStrict']
previous = copy.deepcopy(old)
old.update({
    'previousDecision': previous, 'revisionReviewedAt': '2026-10-07',
    'fieldworkStart': '2026-09-29', 'fieldworkEnd': '2026-09-30',
    'fieldworkStartTime': '10:00', 'fieldworkEndTime': '09:00', 'fieldworkTimeZone': 'Asia/Jerusalem',
    'eligibleStrict': True, 'includeInStrictPostClose': True, 'crossesClosureDate': False,
    'status': 'verified-after-closure-original-filing', 'sampleSize': 1013,
    'collectionMode': report['collectionMethod'], 'samplingMethod': report['samplingMethod'],
    'marginOfErrorPct': 3.1, 'sourceUrl': report['sourceUrl'],
    'evidencePath': pdf.relative_to(ROOT).as_posix(), 'evidenceSha256': sha(pdf),
    'evidence': [{
        'file': pdf.relative_to(ROOT).as_posix(), 'url': report['sourceUrl'],
        'kind': 'original-pollster-election-committee-submission',
        'quote': 'מועד איסוף נתונים: 29.9.2026 בשעה 10:00 עד 30.9.2026 בשעה 9:00; 1,013 משיבים בפועל; טעות הדגימה 3.1%',
        'locator': 'Original report page1, independently visually inspected. Collection interval is explicit, not inferred from publication.',
        'sha256': sha(pdf),
    }, {
        'file': (SOURCE / 'reviewed-rosner-sep30-original.json').relative_to(ROOT).as_posix(),
        'url': report['sourceUrl'], 'kind': 'independent-review-of-primary-official-submission',
        'quote': None, 'locator': 'Verified dates, source conflicts and separate unweighted subgroup columns.',
        'sha256': sha(SOURCE / 'reviewed-rosner-sep30-original.json'),
    }],
    'reason': 'Official original report explicitly verifies September29 10:00 through September30 09:00, wholly after list closure. This revises the existing September30 observation, not a new poll. Prior unknown-fieldwork exclusion is retained in previousDecision and the October6 immutable archive.',
    'accessNote': 'Original filing reports3.1% sampling error versus2.5% in prior broadcast. These descriptive metadata do not alter the published120-seat vector used in the strict trend test. Four unweighted subgroup percentage columns are not national vote shares.',
})
audit['supplementReviewedAt'] = '2026-10-07'
audit['supplementNote'] = ('Original reports now verify existing MaagarSeptember29 and C13September30 fieldwork. '
                           'Earlier exclusions remain in previousDecision and immutable archives; neither filing adds another observation.')
write(path, audit)

new_report = read(SOURCE / 'reviewed-poll.json')
new_id = 'history_hamadad_consortium_2026-10-07_current'
new = by_id[new_id]
assert new['fieldworkStart'] is None and new['fieldworkEnd'] is None
assert new['sampleSize'] == 1013 and sum(new['seats'].values()) == 120
assert new['seats'] == new_report['seats']
document = new_report['sourceDocument']
html = SOURCE / document['fileName']
assert sha(html) == document['sha256'] == '78106cb4b397d4836ea4804ca3698dcd8442312e741cb8778cee2d917b79f013'
path = HERE / 'n12-kan-c13-fieldwork.json'
audit = read(path)
assert new_id not in {row['pollId'] for row in audit['rows']}
audit['rows'].append({
    'pollId': new_id, 'sourcePollId': new_report['id'], 'pollsterId': 'hamadad_consortium',
    'publisher': 'חדשות 13', 'publicationDate': '2026-10-07',
    'fieldworkStart': None, 'fieldworkEnd': None, 'eligibleStrict': False,
    'includeInStrictPostClose': False, 'crossesClosureDate': None,
    'status': 'unknown-fieldwork-original-publication-reviewed', 'sampleSize': 1013,
    'collectionMode': None, 'marginOfErrorPct': 2.5, 'sourceUrl': new_report['sourceUrl'],
    'evidencePath': html.relative_to(ROOT).as_posix(), 'evidenceSha256': sha(html),
    'evidence': [{
        'file': html.relative_to(ROOT).as_posix(), 'url': new_report['sourceUrl'],
        'kind': 'original-publisher-html',
        'quote': '1,013 משיבים בסך הכול, טעות הדגימה 2.5%; NewsArticle.datePublished=2026-10-07T20:35:10+03:00',
        'locator': 'Original methodology supplies respondents and reported error, without fieldwork start/end. Article timestamp establishes publication only.',
        'sha256': sha(html),
    }, {
        'file': (SOURCE / 'reviewed-poll.json').relative_to(ROOT).as_posix(), 'url': new_report['sourceUrl'],
        'kind': 'review-of-original-publication-and-full-report-search',
        'quote': None, 'locator': 'Fieldwork remains null; primary pollster indexes, API and registry checked without a new full report.',
        'sha256': sha(SOURCE / 'reviewed-poll.json'),
    }],
    'reason': 'Original October7 broadcaster article verifies the publication and numbers but not collection dates. This poll is included in the current simulation and descriptive historical archive; excluded from strict post-closure trend testing until the entire fieldwork interval is verified. Dates from the September30 official report are never carried forward.',
})
audit['auditedAt'] = '2026-10-07'
audit['scope'] = 'N12/Midgam, Kantar/Kan/IsraelHayom and Channel13 publications since September9; source decisions supplemented only by verified originals.'
audit['counts'] = {'records': len(audit['rows']),
    'verifiedEligible': sum(row['eligibleStrict'] for row in audit['rows']),
    'unknown': sum(not row['eligibleStrict'] for row in audit['rows'])}
audit['limitations'].append('C13October7 original publication has no verified fieldwork interval and remains excluded; the separate September30 official filing verifies only that older observation. No collection date is inferred or copied between polls.')
write(path, audit)
print('Documented C13October7 exclusion; original September30 fieldwork revision retained with prior decision and hashed primary evidence.')

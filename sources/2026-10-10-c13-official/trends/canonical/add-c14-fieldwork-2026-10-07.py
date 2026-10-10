"""Add only the explicitly verified October 7 NEXT DATA fieldwork interval."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'artifacts/poll-checks/2026-10-07/c13-evening'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


history = read(ROOT / 'data/poll-history.json')
assert history['asOf'] == '2026-10-07' and len(history['polls']) == 110, 'Wait for both new polls and stable canonical ingestion.'
report = read(SOURCE / 'reviewed-c14-primary-poll.json')
assert report['publicationDate'] == report['fieldworkStart'] == report['fieldworkEnd'] == '2026-10-07'
assert report['sampleSize'] == 1100
poll_id = 'history_next_data_2026-10-07_current'
historical = next(row for row in history['polls'] if row['id'] == poll_id)
assert historical['fieldworkStart'] == historical['fieldworkEnd'] == '2026-10-07'
assert historical['sampleSize'] == 1100
assert sum(historical['seats'].values()) == 120
assert all(historical['seats'].get(key, 0) == value for key, value in report['publishedSeats'].items())
html = SOURCE / report['primaryEvidence']['articleFile']
assert sha(html) == report['primaryEvidence']['articleSha256'] == '68a3335e05735b564bdf62f8bbaf03e38f4c0cfc9f83aa63d80bf5ae8198045b'
graphic = next(row for row in report['primaryEvidence']['graphics'] if row['fileName'] == report['primaryEvidence']['seatAndRawGraphic'])
graphic_path = SOURCE / graphic['fileName']
assert sha(graphic_path) == graphic['sha256']
extract = SOURCE / 'c14-1728516.txt'
assert 'נערך היום 7 באוקטובר 2026' in extract.read_text(encoding='utf-8')
path = HERE / 'c14-i24-fieldwork.json'
audit = read(path)
assert poll_id not in {row['pollId'] for row in audit['polls']}
audit['polls'].append({
    'pollId': poll_id, 'sourcePollId': 'next_data_2026-10-07', 'pollsterId': 'next_data',
    'publisher': 'חדשות 14', 'publicationDate': '2026-10-07',
    'fieldworkStart': '2026-10-07', 'fieldworkEnd': '2026-10-07',
    'eligibleStrict': True, 'includeInStrictPostClose': True, 'crossesClosureDate': False,
    'sampleSize': 1100, 'marginOfErrorPct': None, 'collectionMode': None,
    'sourceUrl': report['sourceUrl'], 'evidencePath': html.relative_to(ROOT).as_posix(),
    'evidenceExtractPath': extract.relative_to(ROOT).as_posix(), 'evidenceSha256': sha(html),
    'sourceParagraph': 'הסקר שבוצע באמצעות חברת NEXT DATA בהשתתפות 1100 בוגרים מכלל האוכלוסייה נערך היום 7 באוקטובר 2026 ניתוח הנתונים: שלמה פילבר.',
    'evidence': [{
        'file': html.relative_to(ROOT).as_posix(), 'url': report['sourceUrl'],
        'kind': 'original-publisher-html',
        'quote': 'הסקר שבוצע באמצעות חברת NEXT DATA בהשתתפות 1100 בוגרים מכלל האוכלוסייה נערך היום 7 באוקטובר 2026',
        'locator': 'Original methodology explicitly supplies date of collection, not only article date.',
        'sha256': sha(html),
    }, {
        'file': graphic_path.relative_to(ROOT).as_posix(), 'url': graphic['url'],
        'kind': 'original-publisher-poll-graphic', 'quote': None,
        'locator': 'All published mandates and named below-threshold percentages, independently visually reviewed by source agent and root.',
        'sha256': sha(graphic_path),
    }],
    'certainty': 'verified-explicit-archived-original-publisher-fieldwork-dates',
    'reason': 'Original publisher explicitly says data collection took place October7, wholly after list closure. The two publisher articles describe one mandate survey and are not counted twice. Mode, sampling error and other unpublished metadata remain null.',
})
audit['auditDate'] = '2026-10-07'
audit['notes'].append('NEXT DATAOctober7 original article explicitly verifies same-day collection among1100 adults; missing method/error remain null. One mandate poll is counted despite multiple articles/graphics.')
path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Added one verified NEXT DATAOctober7 fieldwork record; original article and graphic hashes checked.')

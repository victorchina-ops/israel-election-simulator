"""Retain the October 4 Kan source and exclude its unknown fieldwork dates."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / 'artifacts/sources/2026-10-04-kan-update'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


reviewed = read(SRC / 'reviewed-poll.json')
verified = read(SRC / 'verified-kan-2026-10-04.json')
assert reviewed['id'] == 'kantar_2026-10-04'
assert reviewed['fieldworkStart'] is reviewed['fieldworkEnd'] is None
assert reviewed['sampleSize'] == verified['sampleSize'] == 554
source = SRC / reviewed['sourceDocument']['fileName']
assert hashlib.sha256(source.read_bytes()).hexdigest() == reviewed['sourceDocument']['sha256']
broadcast = SRC / reviewed['sourceDocument']['originalBroadcastFileName']
assert hashlib.sha256(broadcast.read_bytes()).hexdigest() == reviewed['sourceDocument']['originalBroadcastSha256']
path = HERE / 'n12-kan-c13-fieldwork.json'
audit = read(path)
row = {
    'pollId': 'history_kantar_2026-10-04_current', 'sourcePollId': 'kantar_2026-10-04',
    'pollsterId': 'kantar', 'publisher': 'כאן חדשות', 'publicationDate': '2026-10-04',
    'fieldworkStart': None, 'fieldworkEnd': None, 'eligibleStrict': False,
    'includeInStrictPostClose': False, 'crossesClosureDate': None,
    'status': 'unknown-fieldwork', 'sampleSize': 554,
    'collectionMode': None, 'marginOfErrorPct': None,
    'sourceUrl': reviewed['sourceUrl'],
    'evidencePath': source.relative_to(ROOT).as_posix(),
    'evidenceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'evidence': [
        {'file': source.relative_to(ROOT).as_posix(), 'url': reviewed['sourceUrl'],
         'kind': 'original-publisher-social-post-and-broadcast',
         'quote': 'Original Kan broadcast names Kantar / Dudi Hasid and sample554; fieldwork dates not disclosed in inspected segment.',
         'locator': 'Kan original broadcast26s,42s,58s,74s; inspected94-second video.',
         'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
        {'file': broadcast.relative_to(ROOT).as_posix(), 'url': reviewed['sourceUrl'],
         'kind': 'original-publisher-broadcast', 'quote': None,
         'locator': 'Original Kan broadcast retained and visually inspected; no verified fieldwork interval.',
         'sha256': hashlib.sha256(broadcast.read_bytes()).hexdigest()},
        {'file': (SRC / 'verified-kan-2026-10-04.json').relative_to(ROOT).as_posix(),
         'url': reviewed['sourceUrl'], 'kind': 'primary-broadcast-review-with-access-limitations',
         'quote': None, 'locator': 'missingMetadataNote and sourceChecks',
         'sha256': hashlib.sha256((SRC / 'verified-kan-2026-10-04.json').read_bytes()).hexdigest()},
    ],
    'reason': 'The original Kan broadcast verifies seats, below-threshold percentages and sample554 but does not disclose fieldwork dates in the inspected segment. '
              'Kan home, politics, news and poll center returned HTTP403. Publication October4 is not used as evidence of collection date; both dates stay null and the poll is excluded strictly.',
    'accessNote': 'Official Kan X post and original broadcast verified. Kan webpages HTTP403. IsraelPolls readable profile exposed posts through October3 and September27 Kantar graphics/table; October4 table not verified.',
}
assert row['pollId'] not in {item['pollId'] for item in audit['rows']}
audit['rows'].append(row)
audit['auditedAt'] = '2026-10-04'
audit['scope'] = 'All11 existing history records with publication>=9September for N12/Midgam, Kantar/Kan/IsraelHayom and Channel13'
audit['counts'] = {'records': len(audit['rows']),
                   'verifiedEligible': sum(item['eligibleStrict'] for item in audit['rows']),
                   'unknown': sum(not item['eligibleStrict'] for item in audit['rows'])}
assert audit['counts'] == {'records': 11, 'verifiedEligible': 9, 'unknown': 2}
audit['limitations'].append('Kan October4 stays excluded: the original broadcast was verified but fieldwork dates were not disclosed; no publication-date imputation.')
path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Added Kan October4 with null fieldwork, explicit strict exclusion and hashed original-source evidence.')

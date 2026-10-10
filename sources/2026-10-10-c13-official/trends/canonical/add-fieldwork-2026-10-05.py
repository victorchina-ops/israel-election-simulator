"""Add explicitly dated original N12 fieldwork to the strict post-close audit."""
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / 'artifacts/sources/2026-10-05-n12-update'
reviewed = json.loads((SRC / 'reviewed-poll.json').read_text(encoding='utf-8-sig'))
assert reviewed['id'] == 'midgam_geva_2026-10-05'
assert reviewed['date'] == reviewed['fieldworkStart'] == reviewed['fieldworkEnd'] == '2026-10-05'
assert reviewed['sampleSize'] == 501
document = reviewed['sourceDocument']
source = SRC / document['fileName']
checksum = hashlib.sha256(source.read_bytes()).hexdigest()
assert checksum == document['sha256']
text = BeautifulSoup(source.read_text(encoding='utf-8'), 'html.parser').get_text(' ', strip=True)
quote = 'מועד איסוף הנתונים: 5.10.2026'
assert quote in text and 'מספר המשיבים בפועל: 501' in text
path = HERE / 'n12-kan-c13-fieldwork.json'
audit = json.loads(path.read_text(encoding='utf-8-sig'))
row = {
    'pollId': 'history_midgam_geva_2026-10-05_current',
    'sourcePollId': reviewed['id'], 'pollsterId': 'midgam_geva',
    'publisher': 'חדשות 12', 'publicationDate': reviewed['date'],
    'fieldworkStart': reviewed['fieldworkStart'], 'fieldworkEnd': reviewed['fieldworkEnd'],
    'eligibleStrict': True, 'includeInStrictPostClose': True,
    'crossesClosureDate': False, 'status': 'verified-after-closure',
    'sampleSize': reviewed['sampleSize'], 'collectionMode': reviewed['samplingMethod'],
    'marginOfErrorPct': reviewed['reportedMarginOfErrorPct'],
    'sourceUrl': reviewed['sourceUrl'],
    'evidencePath': source.relative_to(ROOT).as_posix(), 'evidenceSha256': checksum,
    'evidence': [{
        'file': source.relative_to(ROOT).as_posix(), 'url': reviewed['sourceUrl'],
        'kind': 'primary-publisher-html', 'quote': quote,
        'locator': 'methodology section; actual respondents501; maximum sampling error4.4%',
        'sha256': checksum,
    }],
    'reason': 'Original publisher explicitly states fieldwork5October2026, after September8 list closure. Actual respondents501; internet and telephone stratified random sampling. No publication-date substitution is used.',
    'accessNote': 'Original N12 article, home, politics and elections index accessible; IsraelPolls original branded broadcast graphic verified. No new October5 historical table exposed at initial check.',
}
assert row['pollId'] not in {item['pollId'] for item in audit['rows']}
audit['rows'].append(row)
audit['auditedAt'] = '2026-10-05'
audit['scope'] = 'All12 existing history records with publication>=9September for N12/Midgam, Kantar/Kan/IsraelHayom and Channel13'
audit['counts'] = {'records': len(audit['rows']),
                   'verifiedEligible': sum(item['eligibleStrict'] for item in audit['rows']),
                   'unknown': sum(not item['eligibleStrict'] for item in audit['rows'])}
assert audit['counts'] == {'records': 12, 'verifiedEligible': 10, 'unknown': 2}
audit['limitations'].append('N12 October5 fieldwork is explicitly verified in the original publisher methodology and extends the strict cohort. Kan October4 remains excluded because its fieldwork dates remain unknown.')
path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Verified N12 October5 fieldwork included strictly, with original-source SHA evidence.')

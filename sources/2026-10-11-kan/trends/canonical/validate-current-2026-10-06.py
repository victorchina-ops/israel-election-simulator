"""Cross-check the October 6 strict summaries against independent counts."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


bloc = read(HERE / 'analysis.json')
bloc_independent = read(HERE / 'independent-strict-numeric-audit.json')
party = read(HERE / 'party-analysis.json')
party_independent = read(HERE / 'party-independent.json')
snapshot = read(ROOT / 'data/strict-party-trends.json')
comparison = read(ROOT / 'artifacts/2026-10-06-comparison/strict-trends-comparison.json')
assert bloc['asOf'] == party['asOf'] == snapshot['asOf'] == '2026-10-06'
assert len(bloc['cohort']) == len(party['cohort']) == len(snapshot['cohort']) == 37
assert bloc['cohort'] == party['cohort']
added = [row for row in bloc['cohort'] if row['pollId'] == 'history_maagar_mochot_2026-10-06_current']
assert len(added) == 1 and added == comparison['addedPolls']
new = added[0]
assert new['pollsterId'] == 'maagar_mochot' and new['publicationDate'] == '2026-10-06'
assert new['eligibleStrict'] and new['fieldworkStart'] == '2026-10-05' and new['fieldworkEnd'] == '2026-10-06'
expected_polls = 32
assert bloc['primary']['nPolls'] == party['primary']['nPolls'] == snapshot['coverage']['pollCount'] == expected_polls
assert bloc['primary']['nPollsters'] == party['primary']['nSeries'] == 8
assert bloc['primary']['nDeltas'] == party['primary']['nDeltas'] == expected_polls - 8
eligible = [row for row in bloc['cohort'] if row['eligibleStrict']]
for row in eligible:
    assert '2026-09-09' <= row['fieldworkStart'] <= row['fieldworkEnd'] <= row['publicationDate']
if not new['eligibleStrict']:
    assert new['fieldworkStart'] is None and new['fieldworkEnd'] is None
exact_permutations = math.prod(math.factorial(len(row['pollIds'])) for row in bloc['primary']['byPollster'])
assert exact_permutations == 343_985_356_800
assert bloc['primary']['exactCounting']['nPermutations'] == party['primary']['exactCounting']['nPermutations'] == exact_permutations
assert bloc_independent['total'] == party_independent['nPermutations'] == exact_permutations
assert bloc_independent['cohortPolls'] == party_independent['nPolls'] == expected_polls
assert bloc_independent['counts'] == bloc['primary']['exactCounting']['extremeCounts']
for index, row in enumerate(bloc['primary']['overall']):
    assert abs(row['slopePerWeek'] - bloc_independent['slopes'][index]) < 1e-12
    assert row['pValue'] == bloc_independent['p'][index]
independent_party = {row['partyId']: row for row in party_independent['overall']}
for row in party['primary']['overall']:
    other = independent_party[row['partyId']]
    for key, independent_key in (
        ('slopePerWeek', 'slopePerWeek'), ('weightedNetDelta', 'netDelta'),
        ('pValue', 'p'), ('qValue', 'q'),
        ('wholeSeriesSignFlipP', 'signFlipP'), ('wholeSeriesSignFlipQ', 'signFlipQ'),
    ):
        assert abs(row[key] - other[independent_key]) < 1e-12, (row['partyId'], key)
assert len(snapshot['rows']) == len(independent_party) == 17
assert snapshot['provenance']['analysisSha256'] == hashlib.sha256((HERE / 'party-analysis.json').read_bytes()).hexdigest()
assert party['historySha256'] == hashlib.sha256((ROOT / 'data/poll-history.json').read_bytes()).hexdigest()
evidence = []
for row in [new] + [item['after'] for item in comparison['revisedExistingPolls']]:
    if row.get('evidencePath'):
        evidence.append((row['evidencePath'], row['evidenceSha256']))
    evidence.extend((item['file'], item['sha256']) for item in row.get('evidence', []) if item.get('file') and item.get('sha256'))
assert evidence, 'New fieldwork decision must retain inspectable hashed original evidence.'
for filename, checksum in evidence:
    assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == checksum
report = {
    'passed': True, 'asOf': '2026-10-06', 'polls': expected_polls,
    'series': 8, 'deltas': expected_polls - 8, 'parties': 17, 'individualTests': 136,
    'exactPermutations': exact_permutations, 'newMaagarEligibleStrict': new['eligibleStrict'],
    'excludedPollCount': 37 - expected_polls,
    'independentAgreement': 'All bloc slopes, exact counts and p-values; all party slopes, net changes, exact p/q and sign-flip p/q within 1e-12',
    'sourceEvidenceSha256Verified': True,
    'correctedPartyFindings': [row['partyId'] for row in party['primary']['overall'] if row['qValue'] < .05],
    'correctedBlocFindings': [row['group'] for row in bloc['primary']['overall'] if row['qValue'] < .05],
    'noCorrectedPartyFindings': all(row['qValue'] >= .05 for row in party['primary']['overall']),
    'noCorrectedBlocSensitivityFindings': all(row['wholeInstituteSignFlipQ'] >= .05 for row in bloc['primary']['overall']),
}
(HERE / 'party-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

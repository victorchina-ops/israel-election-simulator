"""Validate the 9 Oct Lazar addition and both independent exact replays."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARCHIVE = ROOT / 'data/history/before-maariv-2026-10-09'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

bloc = read(HERE / 'analysis.json')
party = read(HERE / 'party-analysis.json')
bi = read(HERE / 'independent-strict-numeric-audit.json')
pi = read(HERE / 'party-independent.json')
snapshot = read(ROOT / 'data/strict-party-trends.json')
current = read(ROOT / 'data/current-polls.json')
history = read(ROOT / 'data/poll-history.json')
before = read(ARCHIVE / 'artifacts/strict-post-close/analysis.json')

assert current['asOf'] == history['asOf'] == '2026-10-09'
assert len(current['polls']) == 8 and len(history['polls']) == 114
assert bloc['cohort'] == party['cohort']
assert len(bloc['cohort']) == 43
assert bloc['primary']['nPolls'] == party['primary']['nPolls'] == bi['cohortPolls'] == pi['nPolls'] == 39
assert bloc['primary']['nDeltas'] == party['primary']['nDeltas'] == 31
assert snapshot['coverage'] == {
    **snapshot['coverage'],
    'pollCount': 39,
    'seriesCount': 8,
    'deltaCount': 31,
    'partyCount': 17,
    'to': '2026-10-08',
    'excludedPollCount': 4,
}

eligible = {r['pollId'] for r in bloc['cohort'] if r['eligibleStrict']}
old_eligible = {r['pollId'] for r in before['cohort'] if r['eligibleStrict']}
expected = {'history_lazar_2026-10-09_current'}
assert eligible - old_eligible == expected and not old_eligible - eligible
new_record = next(r for r in bloc['cohort'] if r['pollId'] in expected)
assert new_record['pollsterId'] == 'lazar'
assert new_record['fieldworkStart'] == '2026-10-07'
assert new_record['fieldworkEnd'] == '2026-10-08'
assert new_record['publicationDate'] == '2026-10-09'
for record in bloc['cohort']:
    if record['eligibleStrict']:
        assert '2026-09-09' <= record['fieldworkStart'] <= record['fieldworkEnd'] <= record['publicationDate']
for evidence in new_record['evidence']:
    evidence_path = ROOT / evidence['file']
    assert evidence_path.is_file(), evidence_path
    assert sha(evidence_path) == evidence['sha256'], evidence_path

exact = math.prod(math.factorial(len(s['pollIds'])) for s in bloc['primary']['byPollster'])
assert exact == 36118462464000000
bloc_exact = bloc['primary']['exactCounting']
party_exact = party['primary']['exactCounting']
assert int(bloc_exact['nPermutationsExact']) == exact
assert int(party_exact['nPermutationsExact']) == exact
assert int(str(bi['totalExact'])) == exact
assert int(str(pi['nPermutationsExact'])) == exact
assert bloc_exact['nPermutations'] == party_exact['nPermutations'] == bi['total'] == pi['nPermutations']
assert [int(v) for v in bloc_exact['extremeCountsExact']] == [int(v) for v in bi['countsExact']]
assert bloc_exact['extremeCounts'] == bi['counts']
assert snapshot['methodology']['permutationsExact'] == str(exact)

for index, row in enumerate(bloc['primary']['overall']):
    count = int(bloc_exact['extremeCountsExact'][index])
    assert abs(row['pValue'] - count / exact) < 1e-15
    assert abs(row['slopePerWeek'] - bi['slopes'][index]) < 1e-12
    assert abs(row['pValue'] - bi['p'][index]) < 1e-12

independent = {r['partyId']: r for r in pi['overall']}
for index, row in enumerate(party['primary']['overall']):
    other = independent[row['partyId']]
    count = int(party_exact['extremeCountsExact'][index])
    assert count == int(other['extremeCountExact'])
    assert abs(row['pValue'] - count / exact) < 1e-15
    for key, alias in [('slopePerWeek', 'slopePerWeek'), ('weightedNetDelta', 'netDelta'), ('pValue', 'p'),
                       ('qValue', 'q'), ('wholeSeriesSignFlipP', 'signFlipP'), ('wholeSeriesSignFlipQ', 'signFlipQ')]:
        assert abs(row[key] - other[alias]) < 1e-12, (row['partyId'], key)

assert party['historySha256'] == sha(ROOT / 'data/poll-history.json')
assert snapshot['provenance']['analysisSha256'] == sha(HERE / 'party-analysis.json')
report = {
    'passed': True,
    'asOf': '2026-10-09',
    'polls': 39,
    'series': 8,
    'deltas': 31,
    'parties': 17,
    'individualTests': 136,
    'exactPermutations': str(exact),
    'excludedPollCount': 4,
    'addedPollCount': 1,
    'newlyEligiblePollIds': sorted(expected),
    'lastVerifiedFieldworkEnd': snapshot['coverage']['to'],
    'independentAgreement': 'All exact bloc counts and party p/q, slopes, net deltas and signflip p/q agree within 1e-12',
    'correctedPartyFindings': [r['partyId'] for r in party['primary']['overall'] if r['qValue'] < .05],
    'correctedBlocFindings': [r['group'] for r in bloc['primary']['overall'] if r['qValue'] < .05],
    'correctedPartySensitivityFindings': [r['partyId'] for r in party['primary']['overall'] if r['wholeSeriesSignFlipQ'] < .05],
    'correctedBlocSensitivityFindings': [r['group'] for r in bloc['primary']['overall'] if r['wholeInstituteSignFlipQ'] < .05],
    'sourceEvidenceSha256Verified': True,
}
(HERE / 'party-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

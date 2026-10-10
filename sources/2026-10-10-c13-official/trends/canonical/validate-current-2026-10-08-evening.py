"""Validate the three new observations and independently computed exact tests."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bloc, party = read(HERE / 'analysis.json'), read(HERE / 'party-analysis.json')
bi, pi = read(HERE / 'independent-strict-numeric-audit.json'), read(HERE / 'party-independent.json')
snapshot = read(ROOT / 'data/strict-party-trends.json')
before = read(HERE / 'archive-2026-10-08-metadata/analysis.json')
assert bloc['cohort'] == party['cohort']
assert len(bloc['cohort']) == 42
assert bloc['primary']['nPolls'] == party['primary']['nPolls'] == bi['cohortPolls'] == pi['nPolls'] == 38
assert bloc['primary']['nDeltas'] == party['primary']['nDeltas'] == 30
assert snapshot['coverage']['pollCount'] == 38 and snapshot['coverage']['excludedPollCount'] == 4
eligible = {r['pollId'] for r in bloc['cohort'] if r['eligibleStrict']}
old_eligible = {r['pollId'] for r in before['cohort'] if r['eligibleStrict']}
expected = {f'history_{institute}_2026-10-08_current' for institute in ['kantar', 'direct_polls', 'tatika']}
assert eligible - old_eligible == expected and not old_eligible - eligible
for record in bloc['cohort']:
    if record['eligibleStrict']:
        assert '2026-09-09' <= record['fieldworkStart'] <= record['fieldworkEnd'] <= record['publicationDate']
    if record['pollId'] in expected:
        assert record['fieldworkStart'] == '2026-10-07'
        assert record['fieldworkEnd'] == ('2026-10-07' if record['pollsterId'] == 'direct_polls' else '2026-10-08')
        for evidence in record['evidence']:
            assert sha(ROOT / evidence['file']) == evidence['sha256']
assert bloc['primary']['exactCounting']['extremeCounts'] == bi['counts']
exact = math.prod(math.factorial(len(s['pollIds'])) for s in bloc['primary']['byPollster'])
assert exact == bi['total'] == pi['nPermutations'] == party['primary']['exactCounting']['nPermutations']
for index, row in enumerate(bloc['primary']['overall']):
    assert abs(row['slopePerWeek'] - bi['slopes'][index]) < 1e-12
    assert abs(row['pValue'] - bi['p'][index]) < 1e-12
independent = {r['partyId']: r for r in pi['overall']}
for row in party['primary']['overall']:
    for key, alias in [('slopePerWeek', 'slopePerWeek'), ('weightedNetDelta', 'netDelta'), ('pValue', 'p'),
                       ('qValue', 'q'), ('wholeSeriesSignFlipP', 'signFlipP'), ('wholeSeriesSignFlipQ', 'signFlipQ')]:
        assert abs(row[key] - independent[row['partyId']][alias]) < 1e-12, (row['partyId'], key)
assert party['historySha256'] == sha(ROOT / 'data/poll-history.json')
assert snapshot['provenance']['analysisSha256'] == sha(HERE / 'party-analysis.json')
report = {'passed': True, 'asOf': '2026-10-08', 'polls': 38, 'series': 8, 'deltas': 30, 'parties': 17,
 'individualTests': 136, 'exactPermutations': exact, 'excludedPollCount': 4, 'addedPollCount': 3,
 'newlyEligiblePollIds': sorted(expected), 'lastVerifiedFieldworkEnd': snapshot['coverage']['to'],
 'independentAgreement': 'All exact bloc counts and party p/q, slopes, net deltas and signflip p/q agree within 1e-12',
 'correctedPartyFindings': [r['partyId'] for r in party['primary']['overall'] if r['qValue'] < .05],
 'correctedBlocFindings': [r['group'] for r in bloc['primary']['overall'] if r['qValue'] < .05],
 'correctedPartySensitivityFindings': [r['partyId'] for r in party['primary']['overall'] if r['wholeSeriesSignFlipQ'] < .05],
 'correctedBlocSensitivityFindings': [r['group'] for r in bloc['primary']['overall'] if r['wholeInstituteSignFlipQ'] < .05],
 'sourceEvidenceSha256Verified': True}
(HERE / 'party-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

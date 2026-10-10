"""Validate the October 10 official C13 metadata revision and exact trend replays.

The checkpoint is immutable. This changes no raw observation, historical weight,
app source or dated experiment. Only the operational validation and this dated
receipt are written after every assertion passes.
"""
from __future__ import annotations

from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-10-10'
CHECKPOINT = ROOT / 'artifacts/poll-checks/2026-10-10/before'
STRICT = ROOT / 'artifacts/strict-post-close'
RECEIPT = ROOT / 'artifacts/poll-checks/2026-10-10/c13-official-revision-validation.json'
CURRENT_ID = 'hamadad_consortium_2026-10-07'
HISTORY_ID = 'history_hamadad_consortium_2026-10-07_current'
OFFICIAL_URL = 'https://www.gov.il/BlobFolder/dynamiccollectorresultitem/knesset_election101/he/Survey_4193.pdf'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual, expected, label):
    assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12), (label, actual, expected)


def index(rows, key):
    result = {row[key]: row for row in rows}
    assert len(result) == len(rows), ('duplicate', key)
    return result


def bh(rows, pkey, qkey):
    ordered = sorted(rows, key=lambda row: row[pkey])
    running = 1.0
    for rank in range(len(ordered), 0, -1):
        row = ordered[rank - 1]
        running = min(running, row[pkey] * len(ordered) / rank, 1.0)
        close(row[qkey], running, ('BH', pkey, row.get('partyId', row.get('group', row.get('pollsterId')))))


def midpoint(row):
    return (date.fromisoformat(row['fieldworkStart']).toordinal() +
            date.fromisoformat(row['fieldworkEnd']).toordinal()) / 2


def immutable_write(path, value):
    body = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if path.exists():
        assert path.read_bytes() == body, f'Dated receipt differs; preserve it and use a distinct reviewed run: {path}'
    else:
        path.write_bytes(body)


paths = ['data/current-polls.json', 'data/poll-history.json', 'data/strict-party-trends.json',
         'data/calibration.json', 'data/parties.json', 'artifacts/strict-post-close/analysis.json',
         'artifacts/strict-post-close/party-analysis.json',
         'artifacts/strict-post-close/independent-strict-numeric-audit.json',
         'artifacts/strict-post-close/party-independent.json']
for relative in paths:
    assert (ROOT / relative).is_file(), relative
    if relative not in {'data/calibration.json', 'data/parties.json'}:
        assert (CHECKPOINT / relative).is_file(), ('missing checkpoint', relative)
checkpoint_hashes = {path.relative_to(CHECKPOINT).as_posix(): sha(path)
                     for path in CHECKPOINT.rglob('*') if path.is_file()}
checkpoint_manifest = read(CHECKPOINT / 'manifest.json')
for relative, expected in checkpoint_manifest['files'].items():
    assert sha(CHECKPOINT / relative) == expected, ('checkpoint manifest mismatch', relative)
input_hashes = {relative: sha(ROOT / relative) for relative in paths}
current, history, snapshot, calibration, parties, bloc, party, bi, pi = [read(ROOT / relative) for relative in paths]
before_current = read(CHECKPOINT / paths[0])
before_history = read(CHECKPOINT / paths[1])
before_snapshot = read(CHECKPOINT / paths[2])
before_bloc = read(CHECKPOINT / paths[5])
before_party = read(CHECKPOINT / paths[6])
assert current['asOf'] == history['asOf'] == snapshot['asOf'] == bloc['asOf'] == party['asOf'] == DAY
assert before_current['asOf'] == before_history['asOf'] == before_snapshot['asOf'] == '2026-10-09'
before_dashboard = read(CHECKPOINT / 'dashboard/src/data.json')
before_input = {row['key']: row['value'] for row in before_dashboard['queries']['model_input']['rows']}
before_calibration = dict(before_input['calibration'])
before_calibration.pop('pollCorrelation', None)
assert calibration == before_calibration, 'historical weighting changed'
assert parties == before_input['parties'], 'party catalogue changed'

# Preserve IDs, all other observations, every mandate and every published share.
old_current = index(before_current['polls'], 'id')
new_current = index(current['polls'], 'id')
old_history = index(before_history['polls'], 'id')
new_history = index(history['polls'], 'id')
assert set(old_current) == set(new_current) and set(old_history) == set(new_history)
assert len(new_current) == len(old_current) == 8 and len(new_history) == len(old_history) == 114
for old_rows, new_rows, target_id in [(old_current, new_current, CURRENT_ID), (old_history, new_history, HISTORY_ID)]:
    for poll_id, old in old_rows.items():
        new = new_rows[poll_id]
        if poll_id != target_id:
            assert new == old, ('unrelated observation changed', poll_id)
        else:
            protected = ['seats', 'seatTotal', 'percentages', 'reportedPercentages', 'percentageBounds',
                         'sourceBlocSeats', 'requiresReconstruction', 'knownPercentageSum', 'originalCoveragePct',
                         'unmodelledNamedParties', 'undecidedPct', 'reportedBelowThresholdTotalPct',
                         'belowThresholdNamedSumPct', 'belowThresholdUnexplainedDifferencePP']
            for key in protected:
                assert (key in new) == (key in old), (poll_id, 'presence', key)
                assert new.get(key) == old.get(key), (poll_id, 'published result changed', key)
        assert sum(new['seats'].values()) == 120, poll_id
        assert all(isinstance(value, int) and value >= 0 for value in new['seats'].values()), poll_id

active = new_current[CURRENT_ID]
archived = new_history[HISTORY_ID]
for row in [active, archived]:
    assert row['date'] == '2026-10-07'
    assert (row['fieldworkStart'], row['fieldworkEnd']) == ('2026-10-06', '2026-10-07')
    assert (row['fieldworkStartTime'], row['fieldworkEndTime']) == ('09:00', '09:00')
    assert row['sampleSize'] == 1263 and row['reportedMarginOfErrorPct'] == 2.8
    assert row.get('samplingMethod') and row.get('population'), 'official method/population still missing'
    assert OFFICIAL_URL in json.dumps(row, ensure_ascii=False), 'official report provenance missing'
    for party_id, seats in row['seats'].items():
        if seats > 0:
            assert party_id not in row['percentages'] and party_id not in row['reportedPercentages'], ('invented national percentage', party_id)
assert archived['sourcePollId'] == active['id']
for key in set(active) | set(archived):
    if key not in {'id', 'recordStatus', 'sourcePollId', 'archiveSourceUrl'}:
        assert active.get(key) == archived.get(key), ('current/history mismatch', key)

# Check the unchanged strict membership and the corrected original interval.
assert bloc['cohort'] == party['cohort']
old_cohort = index(before_bloc['cohort'], 'pollId')
new_cohort = index(bloc['cohort'], 'pollId')
assert set(old_cohort) == set(new_cohort)
assert {key for key, row in old_cohort.items() if row['eligibleStrict']} == {key for key, row in new_cohort.items() if row['eligibleStrict']}
for poll_id, old in old_cohort.items():
    row = new_cohort[poll_id]
    if poll_id != HISTORY_ID:
        assert row == old, ('unrelated cohort metadata changed', poll_id)
    if row['eligibleStrict']:
        assert '2026-09-09' <= row['fieldworkStart'] <= row['fieldworkEnd'] <= row['publicationDate']
c13 = new_cohort[HISTORY_ID]
assert c13['publicationDate'] == '2026-10-07' and c13['eligibleStrict']
assert (c13['fieldworkStart'], c13['fieldworkEnd']) == ('2026-10-06', '2026-10-07')
assert c13['sampleSize'] == 1263 and c13['marginOfErrorPct'] == 2.8
assert midpoint(c13) - midpoint(old_cohort[HISTORY_ID]) == 0.5
assert OFFICIAL_URL in json.dumps(c13, ensure_ascii=False)
evidence_hashes = {}
for evidence in c13.get('evidence', []):
    if evidence.get('file') and evidence.get('sha256'):
        path = ROOT / evidence['file']
        assert path.is_file() and sha(path) == evidence['sha256'], path
        evidence_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
assert evidence_hashes, 'missing hashed original evidence'
if c13.get('evidencePath') and c13.get('evidenceSha256'):
    assert sha(ROOT / c13['evidencePath']) == c13['evidenceSha256']

assert bloc['normalizedHistoricalWeights'] == party['normalizedHistoricalWeights'] == before_bloc['normalizedHistoricalWeights']
close(sum(bloc['normalizedHistoricalWeights'].values()), 1, 'normalized weights')
coverage = snapshot['coverage']
assert coverage == before_snapshot['coverage']
assert (coverage['pollCount'], coverage['seriesCount'], coverage['deltaCount'], coverage['partyCount']) == (39, 8, 31, 17)
assert len(new_cohort) == len(old_cohort) == 43 and coverage['excludedPollCount'] == 4
assert len(party['testedPartyIds']) == len(snapshot['rows']) == 17
assert len({row['partyId'] for row in snapshot['rows']}) == 17
assert snapshot['weightMode'] == before_snapshot['weightMode'] == 'quality'
assert snapshot['methodology']['fixedSnapshot'] and not snapshot['methodology']['usesCurrentControls']
assert snapshot['provenance']['historySha256'] == bloc['historySha256'] == party['historySha256'] == input_hashes[paths[1]]
assert snapshot['provenance']['analysisSha256'] == input_hashes[paths[6]]
assert snapshot['provenance']['partiesSha256'] == party['partiesSha256'] == input_hashes[paths[4]]
assert snapshot['weights'] == before_snapshot['weights']
assert [{key: value for key, value in row.items() if key != 'byPollster'} for row in snapshot['rows']] == party['primary']['overall']

# Membership is fixed, so permutation universes and multiplicity families stay fixed.
exact = math.prod(math.factorial(len(series['pollIds'])) for series in bloc['primary']['byPollster'])
old_exact = math.prod(math.factorial(len(series['pollIds'])) for series in before_bloc['primary']['byPollster'])
assert exact == old_exact
assert int(bi['totalExact']) == int(pi['nPermutationsExact']) == exact
assert bi['cohortPolls'] == pi['nPolls'] == coverage['pollCount']
assert bi['cohortPollsters'] == pi['nSeries'] == coverage['seriesCount']
assert pi['nParties'] == coverage['partyCount'] and pi['nIndividualTests'] == coverage['partyCount'] * coverage['seriesCount']
assert pi['historySha256'] == input_hashes[paths[1]] and pi['cohortSha256'] == input_hashes[paths[5]]
for doc, old in [(bloc, before_bloc), (party, before_party)]:
    assert doc['normalizedHistoricalWeights'] == old['normalizedHistoricalWeights']
    for axis in ['primary', 'publicationDateSensitivity']:
        result = doc[axis]
        assert result['nPolls'] == old[axis]['nPolls'] == coverage['pollCount']
        assert result['nDeltas'] == old[axis]['nDeltas'] == coverage['deltaCount']
        assert int(result['exactCounting']['nPermutationsExact']) == exact
        for number, count in zip(result['exactCounting']['pValues'], result['exactCounting']['extremeCountsExact']):
            close(number, int(count) / exact, ('exact probability', axis))
        series_before = index(old[axis]['byPollster'], 'pollsterId')
        for series in result['byPollster']:
            prior = series_before[series['pollsterId']]
            assert series['pollIds'] == prior['pollIds']
            if axis == 'primary':
                verified_times = [midpoint(new_cohort[poll_id]) for poll_id in series['pollIds']]
                expected = [value - verified_times[0] for value in verified_times]
                assert series['timeDaysFromFirst'] == expected
                if series['pollsterId'] == 'hamadad_consortium':
                    assert expected[:-1] == prior['timeDaysFromFirst'][:-1]
                    assert expected[-1] == prior['timeDaysFromFirst'][-1] + 0.5
                else:
                    assert expected == prior['timeDaysFromFirst']
    # Publication dates and seats did not change, so that sensitivity is identical.
    assert doc['publicationDateSensitivity']['overall'] == old['publicationDateSensitivity']['overall']
    assert doc['publicationDateSensitivity']['exactCounting'] == old['publicationDateSensitivity']['exactCounting']

# Independent canonical bloc tail counts and independently computed BH/sign flips.
assert [int(value) for value in bloc['primary']['exactCounting']['extremeCountsExact']] == [int(value) for value in bi['countsExact']]
for i, row in enumerate(bloc['primary']['overall']):
    close(row['slopePerWeek'], bi['slopes'][i], ('bloc slope', row['group']))
    close(row['pValue'], bi['p'][i], ('bloc p', row['group']))
    contributions = [series['weight'] * next(value['slopePerWeek'] for value in series['groups'] if value['group'] == row['group']) for series in bloc['primary']['byPollster']]
    extremes = sum(abs(sum(sign * value for sign, value in zip(signs, contributions))) >= abs(row['slopePerWeek']) - 1e-12 for signs in itertools.product([-1, 1], repeat=len(contributions)))
    close(row['wholeInstituteSignFlipP'], extremes / (2 ** len(contributions)), ('bloc sign flips', row['group']))
bh(bloc['primary']['overall'], 'pValue', 'qValue')
bh(bloc['primary']['overall'], 'wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ')
bh([row for series in bloc['primary']['byPollster'] for row in series['groups']], 'pValue', 'qValue')
independent_parties = index(pi['overall'], 'partyId')
for i, row in enumerate(party['primary']['overall']):
    other = independent_parties[row['partyId']]
    assert int(party['primary']['exactCounting']['extremeCountsExact'][i]) == int(other['extremeCountExact'])
    for key, alias in [('slopePerWeek', 'slopePerWeek'), ('weightedNetDelta', 'netDelta'), ('pValue', 'p'), ('qValue', 'q'), ('wholeSeriesSignFlipP', 'signFlipP'), ('wholeSeriesSignFlipQ', 'signFlipQ')]:
        close(row[key], other[alias], ('party independent', row['partyId'], key))
bh(party['primary']['overall'], 'pValue', 'qValue')
bh(party['primary']['overall'], 'wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ')
bh([row for series in party['primary']['byPollster'] for row in series['parties']], 'pValue', 'qValue')
assert all(sha(ROOT / relative) == value for relative, value in input_hashes.items()), 'inputs changed during validation'
assert all(sha(CHECKPOINT / relative) == value for relative, value in checkpoint_hashes.items()), 'immutable checkpoint changed'

report = {
    'passed': True, 'status': 'PASS', 'asOf': DAY, 'newPollCount': 0,
    'activePolls': len(new_current), 'historyPolls': len(new_history),
    'polls': coverage['pollCount'], 'series': coverage['seriesCount'], 'deltas': coverage['deltaCount'],
    'parties': coverage['partyCount'], 'individualTests': pi['nIndividualTests'],
    'exactPermutations': str(exact), 'excludedPollCount': coverage['excludedPollCount'],
    'changedActivePollIds': [CURRENT_ID], 'changedHistoryPollIds': [HISTORY_ID],
    'fieldworkCorrection': {'publicationDate': active['date'], 'before': ['2026-10-06', '2026-10-06'], 'after': ['2026-10-06', '2026-10-07'], 'times': ['09:00', '09:00'], 'midpointChangeDays': 0.5},
    'allPublishedSeatsAndPercentagesPreserved': True, 'missingNationalSharesPreserved': True,
    'allOtherObservationsPreserved': True, 'sameCohortMembershipAndHistoricalWeights': True,
    'publicationAxisSensitivityUnchanged': True,
    'independentAgreement': 'Exact bloc/party tail counts, slopes, p/q and whole-institute sensitivity agree within 1e-12',
    'correctedPartyFindings': [row['partyId'] for row in party['primary']['overall'] if row['qValue'] < .05],
    'correctedBlocFindings': [row['group'] for row in bloc['primary']['overall'] if row['qValue'] < .05],
    'correctedPartySensitivityFindings': [row['partyId'] for row in party['primary']['overall'] if row['wholeSeriesSignFlipQ'] < .05],
    'correctedBlocSensitivityFindings': [row['group'] for row in bloc['primary']['overall'] if row['wholeInstituteSignFlipQ'] < .05],
    'sourceEvidenceSha256Verified': True, 'sourceEvidenceHashes': evidence_hashes,
    'inputHashes': input_hashes, 'checkpointHashes': checkpoint_hashes,
    'validatorSha256': sha(Path(__file__)), 'checkpoint': CHECKPOINT.relative_to(ROOT).as_posix(),
}
# Refuse changed same-day evidence before updating the operational validation.
immutable_write(RECEIPT, report)
(STRICT / 'party-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: report[key] for key in ['status', 'asOf', 'newPollCount', 'polls', 'series', 'deltas', 'parties', 'exactPermutations', 'correctedPartyFindings', 'correctedBlocFindings']}, ensure_ascii=False))

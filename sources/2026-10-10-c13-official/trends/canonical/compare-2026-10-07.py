"""Compare the October 7 strict update with the immutable October 6 audit.

Only verified primary fieldwork can change eligibility. Original reports that
supplement a historical poll revise its record instead of creating another poll.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEFORE = HERE / 'archive-2026-10-06'
NEW_IDS = ['history_hamadad_consortium_2026-10-07_current', 'history_next_data_2026-10-07_current']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def compare(filename, key, fields):
    old, new = read(BEFORE / filename), read(HERE / filename)
    assert old['asOf'] == '2026-10-06' and new['asOf'] == '2026-10-07'
    before = {row['pollId']: row for row in old['cohort']}
    after = {row['pollId']: row for row in new['cohort']}
    added = sorted(set(after) - set(before))
    assert added == NEW_IDS and set(before) <= set(after)
    revised = sorted(poll_id for poll_id in before if before[poll_id] != after[poll_id])
    for poll_id in revised:
        first, last = before[poll_id], after[poll_id]
        assert first['pollsterId'] == last['pollsterId'] == 'hamadad_consortium'
        for identity in ('pollId', 'pollsterId', 'publicationDate'):
            assert first[identity] == last[identity]
        assert last['previousDecision'] == first
        assert first['fieldworkStart'] is None and first['fieldworkEnd'] is None
        assert last['eligibleStrict'] and last['fieldworkStart'] >= '2026-09-09'
    assert after[NEW_IDS[0]]['pollsterId'] == 'hamadad_consortium'
    assert after[NEW_IDS[1]]['pollsterId'] == 'next_data'
    assert after[NEW_IDS[1]]['eligibleStrict']
    assert after[NEW_IDS[1]]['fieldworkStart'] == after[NEW_IDS[1]]['fieldworkEnd'] == '2026-10-07'
    newly_eligible = [poll_id for poll_id in added + revised
                      if after[poll_id]['eligibleStrict'] and not before.get(poll_id, {}).get('eligibleStrict', False)]
    axes = {}
    for axis in ('primary', 'publicationDateSensitivity'):
        previous, current = old[axis], new[axis]
        assert current['nPolls'] == previous['nPolls'] + len(newly_eligible)
        nseries_key = 'nPollsters' if key == 'group' else 'nSeries'
        assert current[nseries_key] == previous[nseries_key] == 8
        assert current['nDeltas'] == current['nPolls'] - current[nseries_key]
        previous_series = {row['pollsterId']: row for row in previous['byPollster']}
        current_series = {row['pollsterId']: row for row in current['byPollster']}
        assert set(current_series) == set(previous_series)
        for pollster_id in current_series:
            extra = [poll_id for poll_id in newly_eligible if after[poll_id]['pollsterId'] == pollster_id]
            assert set(current_series[pollster_id]['pollIds']) == set(previous_series[pollster_id]['pollIds'] + extra)
        first = {row[key]: row for row in previous['overall']}
        last = {row[key]: row for row in current['overall']}
        axes[axis] = {
            'counts': {
                'beforePolls': previous['nPolls'], 'afterPolls': current['nPolls'],
                'beforeSeries': previous[nseries_key], 'afterSeries': current[nseries_key],
                'beforeDeltas': previous['nDeltas'], 'afterDeltas': current['nDeltas'],
                'beforePermutations': previous['exactCounting']['nPermutations'],
                'afterPermutations': current['exactCounting']['nPermutations'],
            },
            'results': [{key: item, **{field: {
                'before': first[item][field], 'after': last[item][field],
                'change': last[item][field] - first[item][field],
            } for field in fields}} for item in first],
        }
        if not newly_eligible:
            assert current == previous, 'An excluded publication cannot change strict trend estimates.'
    return {'addedPolls': [after[poll_id] for poll_id in added],
            'revisedExistingPolls': [{'pollId': poll_id, 'before': before[poll_id], 'after': after[poll_id]} for poll_id in revised],
            'newlyEligiblePollIds': newly_eligible, 'axes': axes}


bloc = compare('analysis.json', 'group', [
    'weightedNetDelta', 'slopePerWeek', 'pValue', 'qValue',
    'wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ',
])
party = compare('party-analysis.json', 'partyId', [
    'weightedNetDelta', 'slopePerWeek', 'pValue', 'qValue',
    'wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ',
])
for key in ('addedPolls', 'revisedExistingPolls', 'newlyEligiblePollIds'):
    assert bloc[key] == party[key]
old_bloc, new_bloc = read(BEFORE / 'analysis.json'), read(HERE / 'analysis.json')
assert new_bloc['rawHistoricalWeights'] == old_bloc['rawHistoricalWeights']
assert new_bloc['normalizedHistoricalWeights'] == old_bloc['normalizedHistoricalWeights']
calibration = read(ROOT / 'data/calibration.json')
assert all(value == calibration['pollsterQuality'][key]['weight']
           for key, value in new_bloc['rawHistoricalWeights'].items())
report = {
    'baseline': '2026-10-06', 'updated': '2026-10-07',
    'design': 'Unchanged strict verified-fieldwork rule, party/bloc definitions and historical-quality weights. '
              'Publication dates never replace missing collection intervals; new original filings supplement existing observations without duplication.',
    'addedPolls': bloc['addedPolls'], 'revisedExistingPolls': bloc['revisedExistingPolls'],
    'newlyEligiblePollIds': bloc['newlyEligiblePollIds'],
    'weights': {'beforeRaw': old_bloc['rawHistoricalWeights'], 'afterRaw': new_bloc['rawHistoricalWeights'],
                'beforeNormalized': old_bloc['normalizedHistoricalWeights'],
                'afterNormalized': new_bloc['normalizedHistoricalWeights']},
    'blocs': bloc['axes'], 'parties': party['axes'],
}
out = ROOT / 'artifacts/2026-10-07-comparison'
out.mkdir(exist_ok=True)
(out / 'strict-trends-comparison.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'newlyEligiblePollIds': report['newlyEligiblePollIds'],
                  'counts': report['blocs']['primary']['counts']}))

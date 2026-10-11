"""Compare the October 6 Maagar addition with the frozen October 5 strict audit.

Unknown fieldwork remains excluded: no publication date is substituted for it.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEFORE = HERE / 'archive-2026-10-05'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def compare(filename, key, fields):
    old, new = read(BEFORE / filename), read(HERE / filename)
    assert old['asOf'] == '2026-10-05' and new['asOf'] == '2026-10-06'
    before = {row['pollId']: row for row in old['cohort']}
    after = {row['pollId']: row for row in new['cohort']}
    added = sorted(set(after) - set(before))
    assert added == ['history_maagar_mochot_2026-10-06_current']
    assert set(before) <= set(after)
    revised = [poll_id for poll_id in before if before[poll_id] != after[poll_id]]
    assert sorted(revised) == ['history_kantar_2026-10-04_current', 'history_maagar_mochot_2026-09-29_current']
    for poll_id in revised:
        for identity in ['pollId', 'pollsterId', 'publicationDate']:
            assert before[poll_id][identity] == after[poll_id][identity]
        assert before[poll_id]['fieldworkStart'] is None and before[poll_id]['fieldworkEnd'] is None
        assert after[poll_id]['eligibleStrict'] and after[poll_id]['fieldworkStart'] is not None
    assert after[added[0]]['pollsterId'] == 'maagar_mochot'
    eligible_count = sum(after[poll_id]['eligibleStrict'] for poll_id in added + revised)
    axes = {}
    for axis in ['primary', 'publicationDateSensitivity']:
        previous, current = old[axis], new[axis]
        assert current['nPolls'] == previous['nPolls'] + eligible_count
        nseries_key = 'nPollsters' if key == 'group' else 'nSeries'
        assert current['nDeltas'] == current['nPolls'] - current[nseries_key]
        previous_series = {row['pollsterId']: row for row in previous['byPollster']}
        current_series = {row['pollsterId']: row for row in current['byPollster']}
        assert set(current_series) - set(previous_series) == {'maagar_mochot'}
        for pollster_id in current_series:
            extra = [poll_id for poll_id in added + revised
                     if after[poll_id]['pollsterId'] == pollster_id and after[poll_id]['eligibleStrict']]
            previous_ids = previous_series[pollster_id]['pollIds'] if pollster_id in previous_series else []
            assert set(current_series[pollster_id]['pollIds']) == set(previous_ids + extra)
            assert len(current_series[pollster_id]['pollIds']) >= 2
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
        if not eligible_count:
            assert current == previous, 'A fieldwork-excluded addition must not change strict estimates.'
    return {'addedPolls': [after[poll_id] for poll_id in added],
            'revisedExistingPolls': [{'pollId': poll_id, 'before': before[poll_id], 'after': after[poll_id]} for poll_id in revised],
            'axes': axes}


bloc = compare('analysis.json', 'group', [
    'weightedNetDelta', 'slopePerWeek', 'pValue', 'qValue',
    'wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ',
])
party = compare('party-analysis.json', 'partyId', [
    'weightedNetDelta', 'slopePerWeek', 'pValue', 'qValue',
    'wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ',
])
assert bloc['addedPolls'] == party['addedPolls']
assert bloc['revisedExistingPolls'] == party['revisedExistingPolls']
old_bloc, new_bloc = read(BEFORE / 'analysis.json'), read(HERE / 'analysis.json')
old_raw, new_raw = old_bloc['rawHistoricalWeights'], new_bloc['rawHistoricalWeights']
assert all(new_raw[key] == value for key, value in old_raw.items())
assert set(new_raw) - set(old_raw) == {'maagar_mochot'}
calibration = read(ROOT / 'data/calibration.json')
assert all(value == calibration['pollsterQuality'][key]['weight'] for key, value in new_raw.items())
assert all(abs(value - new_raw[key] / sum(new_raw.values())) < 1e-12
           for key, value in new_bloc['normalizedHistoricalWeights'].items())
report = {
    'baseline': '2026-10-05', 'updated': '2026-10-06',
    'design': 'Same strict fieldwork rule, party/bloc definitions and historical-quality weights; '
              'Maagar October 6 is verified from the original broadcast; official filings newly verify existing Kan October 4 and Maagar September 29 without duplicating them. Historical weights normalize once across eight institutes.',
    'addedPolls': bloc['addedPolls'], 'revisedExistingPolls': bloc['revisedExistingPolls'],
    'weights': {'beforeRaw': old_raw, 'afterRaw': new_raw,
                'beforeNormalized': old_bloc['normalizedHistoricalWeights'],
                'afterNormalized': new_bloc['normalizedHistoricalWeights']},
    'blocs': bloc['axes'], 'parties': party['axes'],
}
out = ROOT / 'artifacts/2026-10-06-comparison'
out.mkdir(exist_ok=True)
(out / 'strict-trends-comparison.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'addedPollIds': [row['pollId'] for row in report['addedPolls']],
                  'counts': report['blocs']['primary']['counts']}))

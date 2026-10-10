"""Compare the October 4 Kan addition with the frozen October 2 strict audit.

Unknown fieldwork remains excluded: no publication date is substituted for it.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEFORE = HERE / 'archive-2026-10-02'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def compare(filename, key, fields):
    old, new = read(BEFORE / filename), read(HERE / filename)
    assert old['asOf'] == '2026-10-02' and new['asOf'] == '2026-10-04'
    assert old['normalizedHistoricalWeights'] == new['normalizedHistoricalWeights']
    before = {row['pollId']: row for row in old['cohort']}
    after = {row['pollId']: row for row in new['cohort']}
    added = sorted(set(after) - set(before))
    assert added == ['history_kantar_2026-10-04_current']
    assert set(before) <= set(after)
    assert all(before[poll_id] == after[poll_id] for poll_id in before)
    assert after[added[0]]['pollsterId'] == 'kantar'
    eligible_count = sum(after[poll_id]['eligibleStrict'] for poll_id in added)
    axes = {}
    for axis in ['primary', 'publicationDateSensitivity']:
        previous, current = old[axis], new[axis]
        assert current['nPolls'] == previous['nPolls'] + eligible_count
        assert current['nDeltas'] == previous['nDeltas'] + eligible_count
        previous_series = {row['pollsterId']: row for row in previous['byPollster']}
        current_series = {row['pollsterId']: row for row in current['byPollster']}
        assert previous_series.keys() == current_series.keys()
        for pollster_id in previous_series:
            extra = [poll_id for poll_id in added
                     if after[poll_id]['pollsterId'] == pollster_id and after[poll_id]['eligibleStrict']]
            assert current_series[pollster_id]['pollIds'] == previous_series[pollster_id]['pollIds'] + extra
        first = {row[key]: row for row in previous['overall']}
        last = {row[key]: row for row in current['overall']}
        axes[axis] = {
            'counts': {
                'beforePolls': previous['nPolls'], 'afterPolls': current['nPolls'],
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
    return {'addedPolls': [after[poll_id] for poll_id in added], 'axes': axes}


bloc = compare('analysis.json', 'group', [
    'weightedNetDelta', 'slopePerWeek', 'pValue', 'qValue',
    'wholeInstituteSignFlipP', 'wholeInstituteSignFlipQ',
])
party = compare('party-analysis.json', 'partyId', [
    'weightedNetDelta', 'slopePerWeek', 'pValue', 'qValue',
    'wholeSeriesSignFlipP', 'wholeSeriesSignFlipQ',
])
assert bloc['addedPolls'] == party['addedPolls']
report = {
    'baseline': '2026-10-02', 'updated': '2026-10-04',
    'design': 'Same strict fieldwork rule, party/bloc definitions and historical-quality weights; '
              'Kan October 4 is included only when original-source fieldwork dates are verified.',
    'addedPolls': bloc['addedPolls'], 'blocs': bloc['axes'], 'parties': party['axes'],
}
out = ROOT / 'artifacts/2026-10-04-comparison'
out.mkdir(exist_ok=True)
(out / 'strict-trends-comparison.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'addedPollIds': [row['pollId'] for row in report['addedPolls']],
                  'counts': report['blocs']['primary']['counts']}))

"""Independent stdlib review of current default density/variance arithmetic.

Does not import application JS, profile builder, or release audit functions.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))

current = read('data/current-polls.json')
calibration = read('data/calibration.json')
profile = read('data/poll-correlation.json')
audit = read('artifacts/poll-correlation-2026-10-09/engine-audit.json')
chosen = next(row for row in audit['on'] if not row['includeChannel14'] and not row['signalNoiseEnabled'])
polls = [row for row in current['polls'] if row['pollsterId'] != 'next_data']
ids = [row['pollsterId'] for row in polls]
positions = {key: i for i, key in enumerate(profile['instituteIds'])}
matrix = [[profile['modeledCorrelationMatrix'][positions[i]][positions[j]] for j in ids] for i in ids]
old_quality = [calibration['pollsterQuality'][key]['weight'] for key in ids]
quality_sum = sum(old_quality)
old_weights = [value / quality_sum for value in old_quality]
density = [sum(row) for row in matrix]
raw = [weight / redundancy for weight, redundancy in zip(old_weights, density)]
weights = [value / sum(raw) for value in raw]
denominators = [max(100, row.get('sampleSize') or 500) / 1.5 for row in polls]
independent_variance = sum(weight * weight / denominator for weight, denominator in zip(weights, denominators))
modeled_variance = independent_variance + sum(
    2 * weights[i] * weights[j] * matrix[i][j] / math.sqrt(denominators[i] * denominators[j])
    for i in range(len(polls)) for j in range(i + 1, len(polls))
)
output_weights = {row['pollsterId']: row['weight'] for row in chosen['weights']}
differences = {key: abs(weight - output_weights[key]) for key, weight in zip(ids, weights)}
assert max(differences.values()) < 1e-12, differences
assert abs(1 / modeled_variance - chosen['nEffective']) < 1e-8
assert modeled_variance >= independent_variance
frozen_calibration = ROOT / 'artifacts/dependence-2022-toggle-2026-10-09/before/data/calibration.json'
old_hash = hashlib.sha256(frozen_calibration.read_bytes()).hexdigest()
new_hash = hashlib.sha256((ROOT / 'data/calibration.json').read_bytes()).hexdigest()
assert old_hash == new_hash
report = {
    'status': 'PASS',
    'implementationImports': False,
    'defaultWeighting': 'unchanged historical calibration, Channel 14 excluded, no recency/manual multiplier',
    'profileId': profile['id'],
    'weightsMaximumAbsoluteDifference': max(differences.values()),
    'nEffectiveIndependentSameWeights': 1 / independent_variance,
    'nEffectiveModeled': 1 / modeled_variance,
    'varianceInflation': modeled_variance / independent_variance,
    'historicalAccuracySha256Unchanged': new_hash,
    'instituteDensity': dict(zip(ids, density)),
    'instituteWeights': dict(zip(ids, weights)),
    'interpretation': 'heuristic forecast similarity; no respondent-overlap, accuracy-improvement or new significance claim',
    'reviewFindings': [
        {
            'id': 'signal_noise_duplicate_precision_before_fit',
            'status': 'resolved',
            'resolution': 'Inflation units deduplicate source IDs and conservatively collapse same institute/day precision and quality before aggregation; original observations remain intact for the filter.',
            'test': 'tests/poll-correlation-signal-noise.test.mjs',
        },
        {
            'id': 'interactive_p_q_with_similarity_enabled',
            'status': 'resolved',
            'resolution': 'Interactive p/q are suppressed with the independence-assumption explanation; the audited historical-accuracy significance table remains separately identified and unchanged.',
            'files': ['dashboard/src/content/dashboard/PollTrendsPage.jsx', 'dashboard/src/content/dashboard/VerifiedPartyTrends.jsx'],
        },
    ],
    'signalNoiseReview': {
        'precisionCorrectionApplied': 'party/week scalar inflation once before fit, without posterior reweighting',
        'manualMultiplierApplied': 'once in selected institute reliability; not reapplied after fitting',
        'sourceObservationsUnchanged': True,
        'limitation': 'Within-week scalar sensitivity approximation, not a full joint measurement covariance or measured respondent overlap.',
    },
    'reviewedImplementationHashes': {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in [
            'dashboard/src/content/dashboard/model/poll-correlation.js',
            'dashboard/src/content/dashboard/model/signal-noise.js',
            'dashboard/src/content/dashboard/PollTrendsPage.jsx',
            'dashboard/src/content/dashboard/VerifiedPartyTrends.jsx',
        ]
    },
}
destination = ROOT / 'artifacts/poll-correlation-2026-10-09/independent-engine-review.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in report.items() if key not in ['instituteDensity', 'instituteWeights']}, ensure_ascii=False, indent=2))

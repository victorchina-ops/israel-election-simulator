"""Read-only historical accuracy/dependence feasibility study.

Reproduces the existing 2022 benchmark independently with an exhaustive
simplex-constrained quadratic optimizer, and adds chronological checks.
Writes only artifacts/accuracy-dependence-2026-10-09; never canonical data.
"""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import platform
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'accuracy-dependence-2026-10-09'
ELECTION_IDS = ['2019-04', '2019-09', '2020', '2021', '2022']
FIRMS = ['midgam', 'kantar', 'panels_lazar', 'maagar_mochot', 'smith', 'fuchs_legacy', 'direct_legacy']
REFERENCES = [
 {'title': 'Bates and Granger (1969), The Combination of Forecasts', 'url': 'https://link.springer.com/article/10.1057/jors.1969.103', 'role': 'Past forecast errors determine combination weights; publisher abstract read on 2026-10-09.'},
 {'title': 'Elliott (2011), Averaging and the Optimal Combination of Forecasts', 'url': 'https://econweb.ucsd.edu/~gelliott/AveragingOptimal.pdf', 'role': 'Author paper: covariance-based combination, estimation error, common error and nonnegative restrictions; pages 1–10 reviewed.'},
 {'title': 'Ledoit and Wolf (2004), A well-conditioned estimator for large-dimensional covariance matrices', 'url': 'https://doi.org/10.1016/S0047-259X(03)00096-4', 'role': 'Primary publisher abstract on covariance shrinkage; the fixed 75% coefficient used here is OUR assumption, not the Ledoit–Wolf estimated coefficient.'},
 {'title': 'statsmodels variance_inflation_factor documentation', 'url': 'https://www.statsmodels.org/stable/generated/statsmodels.stats.outliers_influence.variance_inflation_factor.html', 'role': 'Official documentation: VIF is a linear-regression coefficient variance/multicollinearity diagnostic, not itself a forecast-weight formula.'},
]

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def errors(event):
    return {p['pollsterId']: np.array([p['seats'][party] - event['actualSeats'][party] for party in event['parties']], dtype=float) for p in event['polls']}

def quality(train):
    all_errors = [errors(e) for e in train]
    pooled = float(np.mean([np.mean([np.mean(v * v) for v in event.values()]) for event in all_errors]))
    result = {}
    for firm in FIRMS:
        event_mse = [float(np.mean(event[firm] ** 2)) for event in all_errors if firm in event]
        mse = (sum(event_mse) + 3 * pooled) / (len(event_mse) + 3)
        result[firm] = {'nElections': len(event_mse), 'mseByElection': event_mse, 'shrunkMseSeats': mse, 'relativeWeight': pooled / mse}
    return result, pooled

def risk_matrix(train, ids, q, shrinkage=.75):
    all_errors = [errors(e) for e in train]
    n = len(ids)
    raw = np.zeros((n, n))
    counts = np.zeros((n, n), dtype=int)
    coordinate_counts = np.zeros((n, n), dtype=int)
    for i, first in enumerate(ids):
        for j, second in enumerate(ids):
            matched = [event for event in all_errors if first in event and second in event]
            products = [float(np.mean(event[first] * event[second])) for event in matched]
            raw[i, j] = float(np.mean(products)) if products else 0.0
            counts[i, j] = len(products)
            coordinate_counts[i, j] = sum(len(event[first]) for event in matched)
    observed_diagonal = np.maximum(np.diag(raw), 1e-8)
    # This is uncentered error cosine similarity / normalized second moment,
    # NOT Pearson correlation. Historical biases remain in the risk target.
    similarity = np.clip(raw / np.sqrt(np.outer(observed_diagonal, observed_diagonal)), -.95, .95)
    np.fill_diagonal(similarity, 1)
    shrunk = (1 - shrinkage) * similarity + shrinkage * np.eye(n)
    eigenvalues, eigenvectors = np.linalg.eigh(shrunk)
    shrunk = eigenvectors @ np.diag(np.maximum(eigenvalues, .05)) @ eigenvectors.T
    diagonal = np.array([q[firm]['shrunkMseSeats'] for firm in ids])
    risk = shrunk * np.sqrt(np.outer(diagonal, diagonal))
    return risk, {'ids': ids, 'errorSecondMomentSeatsSquared': raw.tolist(), 'normalizedErrorSecondMoment': similarity.tolist(), 'shrinkageToIdentity': shrinkage, 'pairMatchedElectionCounts': counts.tolist(), 'pairMatchedPartyCoordinateCountsNotIndependent': coordinate_counts.tolist(), 'riskMatrixSeatsSquared': risk.tolist(), 'minimumEigenvalue': float(np.linalg.eigvalsh(risk).min()), 'conditioning': float(np.linalg.cond(risk)), 'target': 'Second moment of forecast errors, retaining bias; not centered Pearson covariance.'}

def simplex_quadratic(risk):
    # With n<=7 we can enumerate all active subsets and solve exactly.
    # This independent solver validates the existing projected-gradient code.
    n = len(risk)
    winner = None
    for count in range(1, n + 1):
        for group in itertools.combinations(range(n), count):
            subset = np.array(group)
            subrisk = risk[np.ix_(subset, subset)]
            direction = np.linalg.solve(subrisk, np.ones(count))
            if direction.sum() <= 0:
                continue
            local = direction / direction.sum()
            if np.min(local) < -1e-10:
                continue
            weights = np.zeros(n)
            weights[subset] = np.maximum(local, 0)
            weights /= weights.sum()
            value = float(weights @ risk @ weights)
            if winner is None or value < winner[0]:
                winner = (value, weights)
    if winner is None:
        raise RuntimeError('No feasible simplex solution')
    assert np.min(winner[1]) >= 0 and abs(winner[1].sum() - 1) < 1e-10
    return winner[1]

def evaluate(event, weights):
    ids = [p['pollsterId'] for p in event['polls']]
    w = np.array([weights.get(firm, 1) for firm in ids], dtype=float)
    w /= w.sum()
    matrix = np.array([[poll['seats'][p] for p in event['parties']] for poll in event['polls']])
    projection = w @ matrix
    delta = projection - np.array([event['actualSeats'][p] for p in event['parties']])
    assert abs(projection.sum() - 120) < 1e-8
    return {'weights': dict(zip(ids, map(float, w))), 'maeSeatsPerParty': float(np.mean(np.abs(delta))), 'rmseSeatsPerParty': float(np.sqrt(np.mean(delta ** 2))), 'partyCount': len(event['parties']), 'expectedSeatProjection': dict(zip(event['parties'], map(float, projection))), 'errors': dict(zip(event['parties'], map(float, delta))), 'sumSeatProjection': float(projection.sum())}

def compare(train, test, shrinkage=.75):
    assert test['id'] not in [e['id'] for e in train], 'Test election leaked into training'
    assert all(e['electionDate'] < test['electionDate'] for e in train), 'Future election leaked into training'
    q, pooled = quality(train)
    ids = [p['pollsterId'] for p in test['polls']]
    risk, diagnostics = risk_matrix(train, ids, q, shrinkage)
    constrained = dict(zip(ids, map(float, simplex_quadratic(risk))))
    quality_weights = {firm: q[firm]['relativeWeight'] for firm in ids}
    return {'trainElectionIds': [e['id'] for e in train], 'testElectionId': test['id'], 'testUsedToFit': False, 'quality': q, 'equal': evaluate(test, {firm: 1 for firm in ids}), 'accuracy': evaluate(test, quality_weights), 'accuracyAndDependence': evaluate(test, constrained), 'dependence': diagnostics, 'pooledTrainingMse': pooled}

def main():
    independent_risk = np.diag([1., 2., 4.])
    independent_expected = np.array([1., .5, .25]) / 1.75
    assert np.max(np.abs(simplex_quadratic(independent_risk) - independent_expected)) < 1e-12
    synthetic_redundancy_risk = np.array([[1., .8, 0.], [.8, 1., 0.], [0., 0., 1.]])
    synthetic_weights = simplex_quadratic(synthetic_redundancy_risk)
    assert synthetic_weights[0] < 1/3 and synthetic_weights[1] < 1/3 and synthetic_weights[2] > 1/3
    assert np.max(np.abs(simplex_quadratic(synthetic_redundancy_risk + 10 * np.ones((3, 3))) - synthetic_weights)) < 1e-12
    inputs = [ROOT / 'data' / 'history' / f'final-polls-{eid}.json' for eid in ELECTION_IDS]
    inputs += [ROOT / 'data' / 'calibration.json', ROOT / 'data' / 'history' / 'manual-source-audit.json', ROOT / 'dashboard' / 'src' / 'content' / 'dashboard' / 'model' / 'weights.js']
    manifest_before = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in inputs}
    elections = [read(path) for path in inputs[:5]]
    for event in elections:
        assert sum(event['actualSeats'].values()) == 120
        for poll in event['polls']:
            assert abs(sum(poll['seats'].values()) - 120) < 1e-8
    base = compare(elections[:4], elections[4])
    archived = read(ROOT / 'data' / 'calibration.json')
    for ours, archived_id in [('equal', 'equal'), ('accuracy', 'accuracy_shrunk'), ('accuracyAndDependence', 'accuracy_dependence')]:
        expected = next(item for item in archived['benchmark'] if item['id'] == archived_id)
        for metric in ['maeSeatsPerParty', 'rmseSeatsPerParty']:
            assert abs(base[ours][metric] - expected[metric]) < 1e-9, (ours, metric)
        assert max(abs(base[ours]['weights'][firm] - value) for firm, value in expected['weights'].items()) < 1e-8
    source_verified = copy.deepcopy(elections[:4])
    for event in source_verified:
        event['polls'] = [p for p in event['polls'] if p['sourceVerification']['status'] in ['full_vector_confirmed', 'conflict_resolved_secondary']]
    sensitivity = compare(source_verified, elections[4])
    rolling = [compare(elections[:i], elections[i]) for i in range(1, len(elections))]
    shrinkage_sensitivity = [compare(elections[:4], elections[4], value) for value in [.75, .90, .95, 1.0]]
    modern = archived['pollsterQuality']
    current_ids = ['midgam_geva', 'kantar', 'maagar_mochot', 'lazar', 'hamadad_consortium', 'tatika', 'direct_polls', 'next_data']
    modern_pairs = []
    for i, first in enumerate(current_ids):
        for second in current_ids[i + 1:]:
            a, b = modern[first], modern[second]
            old_a, old_b = a['historyId'], b['historyId']
            matches = [e['id'] for e in elections if any(p['pollsterId'] == old_a for p in e['polls']) and any(p['pollsterId'] == old_b for p in e['polls'])] if old_a and old_b else []
            modern_pairs.append({'first': first, 'second': second, 'matchedElections': matches, 'nElections': len(matches), 'continuityMultiplier': a['continuityFraction'] * b['continuityFraction'], 'status': 'weak_transferable_historical_information' if matches else 'unknown_not_independent'})
    report = {
      'asOf': '2026-10-09', 'status': 'analysis_only_not_production_weights',
      'question': 'Can historical accuracy and correlated pollster forecast errors be combined?',
      'answer': 'Yes as an optional experimental risk-minimizing method; evidence insufficient for a proven improvement or current full covariance calibration.',
      'historicalDesign': {'trainingElectionCount': 4, 'trainingInstituteElectionObservations': 25, 'heldoutElectionCount': 1, 'heldoutInstituteElectionObservations': 7, 'eligibleFinalPollWindowDays': 8, 'actualSelectedHorizonDays': [3, 6], 'outcomeUnit': 'Published seats by party within each election', 'partyCoordinateObservationsIndependent': False, 'parametersSelectedProspectivelyBefore2022': False, 'designTiming': 'Retrospective replay designed in 2026; parameter calculations exclude each test election.'},
      'reproduced2022Benchmark': base,
      'sourceSensitivity': {'verifiedTrainingInstituteElectionObservations': sum(len(e['polls']) for e in source_verified), 'benchmark': sensitivity},
      'expandingWindowChecks': rolling,
      'fixedShrinkageSensitivityNotTunedTo2022': shrinkage_sensitivity,
      'currentEntityContinuity': modern,
      'currentPairCoverage': modern_pairs,
      'currentPairSummary': {'nCurrentEntities': 8, 'totalPairs': len(modern_pairs), 'pairsWithHistoricalInformation': sum(p['nElections'] > 0 for p in modern_pairs), 'pairsWithoutInformation': sum(p['nElections'] == 0 for p in modern_pairs), 'defaultExcludingNextDataTotalPairs': 21, 'defaultExcludingNextDataPairsWithHistoricalInformation': 6, 'defaultExcludingNextDataPairsWithoutInformation': 15},
      'productionCorrelationMode': {'rule': 'historical_quality × fixed veteranClusterDiscount for every institute except direct_polls and next_data', 'defaultVeteranClusterDiscount': .5, 'estimatedPairwiseErrorDependence': False, 'warning': 'The UI sensitivity rule and the covariance research benchmark are different methods.'},
      'recommendedOptionalMethod': {'nameHe': 'דיוק היסטורי ותלות בשגיאות — ניסיוני', 'target': 'Minimize w transpose M w, with weights >=0 and sum(weights)=1', 'diagonal': 'Election-balanced forecast-error MSE shrunk toward pooled prior with 3 prior elections', 'offDiagonal': 'Matched same-party/same-election final forecast-error cross-products; retain biases; shrink heavily toward diagonal', 'initialShrinkageToIndependenceAssumption': .75, 'sensitivityShrinkages': [.9, .95, 1.0], 'continuity': 'Transfer only documented historical entities; Lazar attenuation .5. Never assign legacy Direct/Panels/Fuchs errors automatically to new institutes.', 'unknownPairs': 'Unknown, not proven independent. Do not market their apparent optimizer advantage as additional information.', 'implementationGate': 'Expand matched verified histories/horizons; preregister transfer and shrinkage; chronological withheld-election tests; probability calibration separately; source coverage exposed; base default remains historical quality.'},
      'whyNotVIF': 'Classical VIF measures regression coefficient instability from collinear predictors. Forecast combination directly optimizes error-risk; applying VIF to raw party seat/share vectors mistakes the common political signal and sum-to-120 composition for redundant errors.',
      'references': REFERENCES,
      'inputHashes': manifest_before,
      'runtime': {'python': platform.python_version(), 'numpy': np.__version__},
      'syntheticMethodChecks': {'independentErrorsRecoverInverseMseWeights': True, 'twoRedundantEqualAccuracyForecastsGetLessIndividualWeight': True, 'sharedErrorFloorDoesNotChangeWeightsAndCannotBeDiversifiedAway': True, 'redundancyExampleWeights': synthetic_weights.tolist()},
      'reproduction': 'python -X utf8 scripts/research-accuracy-dependence-2026-10-09.py',
      'assertions': ['All selected final published seat vectors and actual outcomes sum to 120.', 'Independent active-subset quadratic solver reproduces archived 2022 equal/accuracy/dependence metrics and weights.', 'Each chronological test election is excluded from its weight calculations.', 'No canonical input is modified.', 'Output weights are nonnegative and sum to 1.', 'Diagonal risk recovers inverse-MSE weights.', 'Synthetic correlated duplicate forecasts lose individual weight.', 'A uniform shared-error risk floor leaves weights unchanged and remains in aggregate risk.'],
    }
    assert manifest_before == {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in inputs}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(OUT / 'analysis.json'), '2022': {key: {metric: base[key][metric] for metric in ['maeSeatsPerParty', 'rmseSeatsPerParty']} for key in ['equal', 'accuracy', 'accuracyAndDependence']}, 'rolling': [{'test': r['testElectionId'], **{key: r[key]['rmseSeatsPerParty'] for key in ['equal', 'accuracy', 'accuracyAndDependence']}} for r in rolling], 'currentPairSummary': report['currentPairSummary']}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()

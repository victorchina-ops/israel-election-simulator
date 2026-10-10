"""Reviewed forecast-similarity heuristic from actual post-closure 2026 polls.

No 2022 errors or outcome data enter this feature. Published seat forecasts are
matched by verified fieldwork week, averaged once per institute/week, and
compared by Gaussian distance on party fields explicitly present in every row.
This is a model assumption, not an estimate of polling errors or panel overlap.
"""
from pathlib import Path
import argparse
import collections
import datetime as dt
import hashlib
import itertools
import json
import math
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'data' / 'poll-correlation.json'
BANDWIDTH = 2.
STRENGTH = .25
WEEK_DAYS = 7
EPSILON_EIGENVALUE = 1e-8


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def serialized(value):
    # Preserve the CRLF byte format of the already reviewed Windows evidence.
    # Fixed bytes also make the frozen run reproducible on another platform.
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').replace('\n', '\r\n').encode('utf-8')


def immutable_preflight(path, value):
    if path.exists() and path.read_bytes() != serialized(value):
        raise RuntimeError(f'Frozen artifact differs: {path}. Use a distinct --run-id; existing evidence is never overwritten.')


def write_immutable(path, value):
    immutable_preflight(path, value)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(serialized(value))


def complete_block(ids, matched):
    """Largest supported clique; absent overlap remains unknown, never zero."""
    candidates = []
    for size in range(2, len(ids) + 1):
        for group in itertools.combinations(range(len(ids)), size):
            if all(matched[i][j] > 0 for i, j in itertools.combinations(group, 2)):
                overlap = sum(matched[i][j] for i, j in itertools.combinations(group, 2))
                candidates.append((size, overlap, tuple(ids[i] for i in group), group))
    if not candidates:
        return []
    largest = max(candidates, key=lambda row: (row[0], row[1], tuple(reversed(row[2]))))
    return list(largest[3])


def density(ids, matrix):
    d = np.sum(matrix, axis=1)
    return {'instituteIds': ids, 'density': dict(zip(ids, map(float, d))),
            'weightMultipliersBeforeNormalization': dict(zip(ids, map(float, 1. / d)))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of')
    parser.add_argument('--run-id')
    args = parser.parse_args()
    if args.run_id and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.run_id):
        raise ValueError('--run-id must be a single safe directory name, 1–64 characters.')
    files = [ROOT / p for p in ['data/poll-history.json', 'data/current-polls.json',
                                'data/strict-party-trends.json', 'data/parties.json']]
    before = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in files}
    history, current, strict, party_catalogue = [read(p) for p in files]
    as_of = args.as_of or history['asOf']
    assert as_of == history['asOf'] == strict['asOf'], 'Audit date must match canonical history and strict cohort.'
    as_of_date = dt.date.fromisoformat(as_of)
    closure = dt.date.fromisoformat(strict['coverage']['closureDate'])
    anchor = closure + dt.timedelta(days=1)
    archive = {p['id']: p for p in history['polls']}
    assert len(archive) == len(history['polls']), 'Duplicate history IDs'
    current_rows = current['polls']
    current_ids = sorted({p['pollsterId'] for p in current_rows})
    assert len(current_ids) == len(current_rows), 'Current dataset must have one institute row each.'
    cohort = []
    eligible = []
    for item in strict['cohort']:
        poll = archive[item['pollId']]
        selected = bool(item['eligibleStrict'] and poll['pollsterId'] in current_ids)
        start = item.get('fieldworkStart')
        end = item.get('fieldworkEnd')
        if selected:
            assert start and end and closure < dt.date.fromisoformat(start) <= dt.date.fromisoformat(end) <= as_of_date
            assert item['publicationDate'] <= as_of
            assert sum(poll['seats'].values()) == 120, poll['id']
            assert poll['date'] == item['publicationDate']
            eligible.append((item, poll))
        cohort.append({'pollId': poll['id'], 'pollsterId': poll['pollsterId'],
                       'publicationDate': item['publicationDate'],
                       'fieldworkStart': start, 'fieldworkEnd': end,
                       'eligible': selected, 'eligibilityReason': item['reason'],
                       'sourceUrl': poll.get('sourceUrl'),
                       'fieldworkSourceUrls': item.get('sourceUrls', []),
                       'validationSourceUrl': poll.get('validationSourceUrl')})
    assert len(eligible) == strict['coverage']['pollCount']
    assert eligible
    common = sorted(set.intersection(*(set(p['seats']) for _, p in eligible)))
    all_parties = sorted(set.union(*(set(p['seats']) for _, p in eligible)))
    omitted = sorted(set(all_parties) - set(common))
    assert len(common) >= 2
    grouped = collections.defaultdict(lambda: collections.defaultdict(list))
    for item, poll in eligible:
        week = (dt.date.fromisoformat(item['fieldworkEnd']) - anchor).days // WEEK_DAYS
        assert week >= 0
        grouped[week][poll['pollsterId']].append((item, poll))
    bins = []
    forecasts = {}
    for week in sorted(grouped):
        first = anchor + dt.timedelta(days=WEEK_DAYS * week)
        last = min(first + dt.timedelta(days=WEEK_DAYS - 1), as_of_date)
        vector_by_id = {}
        items = []
        for institute in sorted(grouped[week]):
            rows = grouped[week][institute]
            vector = np.mean([[poll['seats'][p] for p in common] for _, poll in rows], axis=0)
            vector_by_id[institute] = vector
            items.append({'pollsterId': institute, 'pollIds': [p['id'] for _, p in rows],
                          'publishedPollCount': len(rows),
                          'fieldworkDates': [{'start': i['fieldworkStart'], 'end': i['fieldworkEnd']} for i, _ in rows],
                          'sourceUrls': sorted({p['sourceUrl'] for _, p in rows if p.get('sourceUrl')}),
                          'forecastSeats': dict(zip(common, map(float, vector))),
                          'aggregation': 'Average of actual published projections in this institute/week; derived comparison vector, not an additional survey.'})
        forecasts[week] = vector_by_id
        bins.append({'binIndex': week, 'from': first.isoformat(), 'to': last.isoformat(),
                     'instituteCount': len(items), 'publishedPollCount': sum(x['publishedPollCount'] for x in items),
                     'institutes': items})
    raw = [[None] * len(current_ids) for _ in current_ids]
    counts = [[0] * len(current_ids) for _ in current_ids]
    pairs = []
    for i, first in enumerate(current_ids):
        for j, second in enumerate(current_ids):
            overlaps = [week for week, values in forecasts.items() if first in values and second in values]
            counts[i][j] = len(overlaps)
            if not overlaps:
                continue
            similarities = [math.exp(-float(np.mean((forecasts[w][first] - forecasts[w][second]) ** 2)) / (2 * BANDWIDTH ** 2)) for w in overlaps]
            raw[i][j] = float(np.mean(similarities))
            if j > i:
                pairs.append({'first': first, 'second': second, 'matchedBinCount': len(overlaps),
                              'matchedBinIndexes': overlaps,
                              'matchedWindows': [{'from': bins[[b['binIndex'] for b in bins].index(w)]['from'],
                                                  'to': bins[[b['binIndex'] for b in bins].index(w)]['to']} for w in overlaps],
                              'perBinPredictionSimilarities': similarities,
                              'predictionSimilarity': raw[i][j],
                              'status': 'observed_prediction_similarity_not_error_correlation',
                              'independentObservationCount': None})
    for i, first in enumerate(current_ids):
        for j in range(i + 1, len(current_ids)):
            if counts[i][j] == 0:
                pairs.append({'first': first, 'second': current_ids[j], 'matchedBinCount': 0,
                              'matchedBinIndexes': [], 'matchedWindows': [],
                              'perBinPredictionSimilarities': [], 'predictionSimilarity': None,
                              'status': 'unknown_no_comparable_window', 'independentObservationCount': None})
    block = complete_block(current_ids, counts)
    included_ids = [current_ids[i] for i in block]
    excluded_ids = [i for i in current_ids if i not in included_ids]
    kernel = np.array([[raw[i][j] for j in block] for i in block], dtype=float)
    if len(block) >= 2:
        raw_min = float(np.min(np.linalg.eigvalsh(kernel)))
        initial = (1 - STRENGTH) * np.eye(len(block)) + STRENGTH * kernel
        initial_min = float(np.min(np.linalg.eigvalsh(initial)))
        additional = max(0., (EPSILON_EIGENVALUE - initial_min) / (1 - initial_min)) if initial_min < EPSILON_EIGENVALUE else 0.
        modeled = (1 - additional) * initial + additional * np.eye(len(block))
        final_min = float(np.min(np.linalg.eigvalsh(modeled)))
        assert final_min >= EPSILON_EIGENVALUE - 1e-10
    else:
        raw_min = initial_min = final_min = None
        additional = 0.
        modeled = np.zeros((0, 0))
    assert all(raw[i][i] in (1., None) for i in range(len(current_ids)))
    without14_indexes = [i for i, key in enumerate(included_ids) if key != 'next_data']
    no14_ids = [included_ids[i] for i in without14_indexes]
    no14_matrix = modeled[np.ix_(without14_indexes, without14_indexes)]
    missing_named = [name for key, name in [('winter', 'Winter'), ('hendel', 'Hendel')] if key in omitted]
    missing_limitation = (f'The common {len(common)}-party comparison currently omits parties with missing fields'
                          + (', including ' + ' and '.join(missing_named) if missing_named else '')
                          + '; no missing seat or support share is converted to zero.')
    profile = {
        'schemaVersion': 1, 'id': 'post-closure-prediction-similarity-v1',
        'asOf': as_of, 'status': 'experimental_forecast_similarity_heuristic_not_estimated_error_correlation',
        'productionUse': 'forecast_similarity_density_discount_and_modeled_shared_uncertainty',
        'instituteIds': included_ids, 'allInstituteIds': current_ids,
        'predictionSimilarityMatrix': kernel.tolist(),
        'allInstitutePredictionSimilarityMatrixWithMissing': raw,
        'modeledCorrelationMatrix': modeled.tolist(),
        'matchedBinCounts': [[counts[i][j] for j in block] for i in block],
        'allInstituteMatchedBinCounts': counts,
        'similarityStrength': STRENGTH,
        'bandwidthSeats': BANDWIDTH,
        'additionalIdentityShrinkage': additional,
        'effectiveSimilarityStrength': STRENGTH * (1 - additional),
        'matrixAudit': {'rawKernelMinimumEigenvalue': raw_min,
                        'initialModeledMinimumEigenvalue': initial_min,
                        'finalModeledMinimumEigenvalue': final_min,
                        'psdRepair': 'Additional minimal convex shrinkage toward identity, if needed; no entries invented from missing pairs.',
                        'positiveDefinite': final_min is not None and final_min > 0},
        'coverage': {'closureDate': closure.isoformat(),
                     'from': min(i['fieldworkStart'] for i, _ in eligible),
                     'to': max(i['fieldworkEnd'] for i, _ in eligible),
                     'publishedPollCount': len(eligible), 'instituteCount': len(current_ids),
                     'modeledInstituteCount': len(included_ids), 'calendarBinCount': len(bins),
                     'calendarBinsAreIndependentObservations': False,
                     'partyCount': len(common), 'partyIds': common,
                     'omittedPartyIdsWithMissingPublishedFields': omitted,
                     'knownPairs': sum(p['matchedBinCount'] > 0 for p in pairs),
                     'unknownPairs': sum(p['matchedBinCount'] == 0 for p in pairs),
                     'totalPairs': len(current_ids) * (len(current_ids) - 1) // 2,
                     'minimumMatchedBinCount': min((p['matchedBinCount'] for p in pairs if p['matchedBinCount'] > 0), default=0),
                     'maximumMatchedBinCount': max((p['matchedBinCount'] for p in pairs), default=0),
                     'excludedUnverifiedFieldworkPollCount': sum(not row['eligible'] for row in cohort),
                     'excludedInstitutesWithoutCompleteComparableBlock': excluded_ids},
        'pairProfiles': sorted(pairs, key=lambda p: (p['first'], p['second'])),
        'weeklyComparisonVectors': bins,
        'cohort': cohort,
        'densityReferences': {'allModeledInstitutes': density(included_ids, modeled),
                              'withoutChannel14': density(no14_ids, no14_matrix),
                              'scope': 'Illustrative active-subset row sums; recompute when the user excludes institutes, including source-compatibility exclusions in signal/noise.'},
        'method': {'inputs': 'Actual published 2026 party seat projections only; no election outcome, 2022 calibration, forecast errors, compiled model forecasts or respondent microdata.',
                   'selectedBaseAccuracyUnchanged': True,
                   'matching': 'Seven-day fieldwork-end bins anchored the day after verified list closure; only records whose full fieldwork starts after closure are eligible.',
                   'withinBinAggregation': 'One comparison vector per institute/bin; equal average of its distinct published polls. It is not a new poll and is never added to the forecast ensemble.',
                   'missingParties': 'Use the intersection of explicitly present party seat fields across eligible polls; omitted fields stay missing and are not treated as zero.',
                   'kernelFormula': 'Average over shared bins of exp(-mean_party((forecast_i - forecast_j)^2)/(2 * bandwidthSeats^2)).',
                   'whyNotPearsonAcrossParties': 'Direct seat differences compare the same party; no large-party/small-party ranking can produce a spurious high Pearson correlation merely because both forecasts rank party sizes similarly.',
                   'modeledMatrixFormula': 'Initially R=(1-similarityStrength)I+similarityStrength*K; additional minimal identity shrinkage guarantees PSD if heterogeneous pair coverage makes the initial matrix non-PSD.',
                   'densityCorrection': 'd_i=sum_j R_ij over active comparable institutes; multiply selected base weight by 1/d_i once, then normalize within the comparable group while preserving its mass relative to unsupported institutes.',
                   'unknownPairs': 'Raw unknown similarities remain null. Only a largest complete comparable-institute block is eligible; unsupported institutes keep their proposed group mass. No zero-correlation assumption or automatic missing-data bonus.',
                   'completeBlockSelection': 'Maximum cardinality supported clique; maximize matched-pair-window count to break ties, then deterministic institute-ID ordering.',
                   'uncertaintyUse': 'R is an explicit forecast-similarity model assumption for shared simulation uncertainty, not an empirically estimated polling-error or respondent-overlap correlation. No proven effective sample count or probability calibration is inferred.',
                   'parameterSelection': 'Bandwidth 2 seats and strength .25 are fixed conservative heuristic assumptions, not estimates fitted to an election outcome.'},
        'sources': {'historySourceUrl': history['sourceUrl'],
                    'originalPollUrls': sorted({p['sourceUrl'] for _, p in eligible if p.get('sourceUrl')}),
                    'fieldworkVerificationUrls': sorted({url for i, _ in eligible for url in i.get('sourceUrls', [])}),
                    'rawInputHashes': before},
        'limitations': [
            'Similar published forecasts may reflect true public opinion, common political developments or rounding; they do not establish shared polling error, overlapping respondents or coordination.',
            'This is not a Pearson significance test, an estimate of historical accuracy, or a validated VIF correction.',
            'Some pairs share only one comparable calendar bin. Bins and repeated institute surveys are not independent experiments.',
            missing_limitation,
            'Weekly averages are derived comparison summaries and fieldwork dates inside a shared week can differ; no interpolation or survey reconstruction is used.',
            'The mapping from forecast similarity to shared uncertainty is heuristic. Model crossing/majority probabilities are conditional outputs, not validated probabilities.',
            'Discounting similar forecasts can increase the relative weight of an outlying source; that is not proof that the outlier is more accurate.',
        ],
        'reproduction': f'python -X utf8 scripts/build-poll-correlation.py --as-of {as_of}',
    }
    assert before == {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in files}
    out = ROOT / 'artifacts' / 'poll-correlation' / as_of / (args.run_id or 'reviewed')
    assert out.resolve().is_relative_to((ROOT / 'artifacts' / 'poll-correlation').resolve())
    if (out / 'profile.json').exists():
        old = read(out / 'profile.json')
        if old != profile:
            raise RuntimeError('Dated evidence already exists with changed content; choose a distinct --run-id.')
    receipt = {'status': 'passed', 'profileSha256': hashlib.sha256(serialized(profile)).hexdigest(),
               'inputHashesUnchanged': True, 'inputHashes': before,
               'election2022Used': False, 'forecastErrorsUsed': False,
               'missingPartyFieldsImputed': False, 'syntheticPollsAdded': False,
               'matrixAudit': profile['matrixAudit'], 'coverage': profile['coverage']}
    # Preflight every frozen output before writing or promoting the mutable profile.
    # Complete identical runs are reused without changing their evidence files.
    immutable_preflight(out / 'profile.json', profile)
    immutable_preflight(out / 'validation.json', receipt)
    if (out / 'independent-audit.json').exists():
        old_audit = read(out / 'independent-audit.json')
        if old_audit.get('profileSha256') != receipt['profileSha256']:
            raise RuntimeError('Dated independent audit belongs to another profile; use a distinct --run-id.')
    write_immutable(out / 'profile.json', profile)
    write_immutable(out / 'validation.json', receipt)
    if not PROFILE.exists() or PROFILE.read_bytes() != serialized(profile):
        PROFILE.parent.mkdir(parents=True, exist_ok=True)
        PROFILE.write_bytes(serialized(profile))
    print(json.dumps({'profile': str(PROFILE.relative_to(ROOT)), 'sha256': sha(PROFILE),
                      'artifactDirectory': str(out.relative_to(ROOT)),
                      'coverage': profile['coverage'], 'matrixAudit': profile['matrixAudit'],
                      'defaultDensity': profile['densityReferences']['withoutChannel14']}, ensure_ascii=False))


if __name__ == '__main__':
    main()

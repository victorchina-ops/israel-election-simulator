"""Independent stdlib source/arithmetic/PSD audit of forecast similarity.

Reads original published seat rows, rebuilds same-week forecast vectors and
Gaussian similarities, and uses a Jacobi eigensolver independent of numpy.
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

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, tolerance=1e-11):
    assert abs(a - b) <= tolerance, (a, b)


def eigenvalues(matrix):
    a = [row[:] for row in matrix]
    n = len(a)
    if n < 2:
        return [a[0][0]] if n else []
    for _ in range(10000):
        p, q = max(itertools.combinations(range(n), 2), key=lambda pair: abs(a[pair[0]][pair[1]]))
        off = a[p][q]
        if abs(off) < 1e-13:
            return sorted(a[i][i] for i in range(n))
        tau = (a[q][q] - a[p][p]) / (2 * off)
        tangent = (1 if tau >= 0 else -1) / (abs(tau) + math.sqrt(1 + tau * tau))
        cosine = 1 / math.sqrt(1 + tangent * tangent)
        sine = tangent * cosine
        app, aqq = a[p][p], a[q][q]
        a[p][p] = app - tangent * off
        a[q][q] = aqq + tangent * off
        a[p][q] = a[q][p] = 0.
        for k in range(n):
            if k in (p, q):
                continue
            x, y = a[k][p], a[k][q]
            a[k][p] = a[p][k] = cosine * x - sine * y
            a[k][q] = a[q][k] = sine * x + cosine * y
    raise RuntimeError('Jacobi eigenvalue solver did not converge')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of')
    parser.add_argument('--run-id')
    args = parser.parse_args()
    if args.run_id and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', args.run_id):
        raise ValueError('--run-id must be a single safe directory name, 1–64 characters.')
    profile = read(ROOT / 'data' / 'poll-correlation.json')
    if args.as_of and args.as_of != profile['asOf']:
        raise ValueError('--as-of must match the reviewed profile date.')
    inputs = profile['sources']['rawInputHashes']
    assert all(sha(ROOT / file) == value for file, value in inputs.items())
    history = read(ROOT / 'data' / 'poll-history.json')
    strict = read(ROOT / 'data' / 'strict-party-trends.json')
    rows = {p['id']: p for p in history['polls']}
    eligible = [p for p in strict['cohort'] if p['eligibleStrict']]
    assert len(eligible) == profile['coverage']['publishedPollCount']
    closure = dt.date.fromisoformat(profile['coverage']['closureDate'])
    anchor = closure + dt.timedelta(days=1)
    parties = sorted(set.intersection(*(set(rows[i['pollId']]['seats']) for i in eligible)))
    assert parties == profile['coverage']['partyIds']
    assert profile['method']['selectedBaseAccuracyUnchanged'] is True
    assert len(parties) == profile['coverage']['partyCount']
    grouped = collections.defaultdict(lambda: collections.defaultdict(list))
    for item in eligible:
        start, end = dt.date.fromisoformat(item['fieldworkStart']), dt.date.fromisoformat(item['fieldworkEnd'])
        assert start > closure and end >= start
        poll = rows[item['pollId']]
        assert sum(poll['seats'].values()) == 120
        week = (end - anchor).days // 7
        grouped[week][poll['pollsterId']].append(poll)
    vectors = {week: {institute: [sum(p['seats'][party] for p in polls) / len(polls) for party in parties]
                      for institute, polls in institutes.items()}
               for week, institutes in grouped.items()}
    for saved in profile['weeklyComparisonVectors']:
        week = saved['binIndex']
        assert saved['from'] == (anchor + dt.timedelta(days=7 * week)).isoformat()
        for row in saved['institutes']:
            for party, value in zip(parties, vectors[week][row['pollsterId']]):
                close(value, row['forecastSeats'][party])
            assert len(row['pollIds']) == row['publishedPollCount']
    ids = profile['instituteIds']
    kernel = []
    counts = []
    for i, first in enumerate(ids):
        krow, crow = [], []
        for j, second in enumerate(ids):
            weeks = [w for w, values in vectors.items() if first in values and second in values]
            assert weeks
            values = [math.exp(-sum((a - b) ** 2 for a, b in zip(vectors[w][first], vectors[w][second]))
                               / len(parties) / (2 * profile['bandwidthSeats'] ** 2)) for w in weeks]
            similarity = sum(values) / len(values)
            close(similarity, profile['predictionSimilarityMatrix'][i][j])
            assert len(weeks) == profile['matchedBinCounts'][i][j]
            krow.append(similarity)
            crow.append(len(weeks))
        kernel.append(krow)
        counts.append(crow)
    initial = [[(1 - profile['similarityStrength'] if i == j else 0.) + profile['similarityStrength'] * kernel[i][j]
                for j in range(len(ids))] for i in range(len(ids))]
    minimum = min(eigenvalues(initial))
    expected_additional = max(0., (1e-8 - minimum) / (1 - minimum)) if minimum < 1e-8 else 0.
    close(expected_additional, profile['additionalIdentityShrinkage'], 1e-9)
    modeled = [[(1 - expected_additional) * initial[i][j] + (expected_additional if i == j else 0.)
                for j in range(len(ids))] for i in range(len(ids))]
    for i in range(len(ids)):
        for j in range(len(ids)):
            close(modeled[i][j], profile['modeledCorrelationMatrix'][i][j])
            close(modeled[i][j], modeled[j][i])
        close(modeled[i][i], 1.)
    eigen = eigenvalues(modeled)
    assert min(eigen) >= 1e-8 - 1e-9
    close(min(eigenvalues(kernel)), profile['matrixAudit']['rawKernelMinimumEigenvalue'], 1e-9)
    close(min(eigen), profile['matrixAudit']['finalModeledMinimumEigenvalue'], 1e-9)
    for name, reference in profile['densityReferences'].items():
        if not isinstance(reference, dict):
            continue
        subset = [ids.index(key) for key in reference['instituteIds']]
        for index in subset:
            d = sum(modeled[index][j] for j in subset)
            close(d, reference['density'][ids[index]])
            close(1 / d, reference['weightMultipliersBeforeNormalization'][ids[index]])
    assert profile['coverage']['unknownPairs'] == sum(p['matchedBinCount'] == 0 for p in profile['pairProfiles'])
    assert len(profile['pairProfiles']) == profile['coverage']['totalPairs']
    for pair in profile['pairProfiles']:
        if not pair['matchedBinCount']:
            assert pair['predictionSimilarity'] is None
    receipt = {'status': 'passed', 'profileSha256': sha(ROOT / 'data' / 'poll-correlation.json'),
               'independentImplementation': 'Python stdlib loops and Jacobi eigenvalue solver; builder/numpy not imported.',
               'inputHashesUnchanged': True, 'actualPublishedVectorsReconstructed': True,
               'weeklyAggregationAgrees': True, 'gaussianKernelAgrees': True,
               'matchedCountsAgree': True, 'modeledMatrixAgrees': True,
               'densityReferencesAgree': True, 'minimumModeledEigenvalue': min(eigen),
               'no2022OrElectionResultsUsed': True, 'noForecastErrorsUsed': True,
               'noMissingPartyImputation': True, 'syntheticPollsAdded': False,
               'statisticalErrorCorrelationClaim': False, 'probabilityCalibrationClaim': False}
    directory = ROOT / 'artifacts' / 'poll-correlation' / profile['asOf'] / (args.run_id or 'reviewed')
    assert directory.resolve().is_relative_to((ROOT / 'artifacts' / 'poll-correlation').resolve())
    # Receipts for a same-date profile revision are kept beside its matching frozen profile.
    if not (directory / 'profile.json').exists() or read(directory / 'profile.json') != profile:
        if args.run_id:
            raise ValueError('--run-id must select the exact frozen profile produced by the builder.')
        candidates = [p.parent for p in directory.parent.glob('*/profile.json') if read(p) == profile]
        assert len(candidates) == 1, 'Cannot locate the matching reviewed profile revision.'
        directory = candidates[0]
    target = directory / 'independent-audit.json'
    # Keep the original reviewed receipt byte format, including CRLF.
    content = (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').replace('\n', '\r\n').encode('utf-8')
    if target.exists() and target.read_bytes() != content:
        raise RuntimeError('Frozen independent audit differs; create a distinct reviewed --run-id with the builder and audit that run. Existing evidence is never overwritten.')
    if not target.exists():
        target.write_bytes(content)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()

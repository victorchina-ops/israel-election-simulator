"""Differential/analytic regression tests for the independent exact tail sweep.

Small cases compare the frozen pre-update dense verifier and a Python-integer
Cartesian reference. Large cases have closed-form binomial tails. These tests
do not read or modify operational poll data or run canonical trend analyses.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/poll-checks/2026-10-13/independent-sweep-tests.json"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


NEW = module("independent_sweep_current", ROOT / "artifacts/strict-post-close/independent-compressed-counts.py")
OLD = module("independent_dense_frozen", ROOT / "artifacts/poll-checks/2026-10-13/before/artifacts/strict-post-close/independent-compressed-counts.py")
PRIMARY = module("primary_exact_current", ROOT / "artifacts/strict-post-close/compressed_searchsorted_exact.py")
CASES = []


def dense_python(blocks, observed):
    total = math.prod(sum(int(value) for value in series[0][1]) for series in blocks)
    counts = []
    for column, statistic in enumerate(observed):
        cutoff = abs(float(statistic)) - 1e-12
        count = 0
        for indices in itertools.product(*(range(len(series[column][0])) for series in blocks)):
            value = sum(float(series[column][0][index]) for series, index in zip(blocks, indices))
            if abs(value) >= cutoff:
                mass = math.prod(int(series[column][1][index]) for series, index in zip(blocks, indices))
                count += mass
        counts.append(count)
    return counts, total


def test(name, blocks, observed, compare_frozen=True, analytic=None):
    counts, total, sizes = NEW.direct_tail_counts(blocks, observed)
    actual = [int(value) for value in counts]
    reference, reference_total = dense_python(blocks, observed)
    assert total == reference_total and actual == reference, (name, actual, reference)
    if compare_frozen:
        old_counts, old_total, _ = OLD.direct_tail_counts(blocks, observed)
        assert old_total == total and [int(value) for value in old_counts] == actual, name
    if analytic is not None:
        assert actual == analytic, (name, actual, analytic)
    primary_blocks = [
        [PRIMARY.ScalarBlock(values, masses, sum(int(value) for value in masses))
         for values, masses in series]
        for series in blocks
    ]
    primary = PRIMARY.exact_counts(primary_blocks, observed)
    assert int(primary["nPermutationsExact"]) == total
    assert [int(value) for value in primary["extremeCountsExact"]] == actual, (name, "primary differential")
    CASES.append({"name": name, "status": "PASS", "frozenDenseCompared": compare_frozen,
                  "pythonIntegerDenseCompared": True, "primaryCompared": True,
                  "analyticCompared": analytic is not None,
                  "totalExact": str(total), "countsExact": [str(value) for value in actual],
                  "halfSizes": sizes})


def block(values, masses):
    return (np.asarray(values, dtype=float), np.asarray(masses, dtype=np.int64))


def main():
    # Ties and duplicates, inclusive negative/positive boundaries, zero and
    # cutoff<=0 (where the two nominal tails overlap and count only once).
    tied = [[block([-1, -1, 0, 1, 1], [2, 3, 4, 5, 6])],
            [block([-1, 0, 1], [2, 1, 3])]]
    for value in [0.0, 5e-13, 1e-12, 1.0, -1.0, 2.0]:
        test(f"ties-and-cutoff-{value}", tied, [value])
    cutoff = 1.0 - 1e-12
    boundary_values = [np.nextafter(-cutoff, -math.inf), -cutoff,
                       np.nextafter(-cutoff, math.inf),
                       np.nextafter(cutoff, -math.inf), cutoff,
                       np.nextafter(cutoff, math.inf)]
    for index, value in enumerate(boundary_values):
        test(f"nextafter-inclusive-boundary-{index}",
             [[block([0], [2])], [block([value], [3])]], [1.0])
    rng = np.random.default_rng(20261013)
    for index in range(30):
        blocks = []
        for _ in range(int(rng.integers(2, 6))):
            n_values = int(rng.integers(1, 5))
            masses = rng.integers(1, 6, size=n_values)
            blocks.append([block(rng.integers(-5, 6, size=n_values) / 4, masses)
                           for _ in range(3)])
        test(f"random-small-multivariate-{index}", blocks,
             rng.integers(-8, 9, size=3) / 4)
    # Source score calculation and count equivalence on both registered time
    # axes, including half-day fieldwork midpoints and constant outcomes.
    seats = np.asarray([[20, 8, 0], [21, 7, 0], [19, 9, 0]], dtype=np.int64)
    orders = np.asarray(list(itertools.permutations(range(3))))
    for name, times in [("fieldwork-half-days", [0, .5, 2]),
                        ("publication-days", [0, 1, 3])]:
        series = [NEW.score_blocks(times, seats, orders, weight) for weight in [.2, .3, .5]]
        for new, old in zip(series, [OLD.score_blocks(times, seats, orders, weight) for weight in [.2, .3, .5]]):
            for (values, masses), (old_values, old_masses) in zip(new, old):
                assert np.array_equal(values, old_values) and np.array_equal(masses, old_masses)
        test(f"unchanged-score-axis-{name}", series, [.7, -.7, 0])
    # Balanced binary nulls have known binomial counts; deliberately exercise
    # complete-mass and half-mass overflow without allocating a large product.
    for name, n_series, mass, cutoff_count in [
        ("full-universe-above-int64", 8, 10**3, 4),
        ("cartesian-half-above-int64", 6, 10**9, 4),
        ("single-series-mass-above-int64", 2, 5*10**18, 2),
    ]:
        blocks = [[block([-1, 1], [mass, mass])] for _ in range(n_series)]
        ways = sum(math.comb(n_series, k) for k in range(n_series+1)
                   if abs(2*k-n_series) >= cutoff_count)
        test(name, blocks, [float(cutoff_count)], compare_frozen=False,
             analytic=[ways*mass**n_series])
        test(name+"-zero-tail", blocks, [0.0], compare_frozen=False,
             analytic=[(2*mass)**n_series])
    report = {"status": "PASS", "asOf": "2026-10-13", "tests": len(CASES),
              "scope": "Independent sweep against frozen original dense counter, explicit Python-int dense reference, primary counter and closed-form large tails; no canonical analyses run.",
              "cases": CASES}
    body = (json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode()
    if OUT.exists():
        assert OUT.read_bytes() == body, "Preserve changed dated test evidence; use a distinct reviewed revision."
    else:
        OUT.write_bytes(body)
    print(json.dumps({"status": report["status"], "tests": report["tests"]}))


if __name__ == "__main__":
    main()

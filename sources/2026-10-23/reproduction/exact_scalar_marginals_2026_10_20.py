"""Exact outcome-marginal time-permutation distributions without n! tensors.

Primary construction streams unique permutations of repeated scalar outcomes and
restores the exact labeled multiplicity product(factorial(frequency)). Independent
construction uses a remaining-count dynamic program whose transitions multiply
by the number of remaining labeled choices. Both retain the registered integer
half-day centered score and feed the unchanged reviewed tail counters.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
import hashlib
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "artifacts/strict-post-close"
sys.dont_write_bytecode = True
sys.path.insert(0, str(FROZEN))
from compressed_searchsorted_exact import ScalarBlock

FROZEN_COUNTER_HASHES = {
    "compressed_searchsorted_exact.py": "22918f50bec91553d715600f1949f45a8140779eaf81b956fdcf623f98b6c1a1",
    "independent-compressed-counts.py": "8a725d5bfca3a0f40a8f6e72f038e76877ec88e0d444b8fbf07686da3f1b924d",
}


def verify_frozen_counters():
    for name, expected in FROZEN_COUNTER_HASHES.items():
        assert hashlib.sha256((FROZEN/name).read_bytes()).hexdigest() == expected, name


def integer_times(times):
    doubled = np.asarray(times, dtype=float) * 2
    if not np.array_equal(doubled, np.rint(doubled)):
        raise ValueError("Time coordinates must be exact integer half-days")
    return tuple(int(x) for x in doubled)


def integer_outcomes(values):
    array = np.asarray(values)
    if array.ndim != 1 or not np.all(np.isfinite(array)) or not np.all(array == np.rint(array)):
        raise ValueError("Scalar outcomes must be finite integers")
    return tuple(sorted(int(x) for x in array))


def checked_histogram(histogram, n):
    raw = math.factorial(n)
    assert histogram and all(type(k) is int and type(v) is int and v > 0 for k,v in histogram.items())
    assert sum(histogram.values()) == raw, "Lost labeled permutation mass"
    assert sum(score*mass for score,mass in histogram.items()) == 0, "Null score mean is not exactly zero"
    return tuple(sorted(histogram.items())), raw


@lru_cache(maxsize=256)
def unique_distribution(u, scalar):
    """Stream distinct value assignments; never store their permutation rows."""
    n = len(u)
    assert n == len(scalar) and n >= 2
    centered = tuple(n*x-sum(u) for x in u)
    denominator = sum(c*x for c,x in zip(centered,u))
    if denominator <= 0:
        raise ValueError("A series needs distinct time coordinates")
    frequencies = Counter(scalar)
    labels = tuple(sorted(frequencies))
    remaining = [frequencies[x] for x in labels]
    labeled_factor = math.prod(math.factorial(count) for count in remaining)
    histogram = Counter()
    suffix = [sum(centered[i:]) for i in range(n+1)]

    def visit(position, score):
        present = [i for i,count in enumerate(remaining) if count]
        if len(present) == 1:
            histogram[score + suffix[position]*labels[present[0]]] += labeled_factor
            return
        for i in present:
            remaining[i] -= 1
            visit(position+1, score+centered[position]*labels[i])
            remaining[i] += 1

    visit(0,0)
    items, raw = checked_histogram(histogram,n)
    return items, raw, denominator


@lru_cache(maxsize=256)
def dp_distribution(u, scalar):
    """Independent labeled-choice DP; no unique-permutation multiplicity factor."""
    n = len(u)
    assert n == len(scalar) and n >= 2
    # Pairwise differences independently form the same centered coefficients.
    coefficients = tuple(sum(x-y for y in u) for x in u)
    denominator = sum((u[i]-u[j])**2 for i in range(n) for j in range(i))
    if denominator <= 0:
        raise ValueError("A series needs distinct time coordinates")
    frequencies = Counter(scalar)
    labels = tuple(sorted(frequencies))
    initial = tuple(frequencies[x] for x in labels)
    suffix = [sum(coefficients[i:]) for i in range(n+1)]

    @lru_cache(maxsize=None)
    def solve(remaining):
        count_left = sum(remaining)
        if not count_left:
            return ((0,1),)
        position = n-count_left
        present = [i for i,count in enumerate(remaining) if count]
        if len(present) == 1:
            return ((suffix[position]*labels[present[0]], math.factorial(count_left)),)
        result = Counter()
        for i in present:
            available = remaining[i]
            child = list(remaining)
            child[i] -= 1
            offset = coefficients[position]*labels[i]
            for score,mass in solve(tuple(child)):
                result[score+offset] += available*mass
        return tuple(result.items())

    items, raw = checked_histogram(dict(solve(initial)),n)
    solve.cache_clear()
    return items, raw, denominator


def score_blocks(times, seats, weight=1.0, *, method="unique"):
    u = integer_times(times)
    y = np.asarray(seats)
    if y.ndim == 1:
        y = y[:,None]
    if y.ndim != 2 or y.shape[0] != len(u):
        raise ValueError("Seat rows and time coordinates differ")
    builder = {"unique":unique_distribution,"dp":dp_distribution}[method]
    result = []
    for column in y.T:
        items, raw, denominator = builder(u,integer_outcomes(column))
        integers = np.asarray([pair[0] for pair in items],dtype=np.int64)
        dtype = object if raw > np.iinfo(np.int64).max else np.int64
        masses = np.asarray([pair[1] for pair in items],dtype=dtype)
        assert sum(int(x) for x in masses) == raw
        scale = 14.0*float(weight)/denominator
        result.append(ScalarBlock(integers.astype(float)*scale,masses,raw))
    return result


def independent_blocks(times, seats, weight=1.0):
    return [(b.values,b.multiplicities) for b in score_blocks(times,seats,weight,method="dp")]


def individual_pvalues(blocks, observed, tolerance=1e-12):
    """Exact Python-integer tail masses with the existing inclusive tolerance."""
    result = []
    for block,statistic in zip(blocks,observed):
        if isinstance(block,ScalarBlock):
            values,masses,raw = block.values,block.multiplicities,block.raw_permutations
        else:
            values,masses = block
            raw = sum(int(x) for x in masses)
        extreme = sum(int(mass) for value,mass in zip(values,masses)
                      if abs(float(value)) >= abs(float(statistic))-tolerance)
        assert type(extreme) is int and type(raw) is int and 0 <= extreme <= raw
        result.append(extreme/raw)
    return np.asarray(result,dtype=float)


verify_frozen_counters()

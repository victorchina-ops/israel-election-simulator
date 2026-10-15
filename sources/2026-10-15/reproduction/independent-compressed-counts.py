"""Independent exact tail counts with integer-score null multiplicities.

The main analyzers use searchsorted on sorted scalar half-distributions.
This verifier counts scalar tails with an independent monotone two-pointer sweep.
It evaluates inclusive sums directly, without searchsorted or Cartesian tail masks.
Within-series midpoint dates are half-days, so repeated null scores can be
identified as exact integers without rounding or changing permutation weights.
"""
import math
import numpy as np


def score_blocks(times, seats, orders, weight):
    doubled = np.asarray(times) * 2
    assert np.array_equal(doubled, np.rint(doubled))
    u = doubled.astype(np.int64)
    centered = len(u) * u - u.sum()
    denominator = int(centered @ u)
    assert denominator > 0
    scores = np.einsum('i,pij->pj', centered, np.asarray(seats, dtype=np.int64)[orders])
    scale = 14 * weight / denominator
    blocks = []
    for column in scores.T:
        values, multiplicities = np.unique(column, return_counts=True)
        assert multiplicities.sum() == math.factorial(len(u))
        assert np.dot(values, multiplicities) == 0
        blocks.append((values * scale, multiplicities.astype(np.int64)))
    return blocks


def sums_with_multiplicities(blocks):
    values, counts = np.zeros(1), np.ones(1, dtype=np.int64)
    mass = 1
    for add, multiplicities in blocks:
        mass *= sum(int(value) for value in multiplicities)
        dtype = object if mass > np.iinfo(np.int64).max else np.int64
        values = (values[:, None] + add[None, :]).reshape(-1)
        counts = (counts.astype(dtype)[:, None] * multiplicities.astype(dtype)[None, :]).reshape(-1)
    return values, counts


def direct_tail_counts(blocks_by_series, observed, tolerance=1e-12):
    """Exact inclusive scalar tails with O(A+B) sorted-half pointer sweeps.

    Each half still preserves the independently computed integer-score
    multiplicities. Direct sum comparisons mirror the original dense mask;
    Python integer masses/products avoid signed64 overflow. No searchsorted
    calls or full Cartesian tail products are used.
    """
    total = math.prod(sum(int(value) for value in series[0][1])
                      for series in blocks_by_series)
    results, sizes = [], []
    for j, threshold in enumerate(abs(np.asarray(observed))):
        cutoff = float(threshold) - tolerance
        if cutoff <= 0:
            results.append(total)
            sizes.append([1, 1])
            continue
        left, right, nl, nr = [], [], 1, 1
        for block in sorted((series[j] for series in blocks_by_series), key=lambda b: len(b[0]), reverse=True):
            if nl <= nr:
                left.append(block); nl *= len(block[0])
            else:
                right.append(block); nr *= len(block[0])
        a, ac = sums_with_multiplicities(left)
        b, bc = sums_with_multiplicities(right)
        total_a = sum(int(value) for value in ac)
        total_b = sum(int(value) for value in bc)
        assert total_a * total_b == total
        ai, bi = np.argsort(a, kind='stable'), np.argsort(b, kind='stable')
        a, ac, b, bc = a[ai], ac[ai], b[bi], bc[bi]
        # Increasing a makes both b boundaries move only left. The upper
        # tail gains mass; the lower tail loses mass. Inclusive direct sum
        # comparisons preserve ties at +/- (abs(observed)-tolerance).
        high_index = low_index = len(b)
        high_mass, low_mass = 0, total_b
        count = 0
        for a_value, a_mass in zip(a, ac):
            a_value = float(a_value)
            while high_index > 0 and a_value + float(b[high_index - 1]) >= cutoff:
                high_index -= 1
                high_mass += int(bc[high_index])
            while low_index > 0 and a_value + float(b[low_index - 1]) > -cutoff:
                low_index -= 1
                low_mass -= int(bc[low_index])
            assert 0 <= high_mass + low_mass <= total_b
            count += int(a_mass) * (high_mass + low_mass)
        assert 0 <= count <= total
        results.append(count)
        sizes.append([len(a), len(b)])
    return np.asarray(results, dtype=object if total > np.iinfo(np.int64).max else np.int64), total, sizes

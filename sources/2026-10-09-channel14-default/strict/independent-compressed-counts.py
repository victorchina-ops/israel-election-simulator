"""Independent exact tail counts with integer-score null multiplicities.

The main analyzers use searchsorted on complete multivariate half-distributions.
This verifier enumerates each scalar Cartesian tail directly in bounded chunks.
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
    for add, multiplicities in blocks:
        values = (values[:, None] + add[None, :]).reshape(-1)
        counts = (counts[:, None] * multiplicities[None, :]).reshape(-1)
    return values, counts


def direct_tail_counts(blocks_by_series, observed, tolerance=1e-12):
    total = math.prod(int(series[0][1].sum()) for series in blocks_by_series)
    results, sizes = [], []
    for j, threshold in enumerate(abs(np.asarray(observed))):
        if threshold < tolerance:
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
        assert int(ac.sum()) * int(bc.sum()) == total
        # Mask + product are bounded to about 32 MiB; no full null product.
        chunk = max(1, (32 * 1024 * 1024) // (len(a) * 17))
        count = 0
        for start in range(0, len(b), chunk):
            part, pc = b[start:start + chunk], bc[start:start + chunk]
            mask = np.abs(part[:, None] + a[None, :]) >= threshold - tolerance
            count += int(np.sum(mask * (pc[:, None] * ac[None, :]), dtype=np.int64))
        assert 0 <= count <= total
        results.append(count)
        sizes.append([len(a), len(b)])
    return np.asarray(results, dtype=np.int64), total, sizes

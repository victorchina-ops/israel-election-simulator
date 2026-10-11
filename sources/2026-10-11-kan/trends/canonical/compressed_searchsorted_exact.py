"""Memory-safe exact stratified permutation tail counts.

This is a candidate primary counter, deliberately separate from the existing
independent verifier.  It preserves the existing null and statistic but works
one outcome at a time:

1. enumerate every within-series time permutation;
2. collapse identical integer slope numerators with exact multiplicities;
3. form two balanced Cartesian half-distributions;
4. count both inclusive tails with sorted values and cumulative multiplicities.

No Monte Carlo sampling or probability rounding is used.  Midpoint dates are
integer half-days, so within-series score identities are exact integers before
the historical-quality weight is applied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class ScalarBlock:
    values: np.ndarray
    multiplicities: np.ndarray
    raw_permutations: int


def integer_score_blocks(times: Sequence[float], seats: np.ndarray,
                         orders: np.ndarray, weight: float) -> list[ScalarBlock]:
    """Return one exact-multiplicity scalar null block per outcome column."""
    doubled = np.asarray(times, dtype=float) * 2
    if not np.array_equal(doubled, np.rint(doubled)):
        raise ValueError("Time coordinates must be integer half-days")
    u = doubled.astype(np.int64)
    centered = len(u) * u - int(u.sum())
    denominator = int(centered @ u)
    if denominator <= 0:
        raise ValueError("A series needs at least two distinct time points")

    y = np.asarray(seats, dtype=np.int64)
    permutations = np.asarray(orders, dtype=np.int64)
    if y.shape[0] != len(u):
        raise ValueError("Seat rows and time coordinates differ")
    raw = math.factorial(len(u))
    if len(permutations) != raw:
        raise ValueError("Orders do not enumerate every within-series permutation")

    integer_scores = np.einsum('i,pij->pj', centered, y[permutations])
    scale = 14.0 * float(weight) / denominator
    blocks: list[ScalarBlock] = []
    for column in integer_scores.T:
        integers, multiplicities = np.unique(column, return_counts=True)
        multiplicities = multiplicities.astype(np.int64)
        if int(multiplicities.sum()) != raw:
            raise AssertionError("Lost permutation multiplicity")
        if int(integers @ multiplicities) != 0:
            raise AssertionError("Permutation-score null is not centered")
        blocks.append(ScalarBlock(integers.astype(float) * scale, multiplicities, raw))
    return blocks


def _cartesian_sums(blocks: Iterable[ScalarBlock]) -> tuple[np.ndarray, np.ndarray]:
    values = np.zeros(1, dtype=float)
    multiplicities = np.ones(1, dtype=np.int64)
    for block in blocks:
        values = (values[:, None] + block.values[None, :]).reshape(-1)
        multiplicities = (
            multiplicities[:, None] * block.multiplicities[None, :]
        ).reshape(-1)
    return values, multiplicities


def compressed_searchsorted_tail(blocks: Sequence[ScalarBlock], observed: float,
                                 tolerance: float = 1e-12) -> dict:
    """Count |T_perm| >= |T_obs|-tolerance with exact multiplicities."""
    if tolerance != 1e-12:
        raise ValueError("Publication counter requires the registered 1e-12 tolerance")
    total = math.prod(block.raw_permutations for block in blocks)
    threshold = abs(float(observed))
    cutoff = threshold - tolerance
    if cutoff <= 0:
        return {
            'extremeCount': total,
            'totalPermutations': total,
            'halfSizes': [1, 1],
            'uniqueStatesBySeries': [len(block.values) for block in blocks],
            'tolerance': tolerance,
        }

    left: list[ScalarBlock] = []
    right: list[ScalarBlock] = []
    nl = nr = 1
    for block in sorted(blocks, key=lambda item: len(item.values), reverse=True):
        if nl <= nr:
            left.append(block)
            nl *= len(block.values)
        else:
            right.append(block)
            nr *= len(block.values)

    a, ac = _cartesian_sums(left)
    b, bc = _cartesian_sums(right)
    if int(ac.sum()) * int(bc.sum()) != total:
        raise AssertionError("Compressed halves do not preserve permutation mass")

    order = np.argsort(b, kind='stable')
    b = b[order]
    bc = bc[order]
    prefix = np.empty(len(b) + 1, dtype=np.int64)
    prefix[0] = 0
    np.cumsum(bc, dtype=np.int64, out=prefix[1:])
    total_b = int(prefix[-1])

    high_index = np.searchsorted(b, cutoff - a, side='left')
    low_index = np.searchsorted(b, -cutoff - a, side='right')
    tails = (total_b - prefix[high_index]) + prefix[low_index]
    count = int(np.sum(ac * tails, dtype=np.int64))
    if not 0 <= count <= total:
        raise AssertionError("Tail count is outside the permutation universe")

    return {
        'extremeCount': count,
        'totalPermutations': total,
        'halfSizes': [len(a), len(b)],
        'uniqueStatesBySeries': [len(block.values) for block in blocks],
        'tolerance': tolerance,
    }


def exact_counts(blocks_by_series: Sequence[Sequence[ScalarBlock]],
                 observed: Sequence[float], tolerance: float = 1e-12) -> dict:
    """Count every outcome independently and return inspectable complexity."""
    n_outcomes = len(observed)
    if any(len(series) != n_outcomes for series in blocks_by_series):
        raise ValueError("Every series must have one block per outcome")
    outcomes = [
        compressed_searchsorted_tail(
            [series[index] for series in blocks_by_series], value, tolerance
        )
        for index, value in enumerate(observed)
    ]
    totals = {result['totalPermutations'] for result in outcomes}
    if len(totals) != 1:
        raise AssertionError("Outcomes disagree on permutation universe")
    total = totals.pop()
    return {
        'nPermutations': total,
        'nPermutationsExact': str(total),
        'extremeCounts': [result['extremeCount'] for result in outcomes],
        'extremeCountsExact': [str(result['extremeCount']) for result in outcomes],
        'pValues': [result['extremeCount'] / total for result in outcomes],
        'halfSizes': [result['halfSizes'] for result in outcomes],
        'uniqueStatesBySeries': [result['uniqueStatesBySeries'] for result in outcomes],
        'tolerance': tolerance,
    }

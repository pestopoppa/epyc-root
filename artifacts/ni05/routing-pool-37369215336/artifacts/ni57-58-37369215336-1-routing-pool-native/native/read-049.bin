"""Pure Pareto objective math shared by runtime and dashboard code."""

from __future__ import annotations

import random
import statistics
from itertools import combinations
from typing import Iterable, Sequence

from src.autopilot_core.tier_specs import DEFAULT_REFERENCE_POINT


def dominates(a: Sequence[float], b: Sequence[float]) -> bool:
    """True if ``a`` Pareto-dominates ``b`` for max-objectives.

    Raises on a dimensionality mismatch. ``zip`` truncates to the shorter sequence, so
    comparing objective tuples built under DIFFERENT policies used to return a
    confident, meaningless answer: a 3D ``(quality, qph, reliability)`` point against a
    4D ``(quality, t/s, -cost, reliability)`` one lines qph (hundreds) up against t/s
    (~50) and reliability against -cost. Mixed-policy comparison is always a bug —
    surface it here rather than letting it decide keep/revert.
    """
    if len(a) != len(b):
        raise ValueError(
            f"objective dimensionality mismatch: {len(a)} vs {len(b)} — refusing to "
            "compare tuples built under different objective policies"
        )
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def median_objectives(points: Iterable[Sequence[float]]) -> tuple[float, ...]:
    """Axis-wise median objective tuple for a reproduction cluster.

    Raises on a dimensionality mismatch within the cluster. ``zip(*rows)`` truncates
    to the shortest row, so a cluster accidentally mixing tuples built under different
    objective policies would silently drop trailing axes (e.g. reliability) from the
    median instead of surfacing the mix — the same hazard `dominates()` guards against.
    """
    rows = [tuple(float(value) for value in point) for point in points]
    if not rows:
        return ()
    dims = {len(row) for row in rows}
    if len(dims) > 1:
        raise ValueError(
            f"objective dimensionality mismatch within reproduction cluster: "
            f"lengths {sorted(dims)} — refusing to compute a median across tuples "
            "built under different objective policies"
        )
    return tuple(statistics.median(axis) for axis in zip(*rows))


def hypervolume(
    points: Iterable[Sequence[float]],
    ref: Sequence[float] = DEFAULT_REFERENCE_POINT,
    *,
    exact_limit: int = 100,
    samples: int = 10000,
) -> float:
    """Max-objective hypervolume.

    Uses exact inclusion-exclusion for small frontiers and deterministic Monte
    Carlo for large frontiers, matching the runtime archive policy.

    Raises on a dimensionality mismatch between any point and ``ref`` — the same
    guard ``dominates()`` applies, for the same reason (see its docstring). Without
    it, the ``all(pi > ri for pi, ri in zip(...))`` filter below truncates a
    shorter/longer point against ``ref`` and either silently drops trailing axes
    (a confident, meaningless hypervolume) or lets a later ``point[dim]`` indexing
    step raise an opaque ``IndexError`` with no indication of what went wrong.
    """
    point_list = [tuple(float(x) for x in point) for point in points]
    ref_tuple = tuple(float(x) for x in ref)
    if not point_list:
        return 0.0

    dims = len(ref_tuple)
    for point in point_list:
        if len(point) != dims:
            raise ValueError(
                f"objective dimensionality mismatch: point has {len(point)} dims, "
                f"reference point has {dims} — refusing to compute a hypervolume "
                "across tuples built under different objective policies"
            )

    valid = [
        point for point in point_list
        if all(pi > ri for pi, ri in zip(point, ref_tuple))
    ]
    if not valid:
        return 0.0

    if len(point_list) > exact_limit:
        return hypervolume_monte_carlo(valid, ref_tuple, samples=samples)

    total = 0.0
    for size in range(1, len(valid) + 1):
        sign = (-1) ** (size + 1)
        for subset in combinations(valid, size):
            box_min = tuple(min(point[dim] for point in subset) for dim in range(dims))
            volume = 1.0
            for dim in range(dims):
                volume *= max(0.0, box_min[dim] - ref_tuple[dim])
            total += sign * volume
    return total


def hypervolume_monte_carlo(
    points: Sequence[Sequence[float]],
    ref: Sequence[float],
    *,
    samples: int = 10000,
) -> float:
    """Deterministic Monte Carlo hypervolume approximation.

    Raises on a dimensionality mismatch (see `hypervolume`) — without this,
    ``point[dim]`` for ``dim in range(len(ref))`` either raises an opaque
    ``IndexError`` (a point shorter than ``ref``) or silently ignores a point's
    trailing axes (a point longer than ``ref``), the same defect class this module
    already guards against in `dominates()`/`hypervolume()`.
    """
    if not points:
        return 0.0
    dims = len(ref)
    for point in points:
        if len(point) != dims:
            raise ValueError(
                f"objective dimensionality mismatch: point has {len(point)} dims, "
                f"reference point has {dims} — refusing to compute a hypervolume "
                "across tuples built under different objective policies"
            )
    ref_tuple = tuple(float(x) for x in ref)
    upper = tuple(max(float(point[dim]) for point in points) for dim in range(dims))
    box_volume = 1.0
    for dim in range(dims):
        box_volume *= upper[dim] - ref_tuple[dim]
    if box_volume <= 0.0:
        return 0.0

    hits = 0
    rng = random.Random(42)
    for _ in range(samples):
        sample = tuple(rng.uniform(ref_tuple[dim], upper[dim]) for dim in range(dims))
        if any(all(point[dim] >= sample[dim] for dim in range(dims)) for point in points):
            hits += 1
    return box_volume * hits / samples

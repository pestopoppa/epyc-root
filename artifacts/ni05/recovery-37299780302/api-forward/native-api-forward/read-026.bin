"""Synthetic `ContentionMatrix` + gate factory for ContentionGate unit tests.

WHY THIS EXISTS (2026-08-03)
---------------------------
`tests/unit/test_scheduling_contention_gate.py` and
`tests/unit/test_gate_seam_wiring.py` used to load the COMMITTED
`orchestration/contention_matrix.yaml`. That file is a MEASUREMENT ARTIFACT:
`scripts/server/contention_matrix.py` regenerates it from whichever role lineup
is live at bench time, so its role NAMES, its RATIOS, and even its top-level
SECTIONS move under the tests without anyone editing a test.

The 2026-08-01 re-bench (W1 GPU cutover, topology `171f86f9188211e9`) did all
three at once:

  * `frontdoor+architect_general` 0.66 block -> 1.43 allow (architect moved to
    the MI210), so every test that used `architect_general` as "the blocker"
    silently lost its blocker;
  * `vision_escalation` disappeared from the matrix (the role now aliases onto
    `worker_vision`), so `frontdoor+vision_escalation` became an UNKNOWN pair —
    i.e. the test's designated *allow* pair became a *queue*;
  * the regenerated file carries no `n_way`, `nway_light_roles` or `same_role`
    sections at all, so `nway_policy` takes its unmeasured fail-closed branch
    and QUEUEs every background co-run regardless of the pair ratio.

That last one is why several gate tests that still *passed* were passing for
the wrong reason: their QUEUE came from the n-way fail-closed branch, not from
the pair ratio named in their docstring.

The gate's job is to turn ratios and verdicts into admission decisions. That is
what these tests prove, so the ratios are DECLARED here rather than measured.

This does NOT replace the currency check on the shipped artifact. Whether the
committed matrix still describes the live stack is asserted by the
`test_real_matrix_*` tests in `tests/unit/test_scheduling_contention.py` and
`tests/unit/test_admit_set.py`, which deliberately read the real file.
"""

from __future__ import annotations

import time

from src.scheduling.contention import (
    ContentionMatrix,
    MatrixStatus,
    Nway,
    Pair,
    SameRole,
)

# Every role the gate fixtures name. Declaring them all "light" makes the
# defensive N-way layer NEUTRAL for unmeasured sets (`nway_policy` allows an
# all-light set), so each pair-layer test isolates the pair layer it is about.
# `synthetic_unmeasured` is included on purpose: the unknown-PAIR test must
# observe the unknown-pair policy, not the unmeasured-N-WAY policy.
FIXTURE_LIGHT_ROLES = frozenset(
    {
        "architect_general",
        "frontdoor",
        "ingest_long_context",
        "synthetic_unmeasured",
        "vision_escalation",
        "worker_borderline",
        "worker_general",
        "worker_summarize",
    }
)

# (role_a, role_b) -> (ratio, verdict). Floor is 0.85.
FIXTURE_PAIRS: dict[tuple[str, str], tuple[float, str]] = {
    # Catastrophic: below floor in BOTH traffic classes.
    ("frontdoor", "ingest_long_context"): (0.37, "block"),
    ("architect_general", "frontdoor"): (0.50, "block"),
    # Concurrency-positive: allow in BOTH traffic classes.
    ("frontdoor", "vision_escalation"): (1.20, "allow"),
    ("frontdoor", "worker_general"): (1.82, "allow"),
    ("frontdoor", "worker_summarize"): (1.30, "allow"),
    ("architect_general", "vision_escalation"): (1.10, "allow"),
    # Borderline: >= floor but < 1.0 — allow foreground, queue background.
    ("frontdoor", "worker_borderline"): (0.90, "borderline"),
}

# Measured N-way entries. The {frontdoor, worker_summarize} set is measured
# AGGREGATE-NEGATIVE while its pair is 1.30 allow — that is the only way to
# exercise the gate's defensive N-way layer (pairwise-allow does not certify
# the set), which no other gate test covers.
FIXTURE_NWAY: dict[tuple[str, ...], tuple[float, str]] = {
    ("frontdoor", "worker_summarize"): (0.72, "block"),
}

FIXTURE_SAME_ROLE: dict[str, str] = {
    "frontdoor": "allow",
    "vision_escalation": "allow",
    "worker_general": "allow",
}


def gate_fixture_matrix() -> ContentionMatrix:
    """Build the declared matrix the gate tests reason about.

    Deliberately NOT loaded from disk — see the module docstring.
    """
    pairs = {}
    for roles, (ratio, verdict) in FIXTURE_PAIRS.items():
        key = tuple(sorted(roles))
        pairs[key] = Pair(roles=key, ratio=ratio, verdict=verdict, samples=3)
    n_way = {}
    for roles, (ratio, verdict) in FIXTURE_NWAY.items():
        key = tuple(sorted(roles))
        n_way[key] = Nway(roles=key, ratio=ratio, verdict=verdict, samples=3)
    same_role = {
        role: SameRole(role=role, verdict=verdict) for role, verdict in FIXTURE_SAME_ROLE.items()
    }
    return ContentionMatrix(
        version=1,
        measured_at="2026-08-01T00:00:00+00:00",
        host="fixture",
        topology_hash="fixture-topology",
        default_floor=0.85,
        pairs=pairs,
        same_role=same_role,
        unknown_pairs=[],
        n_way=n_way,
        light_roles=FIXTURE_LIGHT_ROLES,
        heavy_roles=frozenset(),
    )


def pin_matrix_status(gate, status: MatrixStatus = MatrixStatus.OK) -> None:
    """Pin `gate.matrix_health()` instead of letting it read the live host.

    `ContentionGate.matrix_health()` calls `matrix_status()`, which stats the
    ON-DISK `orchestration/contention_matrix.yaml` (mtime age) and compares its
    `topology_hash` against a fingerprint of the LIVE `stack_numa.NUMA_CONFIG` —
    both of which move whenever the operator changes the stack. An injected
    matrix does not change that: `matrix_status()` re-reads the default path
    regardless. Unpinned, every test here would flip to the fail-closed branch
    the moment the lineup changes, reporting a gate bug that isn't one.

    The fail-closed behaviour itself is asserted by
    `test_gate_fails_closed_on_stale_matrix`, which pins STALE through this same
    seam, so pinning here removes duplication, not coverage.
    """
    gate._matrix_status_cache = status
    gate._matrix_status_checked_at = time.time()


def make_gate(gate_mod, holders, matrix=None, status: MatrixStatus = MatrixStatus.OK):
    """A ContentionGate with declared holders, a declared matrix, pinned health."""
    gate = gate_mod.ContentionGate(
        matrix=matrix if matrix is not None else gate_fixture_matrix(),
        active_holders_fn=lambda: {role: list(idxs) for role, idxs in holders.items()},
    )
    pin_matrix_status(gate, status)
    return gate

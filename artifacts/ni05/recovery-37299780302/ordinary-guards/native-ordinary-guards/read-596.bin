"""WP-5 scaffold tests: RolePlacementPolicy enum + get_placement_policy accessor.

The scaffold ships with conservative defaults and a stable accessor API so
WP-3 can call `get_placement_policy(role)` without WP-5 needing to refactor
call sites later.
"""

from __future__ import annotations

import pytest

from src.scheduling.placement_policy import (
    DEFAULT_PLACEMENT_POLICY,
    RolePlacementPolicy,
    get_placement_policy,
)


def test_default_is_solo_prefer_full() -> None:
    assert DEFAULT_PLACEMENT_POLICY is RolePlacementPolicy.SOLO_PREFER_FULL


def test_enum_values_are_kebab_strings() -> None:
    """Values must be string-comparable so NUMA_CONFIG entries can use bare
    strings without an enum import."""
    assert RolePlacementPolicy.SOLO_PREFER_FULL.value == "solo_prefer_full"
    assert RolePlacementPolicy.BURST_PREFER_SPLIT.value == "burst_prefer_split"
    assert RolePlacementPolicy.FULL_DISABLED.value == "full_disabled"
    assert RolePlacementPolicy.QUEUE_ONLY.value == "queue_only"


def test_unknown_role_returns_default() -> None:
    assert get_placement_policy("nonexistent", {}) is DEFAULT_PLACEMENT_POLICY
    assert get_placement_policy("nonexistent", {"other": {"placement_policy": "queue_only"}}) is DEFAULT_PLACEMENT_POLICY


def test_missing_policy_field_returns_default() -> None:
    cfg = {"frontdoor": {"instances": []}}
    assert get_placement_policy("frontdoor", cfg) is DEFAULT_PLACEMENT_POLICY


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("solo_prefer_full", RolePlacementPolicy.SOLO_PREFER_FULL),
        ("burst_prefer_split", RolePlacementPolicy.BURST_PREFER_SPLIT),
        # Compatibility is input-only; runtime output remains shape-agnostic.
        ("burst_prefer_quarters", RolePlacementPolicy.BURST_PREFER_SPLIT),
        ("full_disabled", RolePlacementPolicy.FULL_DISABLED),
        ("queue_only", RolePlacementPolicy.QUEUE_ONLY),
        ("  burst_prefer_split  ", RolePlacementPolicy.BURST_PREFER_SPLIT),  # whitespace
        ("FULL_DISABLED", RolePlacementPolicy.FULL_DISABLED),  # case
    ],
)
def test_valid_string_values_coerce(raw: str, expected: RolePlacementPolicy) -> None:
    cfg = {"frontdoor": {"placement_policy": raw}}
    assert get_placement_policy("frontdoor", cfg) is expected


def test_enum_value_passes_through() -> None:
    cfg = {"r": {"placement_policy": RolePlacementPolicy.QUEUE_ONLY}}
    assert get_placement_policy("r", cfg) is RolePlacementPolicy.QUEUE_ONLY


@pytest.mark.parametrize("absent", ["", None])
def test_absent_value_falls_back_to_default(absent: object) -> None:
    """An ABSENT policy resolves to the conservative default. Only absent."""
    cfg = {"r": {"placement_policy": absent}}
    assert get_placement_policy("r", cfg) is DEFAULT_PLACEMENT_POLICY


@pytest.mark.parametrize(
    "bad, exc",
    [
        ("garbage", ValueError),
        ("solo-prefer-full", ValueError),  # hyphens, not underscores — the near-miss
        (42, TypeError),
        ({}, TypeError),
    ],
)
def test_unrecognised_value_raises_rather_than_silently_degrading(
    bad: object, exc: type[Exception]
) -> None:
    """A value that WAS configured but cannot be mapped must raise.

    Behaviour change 2026-07-30, replacing `test_malformed_value_falls_back_to_default`.
    That test asserted every malformed value resolved to DEFAULT_PLACEMENT_POLICY —
    which is NOT "no policy", it is a DIFFERENT policy (SOLO_PREFER_FULL), and it is
    the one that lets a solo request acquire a full instance's every region lock and
    serialize the machine (the DISPATCH-A shape, 2026-07-21). So the old behaviour
    silently substituted the most dangerous policy for the one the author asked for,
    with no log line, and the test froze that in place.

    `"solo-prefer-full"` is the case that matters: hyphens where the enum uses
    underscores. It is one keystroke from valid and it degraded silently. This is
    The explicit legacy alias is the only accepted old spelling; any other
    half-finished rename must fail rather than silently changing placement.
    """
    cfg = {"r": {"placement_policy": bad}}
    with pytest.raises(exc):
        get_placement_policy("r", cfg)


def test_live_call_with_no_arg_does_not_crash() -> None:
    """Live wrapper (no numa_config arg) reads production NUMA_CONFIG and must
    be stable for WP-3 consumers regardless of which roles carry a
    `placement_policy` field (frontdoor/worker_general do since WP-7 / the
    2026-07-23 lineup restoration; the original WP-5-era premise that no role
    carries one is long stale). Unknown roles resolve to the default."""
    from src.scheduling.placement_policy import RolePlacementPolicy

    for role in ("frontdoor", "worker_general", "ingest_long_context"):
        assert isinstance(get_placement_policy(role), RolePlacementPolicy)
    assert get_placement_policy("made_up_role") is DEFAULT_PLACEMENT_POLICY

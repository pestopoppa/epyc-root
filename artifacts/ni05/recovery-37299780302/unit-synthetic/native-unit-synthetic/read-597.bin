"""P1-1: the placement_policy vocabulary is shape-agnostic AND fails closed.

Companion to `test_placement_policy.py`, which pins *that* an unrecognised
value raises. It does not pin *what the raise says*, and that gap is real: the
message can be gutted to a bare ``ValueError("bad")`` — losing both the
offending value and the valid set — with all 19 of its tests still passing
(verified 2026-08-12 by mutation before this file was written).

That matters because the point of the 2026-07-31 fail-closed change was not
merely to stop the silent downgrade to SOLO_PREFER_FULL, it was to tell the
operator which config string was wrong and what to write instead. A raise that
says only "bad placement policy" fails closed but not LOUD: it turns a silent
misconfiguration into an opaque crash, and the operator still has to go read
the enum to find out what they were allowed to type.

So this file pins the diagnostic payload of the error, and the compliant path
(canonical + legacy-alias resolution) that must keep working alongside it.
"""

from __future__ import annotations

import logging

import pytest

from src.scheduling.placement_policy import (
    DEFAULT_PLACEMENT_POLICY,
    RolePlacementPolicy,
    get_placement_policy,
)


def _policy_for(raw: object) -> RolePlacementPolicy:
    return get_placement_policy("r", {"r": {"placement_policy": raw}})


# ---------------------------------------------------------------------------
# Direction 1 — the canonical, shape-agnostic vocabulary resolves.
# ---------------------------------------------------------------------------


def test_canonical_name_is_shape_agnostic() -> None:
    """The enum must not name a physical shape the fleet no longer has.

    The 2026-07-30 cutover retired quarter instances in favour of halves, so a
    member called BURST_PREFER_QUARTERS would describe a non-existent thing.
    """
    assert RolePlacementPolicy.BURST_PREFER_SPLIT.value == "burst_prefer_split"
    assert not hasattr(RolePlacementPolicy, "BURST_PREFER_QUARTERS")
    assert "quarter" not in " ".join(p.value for p in RolePlacementPolicy)


def test_canonical_string_resolves() -> None:
    assert _policy_for("burst_prefer_split") is RolePlacementPolicy.BURST_PREFER_SPLIT


# ---------------------------------------------------------------------------
# Direction 2 — the legacy alias still resolves, silently and correctly.
# ---------------------------------------------------------------------------


def test_legacy_alias_resolves_to_the_same_policy() -> None:
    """The compliant path. Every config written before the rename must boot.

    Breaking this would strand existing configs, and — because the failure mode
    is now a raise — would do it as a hard startup crash rather than a downgrade.
    """
    assert _policy_for("burst_prefer_quarters") is RolePlacementPolicy.BURST_PREFER_SPLIT
    assert _policy_for("burst_prefer_quarters") is _policy_for("burst_prefer_split")


@pytest.mark.parametrize("raw", ["BURST_PREFER_QUARTERS", "  burst_prefer_quarters  "])
def test_legacy_alias_is_normalised_like_any_other_value(raw: str) -> None:
    """Case/whitespace normalisation must apply to the alias too — otherwise the
    alias is a second-class spelling that fails on inputs the canonical name
    accepts."""
    assert _policy_for(raw) is RolePlacementPolicy.BURST_PREFER_SPLIT


def test_legacy_alias_does_not_leak_into_the_output_vocabulary() -> None:
    """Compatibility is input-only: nothing rendered or logged may say "quarters"."""
    resolved = _policy_for("burst_prefer_quarters")
    assert resolved.value == "burst_prefer_split"
    assert "quarter" not in resolved.value


# ---------------------------------------------------------------------------
# Direction 3 — an unknown value raises instead of silently degrading.
# ---------------------------------------------------------------------------


def test_unknown_string_raises_rather_than_returning_the_default() -> None:
    with pytest.raises(ValueError):
        _policy_for("burst_prefer_eighths")


def test_near_miss_typo_does_not_resolve_to_the_default() -> None:
    """The failure this whole guard exists for.

    `solo-prefer-full` is one keystroke from valid. Under the old fail-open
    behaviour it returned None and the caller substituted
    DEFAULT_PLACEMENT_POLICY — which *is* SOLO_PREFER_FULL, so the typo appeared
    to work while being unenforced. Assert the raise, not just inequality:
    "happens to equal the default" is exactly the ambiguity that hid the bug.
    """
    with pytest.raises(ValueError):
        _policy_for("solo-prefer-full")


# ---------------------------------------------------------------------------
# Direction 4 — the raise is LOUD: it names the bad value AND the valid set.
# This is the property the existing suite does not pin.
# ---------------------------------------------------------------------------


def test_raise_message_names_the_offending_value() -> None:
    with pytest.raises(ValueError) as ei:
        _policy_for("burst_prefer_eighths")
    assert "burst_prefer_eighths" in str(ei.value), (
        "the error must name the value that was rejected, or the operator "
        f"cannot find it in their config; got: {ei.value}"
    )


def test_raise_message_lists_every_valid_policy() -> None:
    """Naming the bad value is half the diagnosis; the operator also needs to be
    told what they were allowed to write."""
    with pytest.raises(ValueError) as ei:
        _policy_for("burst_prefer_eighths")
    message = str(ei.value)
    missing = [p.value for p in RolePlacementPolicy if p.value not in message]
    assert not missing, f"valid policies absent from the error message: {missing}"


def test_wrong_type_raises_typeerror_naming_the_type() -> None:
    with pytest.raises(TypeError) as ei:
        _policy_for(42)
    assert "int" in str(ei.value)


# ---------------------------------------------------------------------------
# The absent/configured distinction — fail-closed must not swallow the
# legitimate "nothing was configured" case.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("absent", [None, "", "   "])
def test_absent_value_still_resolves_to_the_default(absent: object) -> None:
    """Absent is not misconfigured. Only a value that was WRITTEN and cannot be
    mapped may raise; blank/None must stay on the conservative default or every
    role without an explicit policy becomes a startup crash."""
    assert _policy_for(absent) is DEFAULT_PLACEMENT_POLICY


def test_missing_role_and_missing_key_resolve_to_the_default() -> None:
    assert get_placement_policy("absent_role", {}) is DEFAULT_PLACEMENT_POLICY
    assert get_placement_policy("r", {"r": {}}) is DEFAULT_PLACEMENT_POLICY


# ---------------------------------------------------------------------------
# Fleet-wide fail-open: a broken live config must be reported, not silent.
# ---------------------------------------------------------------------------


def test_unavailable_live_config_is_reported_not_silent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """If the live NUMA_CONFIG import breaks, EVERY role silently resolves to
    DEFAULT_PLACEMENT_POLICY — the same fail-open degradation `_coerce` refuses,
    applied fleet-wide. Not fatal (absent config is legitimate off-server), but
    it must leave a report.
    """
    import sys

    import src.scheduling.placement_policy as mod

    monkeypatch.setattr(mod, "_live_config_warned", False, raising=False)
    # A None entry in sys.modules makes `import <name>` raise ImportError.
    monkeypatch.setitem(sys.modules, "scripts.server.stack_numa", None)

    with caplog.at_level(logging.WARNING, logger=mod.__name__):
        resolved = get_placement_policy("frontdoor")

    assert resolved is DEFAULT_PLACEMENT_POLICY
    assert caplog.records, "a fleet-wide degradation to the default was not reported"
    assert "NUMA_CONFIG" in caplog.text

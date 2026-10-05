"""Eval fan-out NUMA-mode resolution must handle every mode and be LOUD on none.

Regression cover for the fail-open shape at ``_live_safe_concurrency``:

    if str(stack_numa_mode or "").strip().lower() == "quarter":
        return compute_max_disjoint_live_concurrency(...)
    # ...else silently fall through to the conservative bound

An equality test against ONE mode absorbed ``full``, ``both``, unset and typos
into the same else-branch, so a returned cap of 1 could not be distinguished
from a cap of 1 that means "I could not determine the fleet mode". The repair
keeps the conservative value (WP-14 fail-closed) and removes the silence.

Mode vocabulary is ``scripts/server/stack_numa_mode.VALID_STACK_NUMA_MODES``
= {full, quarter, both}. ``half`` is a cpu_shape_class, NOT a mode.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import eval_tower  # noqa: E402


# The live half fleet shape: one full instance + two half siblings.
HALF_FLEET_CFG = {
    "worker_general": {
        "instances": [
            ("0-95", 8072, 96),
            ("0-47,96-143", 8082, 48),
            ("48-95,144-191", 8182, 48),
        ],
        "full_instance_idx": 0,
    },
}


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def _install_fleet(monkeypatch, live_ports: set[int], cfg: dict = HALF_FLEET_CFG) -> None:
    """Wire NUMA_CONFIG + a synthetic /health probe with no real sockets."""
    from scripts.server import stack_numa

    def fake_get(url: str, timeout: float) -> _Response:
        del timeout
        port = int(url.rsplit(":", 1)[1].split("/", 1)[0])
        return _Response(200 if port in live_ports else 503)

    monkeypatch.setenv("AUTOPILOT_EVAL_REQUIRE_LIVE_FLEET", "1")
    monkeypatch.setattr(stack_numa, "NUMA_CONFIG", cfg)
    monkeypatch.setattr(eval_tower.httpx, "get", fake_get)
    # Neutralize the runtime-facts manifest seam; each test drives the mode via
    # ORCHESTRATOR_STACK_NUMA_MODE so the resolution under test is unambiguous.
    monkeypatch.setattr(eval_tower, "_runtime_facts_stack_numa_mode", lambda: None)


# ---------------------------------------------------------------------------
# The pure resolver: every mode is classified, nothing falls through silently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["quarter", "full", "both", " QUARTER ", "Both"])
def test_resolver_recognises_every_valid_mode(raw: str) -> None:
    mode, reason = eval_tower._resolve_stack_numa_mode_for_fanout(raw)
    assert reason == "declared"
    assert mode == raw.strip().lower()
    assert mode in eval_tower._valid_stack_numa_modes()


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_resolver_reports_unset_mode_as_unknown(raw) -> None:
    assert eval_tower._resolve_stack_numa_mode_for_fanout(raw) == (
        eval_tower._EVAL_FANOUT_UNKNOWN_MODE,
        "unset",
    )


@pytest.mark.parametrize("raw", ["half", "halves", "quarters", "nps4", "FULL_ONLY"])
def test_resolver_reports_unrecognised_mode_as_unknown(raw: str) -> None:
    """A cpu_shape_class ('half') or a typo is NOT silently a non-quarter mode."""
    assert eval_tower._resolve_stack_numa_mode_for_fanout(raw) == (
        eval_tower._EVAL_FANOUT_UNKNOWN_MODE,
        "unrecognised",
    )


def test_unknown_sentinel_is_not_a_valid_mode() -> None:
    assert eval_tower._EVAL_FANOUT_UNKNOWN_MODE not in eval_tower._valid_stack_numa_modes()


def test_resolver_vocabulary_matches_the_launcher() -> None:
    """The resolver must not fork the launcher's --numa-mode vocabulary."""
    from scripts.server.stack_numa_mode import VALID_STACK_NUMA_MODES

    assert eval_tower._valid_stack_numa_modes() == frozenset(VALID_STACK_NUMA_MODES)


# ---------------------------------------------------------------------------
# Per-mode concurrency on the live half fleet
# ---------------------------------------------------------------------------


def test_quarter_mode_uses_largest_disjoint_live_subset(monkeypatch) -> None:
    """Full dead, both halves live -> full-first does not bind -> 2, not 1."""
    _install_fleet(monkeypatch, live_ports={8082, 8182})
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")

    assert eval_tower._live_safe_concurrency("worker_general", 1) == 2


def test_full_mode_is_one_live_instance(monkeypatch) -> None:
    _install_fleet(monkeypatch, live_ports={8072})
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")

    assert eval_tower._live_safe_concurrency("worker_general", 3) == 1


def test_both_mode_is_bounded_by_the_full_first_topology_cap(monkeypatch) -> None:
    """Full live alongside the halves: full-first policy binds the cap to 1."""
    _install_fleet(monkeypatch, live_ports={8072, 8082, 8182})
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "both")

    assert eval_tower._live_safe_concurrency("worker_general", 3) == 1


@pytest.mark.parametrize("mode", ["quarter", "full", "both"])
def test_recognised_modes_are_never_loud(monkeypatch, caplog, mode: str) -> None:
    _install_fleet(monkeypatch, live_ports={8082, 8182})
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", mode)

    with caplog.at_level(logging.ERROR, logger="autopilot.eval"):
        eval_tower._live_safe_concurrency("worker_general", 3)

    assert [r for r in caplog.records if "could not determine" in r.getMessage()] == []


# ---------------------------------------------------------------------------
# The fail-open repair: an undetermined mode is LOUD
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_mode", "expected_reason"),
    [(None, "unset"), ("half", "unrecognised"), ("nps4", "unrecognised")],
)
def test_undetermined_mode_is_reported_loudly(
    monkeypatch, caplog, raw_mode, expected_reason: str
) -> None:
    """THE REGRESSION. Halves live, full dead, mode undetermined.

    The cap stays conservative (1), but the process must SAY that the 1 came
    from an unresolved fleet mode and that a disjoint live subset of 2 was
    available. The pre-fix code returned 1 in total silence.
    """
    _install_fleet(monkeypatch, live_ports={8082, 8182})
    if raw_mode is None:
        monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    else:
        monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", raw_mode)

    with caplog.at_level(logging.ERROR, logger="autopilot.eval"):
        cap = eval_tower._live_safe_concurrency("worker_general", 1)

    assert cap == 1
    loud = [
        r
        for r in caplog.records
        if r.levelno >= logging.ERROR and "could not determine the fleet mode" in r.getMessage()
    ]
    assert len(loud) == 1, "an undetermined NUMA mode must emit exactly one ERROR"
    message = loud[0].getMessage()
    assert expected_reason in message
    assert "worker_general" in message
    # The silently-forfeited fan-out must be in the message, not just the cap.
    assert "subset is 2" in message


def test_single_live_instance_does_not_raise_a_spurious_alarm(monkeypatch, caplog) -> None:
    """A one-instance role has cap 1 by construction; no mode can change that,
    so it must not be reported as an undetermined-mode degradation."""
    _install_fleet(
        monkeypatch,
        live_ports={8083},
        cfg={"architect_general": {"instances": [("184-191", 8083, 8)]}},
    )
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)

    with caplog.at_level(logging.ERROR, logger="autopilot.eval"):
        assert eval_tower._live_safe_concurrency("architect_general", 3) == 1

    assert [r for r in caplog.records if "could not determine" in r.getMessage()] == []


def test_dead_fleet_is_serial_and_silent(monkeypatch, caplog) -> None:
    _install_fleet(monkeypatch, live_ports=set())
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)

    with caplog.at_level(logging.ERROR, logger="autopilot.eval"):
        assert eval_tower._live_safe_concurrency("worker_general", 3) == 1

    assert [r for r in caplog.records if "could not determine" in r.getMessage()] == []


# ---------------------------------------------------------------------------
# The extracted full-first walk (pure)
# ---------------------------------------------------------------------------


def test_full_first_walk_returns_one_when_the_full_instance_is_first() -> None:
    regions = [
        frozenset({"q0", "q1", "q2", "q3"}),
        frozenset({"q0", "q1"}),
        frozenset({"q2", "q3"}),
    ]
    assert eval_tower._full_first_live_concurrency(regions, 3) == 1


def test_full_first_walk_accepts_disjoint_siblings() -> None:
    regions = [frozenset({"q0", "q1"}), frozenset({"q2", "q3"})]
    assert eval_tower._full_first_live_concurrency(regions, 3) == 2


def test_full_first_walk_is_bounded_by_the_topology_cap() -> None:
    regions = [frozenset({"q0"}), frozenset({"q1"}), frozenset({"q2"}), frozenset({"q3"})]
    assert eval_tower._full_first_live_concurrency(regions, 2) == 2
    assert eval_tower._full_first_live_concurrency(regions, 1) == 1
    assert eval_tower._full_first_live_concurrency([], 4) == 1

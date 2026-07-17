"""Tests for batch_ledger.py (Ledger v2).

Run with the orchestrator venv python (stdlib-only module, but keep the runner uniform):
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_batch_ledger.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the sibling module importable without packaging.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import batch_ledger as bl  # noqa: E402
from batch_ledger import Ledger, LedgerError  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: a synthetic multi-entry manifest exercising phase/priority/deps.
# ---------------------------------------------------------------------------
def _entry(task_id, phase, priority, depends_on=None, **pre):
    preconditions = {"depends_on": depends_on or []}
    preconditions.update(pre)
    return {
        "task_id": task_id,
        "title": task_id,
        "phase": phase,
        "priority": priority,
        "preconditions": preconditions,
        "provenance": {"owning_handoff": "h.md", "checkbox": "X"},
        "execution": {"driver": "command", "concurrency_mode": "serial_noninference"},
        "outcomes": {"gate_table": [{"gate": "g", "evidence": "e", "fork": {}}]},
        "artifacts": {},
        "ledger": {},
    }


@pytest.fixture
def manifest():
    # A depends on nothing; B depends on A; C depends on A; D depends on B and C.
    # Phase/priority set so the deterministic tie-break is observable.
    return {
        "entries": [
            _entry("D", phase=1, priority="P0", depends_on=["B", "C"]),
            _entry("A", phase=0, priority="P1"),
            _entry("C", phase=1, priority="P1", depends_on=["A"]),
            _entry("B", phase=1, priority="P0", depends_on=["A"]),
        ]
    }


# ---------------------------------------------------------------------------
# append / latest
# ---------------------------------------------------------------------------
def test_append_and_latest_in_memory():
    led = Ledger()  # in-memory
    led.append_row({"task_id": "A", "status": "READY"})
    led.append_row({"task_id": "A", "status": "RUNNING"})
    led.append_row({"task_id": "A", "status": "DONE_PASS"})
    assert led.latest_state("A") == "DONE_PASS"  # latest row wins
    assert led.latest_state("missing") is None
    assert len(led.rows()) == 3  # append-only: all three rows retained


def test_append_fills_v2_defaults():
    led = Ledger()
    row = led.append_row({"task_id": "A", "status": "DONE_PASS"})
    for field in (
        "entry_hash", "attestation_ref", "era_stamp", "gate_results",
        "wall_clock_s", "failure_reason", "operator_batch_ref",
    ):
        assert field in row
    # v1 carry-over fields present too.
    for field in ("run_id", "flags", "needs_approval", "journal_quarantine_rule"):
        assert field in row
    assert row["schema_version"] == bl.SCHEMA_VERSION
    assert row["ts"]


def test_append_rejects_bad_status_and_missing_task_id():
    led = Ledger()
    with pytest.raises(LedgerError):
        led.append_row({"task_id": "A", "status": "NOT_A_STATUS"})
    with pytest.raises(LedgerError):
        led.append_row({"status": "READY"})


def test_persistent_ledger_roundtrip(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = Ledger(path)
    led.append_row({"task_id": "A", "status": "DONE_PASS", "wall_clock_s": 12.5})
    led.append_row({"task_id": "B", "status": "RUNNING"})
    # A fresh handle reads the same file back.
    led2 = Ledger(path)
    assert led2.latest_state("A") == "DONE_PASS"
    assert led2.latest_row("A")["wall_clock_s"] == 12.5
    assert led2.latest_state("B") == "RUNNING"
    assert set(led2.all_latest()) == {"A", "B"}


# ---------------------------------------------------------------------------
# reconcile
# ---------------------------------------------------------------------------
def test_reconcile_defaults_unseen_to_ready(manifest):
    led = Ledger()
    led.append_row({"task_id": "A", "status": "DONE_PASS"})
    states = led.reconcile(manifest)
    assert states == {"A": "DONE_PASS", "B": "READY", "C": "READY", "D": "READY"}


def test_reconcile_reports_orphans(manifest):
    led = Ledger()
    led.append_row({"task_id": "A", "status": "DONE_PASS"})
    led.append_row({"task_id": "ZZZ", "status": "COORDINATION"})  # not in manifest
    assert led.orphans(manifest) == ["ZZZ"]
    assert "ZZZ" not in led.reconcile(manifest)


# ---------------------------------------------------------------------------
# pending (structural eligibility)
# ---------------------------------------------------------------------------
def test_pending_only_deps_free_entries_first(manifest):
    led = Ledger()  # empty ledger
    pend = [e["task_id"] for e in led.pending(manifest)]
    # Only A has no deps; B/C/D all wait on A.
    assert pend == ["A"]


def test_pending_unlocks_after_dep_done(manifest):
    led = Ledger()
    led.append_row({"task_id": "A", "status": "DONE_PASS"})
    pend = [e["task_id"] for e in led.pending(manifest)]
    # B and C both depend only on A (now DONE); ordering: phase 1, both P0/P1 -> B(P0) before C(P1).
    assert pend == ["B", "C"]


def test_pending_excludes_running_and_terminal(manifest):
    led = Ledger()
    led.append_row({"task_id": "A", "status": "RUNNING"})  # not READY -> not pending
    assert led.pending(manifest) == []
    led.append_row({"task_id": "A", "status": "DONE_PASS"})  # now terminal-success
    # A itself is DONE (excluded); B/C unlocked.
    assert [e["task_id"] for e in led.pending(manifest)] == ["B", "C"]


def test_marginal_obs_satisfies_dependency(manifest):
    led = Ledger()
    led.append_row({"task_id": "A", "status": "DONE_MARGINAL_OBS"})
    assert [e["task_id"] for e in led.pending(manifest)] == ["B", "C"]


def test_superseded_does_not_satisfy_dependency(manifest):
    led = Ledger()
    led.append_row({"task_id": "A", "status": "SKIPPED_SUPERSEDED"})
    # A is terminal (excluded from pending) but does NOT satisfy B/C's dependency.
    assert led.pending(manifest) == []


def test_structural_unsatisfiable_missing_dep():
    m = {"entries": [_entry("X", 0, "P0", depends_on=["NOPE"])]}
    led = Ledger()
    # X depends on a task_id that is not in the manifest -> structurally unsatisfiable.
    assert led.pending(m) == []


def test_structural_unsatisfiable_flag_conflict():
    e = _entry("X", 0, "P0")
    e["preconditions"]["flags_required"] = {"F": 1}
    e["preconditions"]["flags_forbidden"] = ["F"]
    led = Ledger()
    assert led.pending({"entries": [e]}) == []


# ---------------------------------------------------------------------------
# canonical_hash
# ---------------------------------------------------------------------------
def test_canonical_hash_stable_and_order_independent():
    a = {"task_id": "A", "phase": 1, "x": [1, 2]}
    b = {"x": [1, 2], "phase": 1, "task_id": "A"}  # key order differs
    assert bl.canonical_hash(a) == bl.canonical_hash(b)
    assert bl.canonical_hash(a).startswith("sha256:")
    assert bl.canonical_hash({"task_id": "B"}) != bl.canonical_hash(a)

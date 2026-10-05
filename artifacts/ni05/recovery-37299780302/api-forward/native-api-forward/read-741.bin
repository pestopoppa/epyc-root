"""Phase B — admission gate behavior + active_region_holders helper.

HERMETICITY (2026-08-03): the `ContentionGate` tests below assert against a
DECLARED matrix (`tests/unit/contention_gate_fixture.py`), not the committed
`orchestration/contention_matrix.yaml`. That file is a measurement artifact
that is regenerated per re-bench — see the fixture module's docstring for the
three ways the 2026-08-01 re-bench moved it under these tests. Whether the
shipped artifact still describes the live stack is asserted separately, by the
`test_real_matrix_*` tests in `test_scheduling_contention.py`.
"""

from __future__ import annotations

import importlib
import sys
import threading
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

contention = importlib.import_module("src.scheduling.contention")
gate_mod = importlib.import_module("src.scheduling.contention_gate")
cpu_region_lock = importlib.import_module("src.runtime.cpu_region_lock")

from tests.unit.contention_gate_fixture import (  # noqa: E402
    gate_fixture_matrix,
    make_gate,
    pin_matrix_status,
)


@pytest.fixture
def matrix():
    """The declared gate matrix (see contention_gate_fixture)."""
    return gate_fixture_matrix()


@pytest.fixture(autouse=True)
def reset_singleton():
    """Each test gets a fresh ContentionGate singleton."""
    gate_mod.reset_gate()
    yield
    gate_mod.reset_gate()


# ── active_region_holders (helper factoring per handoff line 35) ───────


def test_active_region_holders_empty_when_no_topology() -> None:
    """No instance_regions → empty dict."""
    holders = cpu_region_lock.active_region_holders(instance_regions={})
    assert holders == {}


def test_active_region_holders_empty_when_no_locks(tmp_path, monkeypatch) -> None:
    """Topology present but no lock files exist → empty (nothing actively decoding)."""
    monkeypatch.setattr(cpu_region_lock, "_tmp_dir", lambda: tmp_path)
    instance_regions = {
        ("frontdoor", 0): frozenset({"q0", "q1"}),
        ("frontdoor", 1): frozenset({"q0"}),
        ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
    }
    holders = cpu_region_lock.active_region_holders(instance_regions=instance_regions)
    assert holders == {}


def test_active_region_holders_returns_instances_with_held_regions(tmp_path, monkeypatch) -> None:
    """Create a held lock file → its (role, idx) shows up in the result."""
    monkeypatch.setattr(cpu_region_lock, "_tmp_dir", lambda: tmp_path)
    # Stub _current_lock_owner_pids: q0 of frontdoor is held; q1 isn't.
    def fake_owners(path):
        return ["12345"] if path.name == "cpu_region.frontdoor.q0.lock" else []
    monkeypatch.setattr(cpu_region_lock, "_current_lock_owner_pids", fake_owners)
    # Touch the lock files so .exists() passes
    (tmp_path / "cpu_region.frontdoor.q0.lock").touch()
    (tmp_path / "cpu_region.frontdoor.q1.lock").touch()
    (tmp_path / "cpu_region.worker_general.q0.lock").touch()

    instance_regions = {
        ("frontdoor", 0): frozenset({"q0", "q1"}),  # has q0 held → active
        ("frontdoor", 1): frozenset({"q1"}),         # only q1 → not active
        ("worker_general", 0): frozenset({"q0"}),    # different role, no held lock
    }
    holders = cpu_region_lock.active_region_holders(instance_regions=instance_regions)
    # Only frontdoor instance 0 is active (its q0 is held)
    assert holders == {"frontdoor": [0]}


def test_active_region_holders_groups_multiple_instances(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cpu_region_lock, "_tmp_dir", lambda: tmp_path)
    def fake_owners(path):
        return ["111"] if "q0" in path.name or "q2" in path.name else []
    monkeypatch.setattr(cpu_region_lock, "_current_lock_owner_pids", fake_owners)
    for region in ("q0", "q1", "q2", "q3"):
        (tmp_path / f"cpu_region.frontdoor.{region}.lock").touch()

    instance_regions = {
        ("frontdoor", 1): frozenset({"q0"}),  # held
        ("frontdoor", 2): frozenset({"q1"}),  # not held
        ("frontdoor", 3): frozenset({"q2"}),  # held
    }
    holders = cpu_region_lock.active_region_holders(instance_regions=instance_regions)
    assert holders == {"frontdoor": [1, 3]}  # sorted


# ── ContentionGate.evaluate ────────────────────────────────────────────


def test_gate_admits_when_no_active_decodes(matrix) -> None:
    gate = make_gate(gate_mod, {}, matrix=matrix)
    d = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert d.admitted
    assert d.decision == contention.PairDecision.ALLOW


def test_gate_blocks_background_when_pair_catastrophic(matrix) -> None:
    """frontdoor+ingest = 0.37, far below the 0.85 floor → background QUEUEs.

    The whole active set is declared light, so the defensive N-way layer allows
    it: the QUEUE here can only have come from the PAIR ratio.
    """
    gate = make_gate(gate_mod, {"ingest_long_context": [0]}, matrix=matrix)
    d = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not d.admitted
    assert d.decision == contention.PairDecision.QUEUE
    assert "ingest_long_context" in d.blocking_roles


def test_gate_blocks_foreground_when_pair_below_floor(matrix) -> None:
    """frontdoor+architect = 0.50 < 0.85 → foreground also queues (per handoff:
    'block or delay unless explicit low-latency override')."""
    gate = make_gate(gate_mod, {"architect_general": [0]}, matrix=matrix)
    d = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert not d.admitted
    assert d.decision == contention.PairDecision.QUEUE


def test_gate_allows_borderline_pair_for_foreground_but_queues_background(matrix) -> None:
    """floor <= ratio < 1.0 is the third pair band: foreground ALLOW, background
    QUEUE. Distinguishes 'below floor' from 'merely borderline'."""
    gate = make_gate(gate_mod, {"worker_borderline": [0]}, matrix=matrix)
    fg = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert fg.admitted and fg.decision == contention.PairDecision.ALLOW
    bg = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not bg.admitted and bg.decision == contention.PairDecision.QUEUE


def test_gate_allows_known_good_pair(matrix) -> None:
    """A concurrency-positive pair (>= 1.0) is ALLOW even for background."""
    gate = make_gate(gate_mod, {"vision_escalation": [0]}, matrix=matrix)
    d = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert d.admitted
    assert d.decision == contention.PairDecision.ALLOW


def test_gate_allows_resolved_gpu_candidate_while_cpu_regions_are_active(
    matrix, monkeypatch
) -> None:
    from src.scheduling.device_model import DeviceClass, RoleDevice

    def resolve(role: str) -> RoleDevice:
        device_class = (
            DeviceClass.GPU if role == "coder_escalation" else DeviceClass.CPU
        )
        return RoleDevice(
            role=role,
            device_class=device_class,
            device="ROCm0" if device_class is DeviceClass.GPU else None,
            source="unit",
            corroborated=True,
            accounting_key=role,
        )

    monkeypatch.setattr("src.scheduling.device_model.resolve_role_device", resolve)
    gate = make_gate(gate_mod, {"frontdoor": [0]}, matrix=matrix)

    decision = gate.evaluate("coder_escalation", contention.TrafficClass.BACKGROUND)

    assert decision.admitted
    assert decision.decision == contention.PairDecision.ALLOW
    assert "GPU lane" in decision.reason


def test_gate_allows_same_role_when_matrix_says_allow(matrix) -> None:
    """frontdoor is same-role-allow. A second frontdoor request should be
    admitted even while frontdoor is decoding."""
    gate = make_gate(gate_mod, {"frontdoor": [0]}, matrix=matrix)
    d = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert d.admitted


def test_gate_same_role_allow_verdict_admits_both_traffic_classes(matrix) -> None:
    """A same-role verdict of 'allow' admits in BOTH classes.

    (History: vision_escalation same-role once read 'block'; the 2026-05-26
    certified-affinity re-bench REFUTED that as a bad-affinity artifact — the
    quarters had been pinned to the wrong cores. The matrix has said 'allow'
    ever since, which is what this asserts.)
    """
    gate = make_gate(gate_mod, {"vision_escalation": [0]}, matrix=matrix)
    bg = gate.evaluate("vision_escalation", contention.TrafficClass.BACKGROUND)
    assert bg.admitted
    fg = gate.evaluate("vision_escalation", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert fg.admitted


def test_gate_same_role_block_queues_background_degrades_foreground() -> None:
    """The same-role BLOCK path. The real matrix carries no measured same-role
    block any more (the note this file used to carry said to cover it with a
    synthetic fixture if regression protection was wanted — this is that)."""
    m = gate_fixture_matrix()
    m.same_role["frontdoor"] = contention.SameRole(role="frontdoor", verdict="block")
    gate = make_gate(gate_mod, {"frontdoor": [0]}, matrix=m)
    bg = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not bg.admitted and bg.decision == contention.PairDecision.QUEUE
    fg = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert fg.admitted and fg.decision == contention.PairDecision.DEGRADED_ALLOW


def test_gate_picks_worst_pair_in_multi_active(matrix) -> None:
    """When multiple roles are active, gate picks the most-restrictive decision."""
    gate = make_gate(
        gate_mod,
        {"vision_escalation": [0], "architect_general": [0]},
        matrix=matrix,
    )
    d = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not d.admitted
    assert "architect_general" in d.blocking_roles
    # vision_escalation is allow-pair so shouldn't appear as blocker
    assert "vision_escalation" not in d.blocking_roles


def test_gate_unknown_pair_blocks_background_allows_foreground(matrix) -> None:
    """Per handoff: unknown pair → background QUEUE, foreground ALLOW.

    `synthetic_unmeasured` has no pair row but IS declared light, so the N-way
    layer is neutral — this isolates the unknown-PAIR policy.
    """
    gate = make_gate(gate_mod, {"synthetic_unmeasured": [0]}, matrix=matrix)
    bg = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not bg.admitted
    fg = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert fg.admitted


def test_gate_nway_block_restricts_a_pairwise_allowed_set(matrix) -> None:
    """J4c defensive layer: pairwise-allow does NOT certify the active SET.

    frontdoor+worker_summarize is a 1.30 allow PAIR, but the set is a measured
    0.72 aggregate-negative N-way — the gate must take the N-way verdict and
    count the restriction. Nothing else at gate level covers this path, and it
    is exactly the layer that silently drives verdicts when a regenerated
    matrix ships without an `n_way` section.
    """
    gate = make_gate(gate_mod, {"worker_summarize": [0]}, matrix=matrix)
    assert (
        contention.pair_policy(
            "frontdoor", "worker_summarize", contention.TrafficClass.BACKGROUND, matrix=matrix
        )
        == contention.PairDecision.ALLOW
    )
    d = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not d.admitted
    assert d.decision == contention.PairDecision.QUEUE
    assert d.blocking_roles == ["worker_summarize"]
    assert gate.metrics_snapshot()["contention_nway_restricted_count"] == 1


# ── ContentionGate.admit (waiting behavior) ───────────────────────────


def test_admit_returns_immediately_when_ok(matrix) -> None:
    gate = make_gate(gate_mod, {}, matrix=matrix)
    t0 = time.monotonic()
    d = gate.admit("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE, max_queue_wait_ms=100)
    assert d.admitted
    assert (time.monotonic() - t0) < 0.5


def test_admit_times_out_when_persistently_blocked(matrix) -> None:
    gate = make_gate(gate_mod, {"architect_general": [0]}, matrix=matrix)
    t0 = time.monotonic()
    d = gate.admit("frontdoor", contention.TrafficClass.BACKGROUND, max_queue_wait_ms=400)
    elapsed = time.monotonic() - t0
    assert not d.admitted
    assert "timeout" in d.reason
    assert 0.4 <= elapsed < 1.5  # respected the 400ms budget


def test_admit_zero_wait_times_out_without_poll_sleep(matrix, monkeypatch) -> None:
    gate = make_gate(gate_mod, {"architect_general": [0]}, matrix=matrix)

    monkeypatch.setattr(gate_mod.time, "sleep", lambda _: pytest.fail("zero-wait path slept"))

    d = gate.admit("frontdoor", contention.TrafficClass.BACKGROUND, max_queue_wait_ms=0)

    assert not d.admitted
    assert d.decision == contention.PairDecision.QUEUE
    assert d.blocking_roles == ["architect_general"]
    assert "timeout" in d.reason
    assert gate.metrics_snapshot()["contention_timeout_count"] == 1


def test_admit_unblocks_when_active_clears(matrix) -> None:
    # Mutable holders dict — flip to empty after 200 ms
    holders = {"architect_general": [0]}
    gate = gate_mod.ContentionGate(matrix=matrix, active_holders_fn=lambda: dict(holders))
    pin_matrix_status(gate)

    def clear_later():
        time.sleep(0.20)
        holders.clear()
    threading.Thread(target=clear_later, daemon=True).start()

    t0 = time.monotonic()
    d = gate.admit("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE, max_queue_wait_ms=2000)
    elapsed = time.monotonic() - t0
    assert d.admitted
    assert 0.15 <= elapsed < 1.0


# ── Singleton + metrics ────────────────────────────────────────────────


def test_get_gate_returns_singleton() -> None:
    g1 = gate_mod.get_gate()
    g2 = gate_mod.get_gate()
    assert g1 is g2


def test_metrics_snapshot_includes_required_keys(matrix) -> None:
    gate = make_gate(gate_mod, {}, matrix=matrix)
    snap = gate.metrics_snapshot()
    # Acceptance: handoff requires these counter keys
    for key in (
        "contention_blocked_count",
        "contention_wait_seconds",
        "contention_unknown_pair_count",
        "contention_admitted_count",
        "contention_nway_restricted_count",
        "active_decodes_by_role",
        "matrix_status",
    ):
        assert key in snap


def test_metrics_record_blocked_count(matrix) -> None:
    gate = make_gate(gate_mod, {"architect_general": [0]}, matrix=matrix)
    # Force one short-budget admit that times out → records blocked count
    gate.admit("frontdoor", contention.TrafficClass.BACKGROUND, max_queue_wait_ms=200)
    snap = gate.metrics_snapshot()
    # Pair key is sorted: ("architect_general", "frontdoor")
    assert any("architect_general" in k and "frontdoor" in k
               for k in snap["contention_blocked_count"].keys())
    assert snap["contention_timeout_count"] == 1


def test_metrics_use_exact_holder_instances_not_attribution_overcount(
    matrix,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setattr(
        cpu_region_lock,
        "active_region_holders",
        lambda: {"worker_general": [0, 1, 2, 3, 4]},
    )
    monkeypatch.setattr(
        cpu_region_lock,
        "active_region_holder_instances",
        lambda: {"worker_general": [0]},
    )
    gate = gate_mod.ContentionGate(matrix=matrix)
    pin_matrix_status(gate)

    gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    snap = gate.metrics_snapshot()

    assert snap["active_decodes_by_role"] == {"worker_general": 1}
    assert snap["active_instances_by_role"] == {"worker_general": [0]}


def test_gate_fails_closed_on_stale_matrix(matrix) -> None:
    """#2 (operator audit 2026-05-27): when matrix_health is not OK (topology changed / matrix
    stale) AND concurrency is active, evaluate() fail-closes — background SERIALIZES (QUEUE, not
    admitted), foreground degraded-admits (visible, not silently 'healthy')."""
    # Simulate a topology change the matrix wasn't benched against (force cached STALE health).
    gate = make_gate(
        gate_mod, {"frontdoor": [0]}, matrix=matrix, status=contention.MatrixStatus.STALE
    )
    bg = gate.evaluate("frontdoor", contention.TrafficClass.BACKGROUND)
    assert not bg.admitted and bg.decision == contention.PairDecision.QUEUE
    assert "fail-closed" in bg.reason
    fg = gate.evaluate("frontdoor", contention.TrafficClass.FOREGROUND_INTERACTIVE)
    assert fg.admitted and fg.decision == contention.PairDecision.DEGRADED_ALLOW


def test_matrix_health_hash_ignores_auxiliary_unmeasured_roles(monkeypatch) -> None:
    measured_config = {
        "frontdoor": {"instances": [("0-1", 8070, 2)]},
        "worker_general": {"instances": [("2-3", 8072, 2)]},
    }
    live_config = {
        **measured_config,
        "eval_batch_frontdoor": {"instances": [("0-1", 18070, 2)]},
    }
    matrix = contention.ContentionMatrix(
        version=1,
        measured_at="",
        host="",
        topology_hash=contention.topology_fingerprint(measured_config),
        default_floor=0.85,
        pairs={
            ("frontdoor", "worker_general"): contention.Pair(
                roles=("frontdoor", "worker_general"),
                ratio=1.0,
                verdict="allow",
            )
        },
    )
    import scripts.server.stack_numa as stack_numa

    captured: dict[str, str | None] = {}

    def fake_matrix_status(*, current_topology_hash=None):
        captured["hash"] = current_topology_hash
        return contention.MatrixStatus.OK

    monkeypatch.setattr(stack_numa, "NUMA_CONFIG", live_config)
    monkeypatch.setattr(gate_mod, "matrix_status", fake_matrix_status)

    gate = gate_mod.ContentionGate(matrix=matrix)

    assert gate.matrix_health() == contention.MatrixStatus.OK
    assert captured["hash"] == contention.topology_fingerprint(measured_config)
    assert captured["hash"] != contention.topology_fingerprint(live_config)

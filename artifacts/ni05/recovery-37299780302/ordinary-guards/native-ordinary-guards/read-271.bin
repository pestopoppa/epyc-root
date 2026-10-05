"""Tests for DS-6 (backend instance management, QuarterScheduler) and DS-7 (stack templates)."""

import time
from unittest.mock import MagicMock

import pytest

from src.backends.round_robin import RoundRobinBackend
from src.backends.concurrency_aware import (
    ConcurrencyAwareBackend,
    _STATE_ASSIGNED_QUARTER,
    _STATE_MIGRATION_FAILED_COLD,
)

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"


# === DS-6: Backend instance management ===


class TestRoundRobinDynamicInstances:
    """Test add_instance/remove_instance on RoundRobinBackend."""

    def _make_backend(self):
        return MagicMock()

    def test_add_instance(self):
        b1, b2, b3 = self._make_backend(), self._make_backend(), self._make_backend()
        rr = RoundRobinBackend([b1, b2], role="test")
        assert rr.instance_count() == 2
        rr.add_instance(b3)
        assert rr.instance_count() == 3

    def test_remove_instance(self):
        b1, b2 = self._make_backend(), self._make_backend()
        rr = RoundRobinBackend([b1, b2], role="test")
        assert rr.remove_instance(1)
        assert rr.instance_count() == 1

    def test_remove_invalid_index(self):
        rr = RoundRobinBackend([self._make_backend()], role="test")
        assert not rr.remove_instance(5)
        assert not rr.remove_instance(-1)

    def test_remove_active_instance_refused(self):
        b1 = self._make_backend()
        b1.infer = MagicMock(return_value="result")
        rr = RoundRobinBackend([b1], role="test")
        # Simulate active request
        rr._active_per_instance[0] = 1
        assert not rr.remove_instance(0)

    def test_stats_after_add(self):
        rr = RoundRobinBackend([self._make_backend()], role="test")
        rr.add_instance(self._make_backend())
        stats = rr.get_stats()
        assert stats["round_robin_instances"] == 2
        assert len(stats["active_per_instance"]) == 2


class TestConcurrencyAwareDynamicQuarters:
    """Test add_quarter/remove_quarter on ConcurrencyAwareBackend."""

    def _make_backend(self):
        b = MagicMock()
        b.health_check = MagicMock(return_value=True)
        b.config = MagicMock(base_url="http://localhost:9999")
        return b

    def test_add_quarter(self):
        full = self._make_backend()
        q1 = self._make_backend()
        ca = ConcurrencyAwareBackend(full, [q1], role="test")
        assert ca.quarter_count() == 1
        idx = ca.add_quarter(self._make_backend())
        assert idx == 1
        assert ca.quarter_count() == 2

    def test_remove_quarter(self):
        full = self._make_backend()
        q1, q2 = self._make_backend(), self._make_backend()
        ca = ConcurrencyAwareBackend(full, [q1, q2], role="test")
        assert ca.remove_quarter(0)
        assert ca.quarter_count() == 1

    def test_remove_active_quarter_refused(self):
        full = self._make_backend()
        q1 = self._make_backend()
        ca = ConcurrencyAwareBackend(full, [q1], role="test")
        ca._quarter_active[0] = True
        assert not ca.remove_quarter(0)

    def test_session_affinity_cleanup_on_remove(self):
        full = self._make_backend()
        q1, q2 = self._make_backend(), self._make_backend()
        ca = ConcurrencyAwareBackend(full, [q1, q2], role="test")
        ca._session_quarter["sess-a"] = 0
        ca._session_quarter["sess-b"] = 1
        ca.remove_quarter(0)
        # sess-a was on quarter 0 → removed
        assert "sess-a" not in ca._session_quarter
        # sess-b was on quarter 1 → shifted to 0
        assert ca._session_quarter["sess-b"] == 0

    def test_restore_failure_does_not_create_stale_affinity(self, monkeypatch):
        full = self._make_backend()
        q1 = self._make_backend()
        q1.config = MagicMock(base_url="http://localhost:9998")
        ca = ConcurrencyAwareBackend(full, [q1], role="test")
        monkeypatch.setattr("src.backends.concurrency_aware._slot_save", lambda *args, **kwargs: True)
        monkeypatch.setattr("src.backends.concurrency_aware._slot_restore", lambda *args, **kwargs: False)

        ca._select("sess-a")
        ca._release(-1, True)
        ca._select("sess-b")

        deadline = time.time() + 1.0
        while time.time() < deadline:
            if ca._session_state.get("sess-a", {}).get("state") == _STATE_MIGRATION_FAILED_COLD:
                break
            time.sleep(0.01)

        assert "sess-a" not in ca._session_quarter
        assert ca._session_state["sess-a"]["state"] == _STATE_MIGRATION_FAILED_COLD
        assert ca._session_state["sess-a"]["quarter"] == 0

        backend, idx, is_full = ca._select("sess-a")
        assert backend is q1
        assert idx == 0
        assert is_full is False

    def test_successful_restore_finalizes_quarter_affinity(self, monkeypatch):
        full = self._make_backend()
        q1 = self._make_backend()
        q1.config = MagicMock(base_url="http://localhost:9998")
        ca = ConcurrencyAwareBackend(full, [q1], role="test")
        monkeypatch.setattr("src.backends.concurrency_aware._slot_save", lambda *args, **kwargs: True)
        monkeypatch.setattr("src.backends.concurrency_aware._slot_restore", lambda *args, **kwargs: True)
        monkeypatch.setattr("src.backends.concurrency_aware._slot_erase", lambda *args, **kwargs: True)

        ca._select("sess-a")
        ca._release(-1, True)
        ca._select("sess-b")

        deadline = time.time() + 1.0
        while time.time() < deadline:
            if ca._session_state.get("sess-a", {}).get("state") == _STATE_ASSIGNED_QUARTER:
                break
            time.sleep(0.01)

        assert ca._session_quarter["sess-a"] == 0
        assert ca._session_state["sess-a"]["state"] == _STATE_ASSIGNED_QUARTER
        assert ca._session_state["sess-a"]["detail"] == "restored"

    def test_stats_include_session_states(self):
        full = self._make_backend()
        q1 = self._make_backend()
        ca = ConcurrencyAwareBackend(full, [q1], role="test")
        ca._session_state["sess-a"] = {
            "state": _STATE_MIGRATION_FAILED_COLD,
            "quarter": 0,
            "detail": "restore_failed",
            "updated_at": time.time(),
        }
        stats = ca.get_stats()
        assert stats["session_states"]["sess-a"]["state"] == _STATE_MIGRATION_FAILED_COLD
        assert stats["migration_pending"] == {}


# === DS-6: QuarterScheduler ===


class TestQuarterScheduler:
    """Test QuarterScheduler core operations."""

    def _make_scheduler(self):
        from scripts.server.quarter_scheduler import QuarterScheduler
        return QuarterScheduler()

    def test_initial_state(self):
        qs = self._make_scheduler()
        state = qs.get_state()
        assert len(state["slots"]) == 4
        for slot in state["slots"].values():
            assert slot["status"] == "unavailable"

    def test_assign_and_unassign(self):
        qs = self._make_scheduler()
        assert qs.assign("Q0A", "frontdoor")
        slots = qs.get_slots_for_role("frontdoor")
        assert len(slots) == 1
        assert slots[0].name == "Q0A"

        assert qs.unassign("Q0A")
        assert len(qs.get_slots_for_role("frontdoor")) == 0

    def test_assign_invalid_slot(self):
        qs = self._make_scheduler()
        assert not qs.assign("Q99", "frontdoor")

    def test_get_available_slots(self):
        qs = self._make_scheduler()
        available = qs.get_available_slots()
        assert len(available) == 4  # All start as UNAVAILABLE

        qs.assign("Q0A", "frontdoor")
        available = qs.get_available_slots()
        assert len(available) == 3

    def test_burst_request(self):
        qs = self._make_scheduler()
        # Assign all 4 quarters
        for name in ["Q0A", "Q0B", "Q1A", "Q1B"]:
            qs.assign(name, "frontdoor")

        burst = qs.request_burst("architect_general", quarters_needed=2)
        assert burst is not None
        assert len(burst.quarters_to_drain) == 2

        # Check draining state
        state = qs.get_state()
        draining_count = sum(1 for s in state["slots"].values() if s["status"] == "draining")
        assert draining_count == 2

    def test_burst_release(self):
        qs = self._make_scheduler()
        for name in ["Q0A", "Q0B", "Q1A", "Q1B"]:
            qs.assign(name, "frontdoor")

        qs.request_burst("architect_general", quarters_needed=2)
        freed = qs.release_burst()
        assert len(freed) == 2

        state = qs.get_state()
        unavailable_count = sum(1 for s in state["slots"].values() if s["status"] == "unavailable")
        assert unavailable_count == 2

    def test_burst_not_enough_quarters(self):
        qs = self._make_scheduler()
        qs.assign("Q0A", "frontdoor")
        burst = qs.request_burst("architect", quarters_needed=3)
        assert burst is None

    def test_double_burst_refused(self):
        qs = self._make_scheduler()
        for name in ["Q0A", "Q0B", "Q1A", "Q1B"]:
            qs.assign(name, "frontdoor")
        qs.request_burst("architect_general", quarters_needed=2)
        second = qs.request_burst(_RETIRED_ARCHITECT_ROLE, quarters_needed=2)
        assert second is None

    def test_quarter_topology_matches_live_numa_constants(self):
        """DS-6 is PARKED, not dead — so its topology must not silently rot.

        P1-9 (2026-07-30) proposed deleting `quarter_scheduler.py` partly on the
        claim that it was "now factually wrong about the machine". That claim was
        refuted on 2026-08-12: the table below is byte-identical to the live
        production constants. This test pins that parity so the claim cannot
        become true unnoticed — if `stack_numa.py` is re-derived and this table
        is not, this fails loudly instead of rotting into a real defect.

        Guard, not gold-plating: `stack_numa.NUMA_Q*` is the load-bearing copy
        that production reads. This asserts the parked copy still agrees with it.
        """
        from scripts.server import stack_numa
        from scripts.server.quarter_scheduler import QuarterScheduler

        live = {
            "Q0A": stack_numa.NUMA_Q0A,
            "Q0B": stack_numa.NUMA_Q0B,
            "Q1A": stack_numa.NUMA_Q1A,
            "Q1B": stack_numa.NUMA_Q1B,
        }
        parked = QuarterScheduler.QUARTER_TOPOLOGY

        assert set(parked) == set(live), (
            "quarter slot names drifted from stack_numa NUMA_Q* constants"
        )
        for name, (cpu_list, threads) in live.items():
            assert parked[name]["cpu_list"] == cpu_list, (
                f"{name} cpu_list drifted: quarter_scheduler has "
                f"{parked[name]['cpu_list']!r}, stack_numa has {cpu_list!r}"
            )
            assert parked[name]["threads"] == threads, (
                f"{name} thread count drifted: quarter_scheduler has "
                f"{parked[name]['threads']}, stack_numa has {threads}"
            )


# === DS-7: Stack Templates ===


class TestStackTemplates:
    """Test template loading and validation."""

    def test_load_default_template(self):
        from src.config.stack_templates import load_template
        template = load_template("default")
        assert template.name == "default"
        assert "frontdoor" in template.roles
        assert "architect_general" in template.roles
        assert template.total_instances > 0
        assert template.total_ram_gb > 0

    def test_frontdoor_has_full_and_quarters(self):
        """frontdoor declares an aligned full plus EVERY sibling instance.

        The counts and ports are derived from ``scripts.server.stack_numa.NUMA_CONFIG``
        — the host-facts table default.yaml restates — rather than pinned. The
        sibling count has moved twice (4×48t quarters -> 2×48t halves on the
        2026-07-30/31 retirement), and a pinned ``== 4`` asserted a lineup whose
        ports had already been freed.
        """
        from scripts.server.stack_numa import NUMA_CONFIG
        from src.config.stack_templates import load_template

        cfg = NUMA_CONFIG["frontdoor"]
        full_idx = cfg["full_instance_idx"]
        expected_full_port = cfg["instances"][full_idx][1]
        expected_sibling_ports = [
            inst[1] for idx, inst in enumerate(cfg["instances"]) if idx != full_idx
        ]
        assert expected_sibling_ports, "frontdoor must declare sibling instances"

        template = load_template("default")
        fd = template.roles["frontdoor"]
        assert fd.full is not None
        assert fd.full.port == expected_full_port
        assert [q.port for q in fd.quarters] == expected_sibling_ports
        # Thread counts must match the shape too, or the template describes a
        # fleet the launcher cannot produce.
        assert fd.full.threads == cfg["instances"][full_idx][2]
        assert [q.threads for q in fd.quarters] == [
            inst[2] for idx, inst in enumerate(cfg["instances"]) if idx != full_idx
        ]

    def test_architect_has_single_full_instance(self):
        """architect_general is one instance whose shape matches NUMA_CONFIG.

        ``numa: FULL`` was correct while the role served the whole-machine 122B;
        the 2026-07-31/08-01 cutover moved that model to architect_critic and
        re-placed architect_general on the MI210 with only 8 pinned host threads.
        Derive the shape from the same host-facts table instead of restating it.
        """
        from scripts.server.stack_numa import _CPU_SHAPES, NUMA_CONFIG
        from src.config.stack_templates import load_template

        instances = NUMA_CONFIG["architect_general"]["instances"]
        assert len(instances) == 1
        cpuset, expected_port, expected_threads = instances[0]

        template = load_template("default")
        arch = template.roles["architect_general"]
        assert arch.full is not None
        assert arch.full.port == expected_port
        assert arch.full.threads == expected_threads
        assert len(arch.replicas) == 0
        assert not arch.quarters
        # The declared shape name must resolve to the cpuset actually pinned.
        shape = arch.full.numa
        shape_key = shape if shape in _CPU_SHAPES else f"NUMA_{shape}"
        assert shape_key in _CPU_SHAPES, f"unknown CPU shape {shape!r}"
        assert _CPU_SHAPES[shape_key] == (cpuset, expected_threads)

    def test_embedder_fleet_has_single_embedding_instances(self):
        from src.config.stack_templates import load_template
        template = load_template("default")
        embedder_roles = [
            "embedder",
            "embedder_1",
            "embedder_2",
            "embedder_3",
            "embedder_4",
            "embedder_5",
        ]
        assert [template.roles[name].full.port for name in embedder_roles] == [
            8090,
            8091,
            8092,
            8093,
            8094,
            8095,
        ]
        assert {template.roles[name].mode for name in embedder_roles} == {"embedding"}
        assert all(not template.roles[name].quarters for name in embedder_roles)

    def test_validate_default_passes(self):
        from src.config.stack_templates import load_template, validate_template
        template = load_template("default")
        result = validate_template(template)
        assert result.valid, f"Validation failed: {result.errors}"

    def test_validate_catches_port_conflict(self):
        from src.config.stack_templates import (
            StackTemplate, RoleConfig, InstanceConfig, validate_template,
        )
        template = StackTemplate(
            name="conflict",
            roles={
                "frontdoor": RoleConfig(
                    model="m1", quant="Q4_K_M", tier="HOT", ram_gb=10,
                    full=InstanceConfig(port=8080, numa="NODE0", threads=96),
                ),
                "worker": RoleConfig(
                    model="m2", quant="Q4_K_M", tier="HOT", ram_gb=10,
                    full=InstanceConfig(port=8080, numa="NODE1", threads=96),
                ),
            },
        )
        result = validate_template(template)
        assert not result.valid
        assert any("Port conflict" in e for e in result.errors)

    def test_validate_catches_memory_exceeded(self):
        from src.config.stack_templates import (
            StackTemplate, RoleConfig, InstanceConfig, validate_template,
            MAX_STACK_RAM_GB,
        )
        template = StackTemplate(
            name="huge",
            roles={
                "frontdoor": RoleConfig(
                    model="huge", quant="Q4_K_M", tier="HOT",
                    ram_gb=MAX_STACK_RAM_GB + 100,
                    full=InstanceConfig(port=8080, numa="NODE0", threads=96),
                ),
            },
        )
        result = validate_template(template)
        assert not result.valid
        assert any("budget exceeded" in e for e in result.errors)

    def test_validate_catches_missing_frontdoor(self):
        from src.config.stack_templates import (
            StackTemplate, RoleConfig, InstanceConfig, validate_template,
        )
        template = StackTemplate(
            name="no-fd",
            roles={
                "worker": RoleConfig(
                    model="m1", quant="Q4_K_M", tier="HOT", ram_gb=10,
                    full=InstanceConfig(port=8080, numa="NODE0", threads=96),
                ),
            },
        )
        result = validate_template(template)
        assert not result.valid
        assert any("frontdoor" in e for e in result.errors)

    def test_discover_templates(self):
        from src.config.stack_templates import discover_templates
        names = discover_templates()
        assert "default" in names

    def test_load_nonexistent_template(self):
        from src.config.stack_templates import load_template
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent_template_xyz")

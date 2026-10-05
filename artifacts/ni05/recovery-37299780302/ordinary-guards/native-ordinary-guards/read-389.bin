"""P2-1 (role-agnostic resident lane) + P2-3 (Stage-0 hardening) tests.

Kept in a file separate from ``test_gpu_shadow_lane.py`` because the P0-7/P2-6
suite is being edited concurrently by another session on this shared clone.

The load-bearing assertions here are the REFUSALS. A capacity policy that
degrades to a guess under an unexpected input is worse than no policy, so every
"no validated operating point" path gets a test proving it refuses rather than
falls back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.server import gpu_shadow_lane as lane
from scripts.server import gpu_shadow_lane_lease as lease
from scripts.server import gpu_shadow_lane_stage0 as stage0
from scripts.server import gpu_shadow_lane_tenancy as tenancy_mod
from src.features import Features


@pytest.fixture
def enabled() -> Features:
    return Features(gpu_shadow_lane=True)


@pytest.fixture
def tenancy(enabled: Features) -> tenancy_mod.Tenancy:
    return tenancy_mod.load_tenancy(feats=enabled)


@pytest.fixture
def policy(enabled: Features) -> lane.NpCeilingPolicy:
    return lane.load_np_ceiling_policy(feats=enabled)


# ---------------------------------------------------------------------------
# P2-1 — tenancy as data, and the invariants the data may not express
# ---------------------------------------------------------------------------
class TestTenancyInertness:
    def test_load_refused_while_flag_off(self):
        with pytest.raises(lane.GpuShadowLaneDisabled):
            tenancy_mod.load_tenancy(feats=Features(gpu_shadow_lane=False))

    def test_no_production_module_imports_tenancy_or_lease(self):
        """P2-1 stays uncoupled: the launch/routing path never imports the
        tenancy or lease modules, so neither can execute in production."""
        root = Path(lane.__file__).resolve().parents[2]
        for rel in (
            "src/api/routes/chat_pipeline/routing_decision.py",
            "src/registry/registry_compiler.py",
            "scripts/server/stack_numa.py",
        ):
            source = (root / rel).read_text(encoding="utf-8")
            assert "gpu_shadow_lane_tenancy" not in source, rel
            assert "gpu_shadow_lane_lease" not in source, rel

    def test_module_has_no_registry_apply_path(self):
        """D3 is enforced by the ABSENCE of an apply function, not by a flag
        guarding one — a guard can be flipped, a missing function cannot."""
        source = Path(tenancy_mod.__file__).read_text(encoding="utf-8")
        for forbidden in ("def apply_", "registry_compiler", "--apply"):
            assert forbidden not in source


class TestTenancyValidation:
    def test_committed_tenancy_is_state_a(self, tenancy: tenancy_mod.Tenancy):
        assert tenancy.resident_state == tenancy_mod.STATE_A
        assert tenancy.resident_tenant is None

    def test_slot_is_lane_property_not_tenant_property(self, tenancy: tenancy_mod.Tenancy):
        assert tenancy.slot.port == lane.LANE_PORT
        assert tenancy.slot.host_cpuset == lane.LANE_HOST_CPUSET
        assert tenancy.slot.device == lane.LANE_DEVICE
        assert tenancy.slot.binary_version == lane.LANE_BINARY_VERSION

    def test_refuses_declaring_state_b(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "tenancy.yaml"
        bad.write_text(
            "version: 1\nlane: gpu_shadow_lane\nresident_state: state_b\n",
            encoding="utf-8",
        )
        with pytest.raises(tenancy_mod.TenancyError, match="resident_state"):
            tenancy_mod.load_tenancy(bad, feats=enabled)

    def _minimal(self, binding: str) -> str:
        return f"""
version: 1
lane: gpu_shadow_lane
slot:
  device: ROCm0
  port: 18100
  host_cpuset: "184-191"
  host_threads: 8
  binary: {{dir: /x, version: "10107", commit: 67a433bf4}}
  region_claim: {{lock_role: gpu_shadow_lane, cpu_regions_from: host_cpuset_smt_folded, device_lock: true}}
resident_state: state_a
resident_tenant: null
tenants:
  t:
    np_policy_tenant: p
    model: {{path: /m.gguf, bytes: 1, sha256: abc, sha256_status: attested}}
    mode: {{mtp: false, reasoning: false}}
    role_bindings:
      - {binding}
"""

    def test_refuses_binding_a_production_role(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "tenancy.yaml"
        bad.write_text(
            self._minimal(
                "{role: coder_escalation, shadow: true, duty: coder, "
                "admission_class: escalations}"
            ),
            encoding="utf-8",
        )
        with pytest.raises(tenancy_mod.TenancyError, match="PRODUCTION role"):
            tenancy_mod.load_tenancy(bad, feats=enabled)

    def test_refuses_non_shadow_binding(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "tenancy.yaml"
        bad.write_text(
            self._minimal(
                "{role: whatever_shadow, shadow: false, duty: coder, "
                "admission_class: escalations}"
            ),
            encoding="utf-8",
        )
        with pytest.raises(tenancy_mod.TenancyError, match="not marked shadow"):
            tenancy_mod.load_tenancy(bad, feats=enabled)

    def test_refuses_unimplemented_admission_class(self, tmp_path: Path, enabled: Features):
        """D1 reserves shed_batch / degraded overflow by NAME. Reserving a name
        is not building it, so a duty may not bind to one yet."""
        bad = tmp_path / "tenancy.yaml"
        bad.write_text(
            self._minimal(
                "{role: shed_shadow, shadow: true, duty: batch, "
                "admission_class: shed_batch}"
            ),
            encoding="utf-8",
        )
        with pytest.raises(tenancy_mod.TenancyError, match="not implemented"):
            tenancy_mod.load_tenancy(bad, feats=enabled)

    def test_refuses_mtp_without_draft_depth(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "tenancy.yaml"
        body = self._minimal(
            "{role: x_shadow, shadow: true, duty: coder, admission_class: escalations}"
        ).replace("mode: {mtp: false, reasoning: false}", "mode: {mtp: true, reasoning: false}")
        bad.write_text(body, encoding="utf-8")
        with pytest.raises(tenancy_mod.TenancyError, match="draft_n_max"):
            tenancy_mod.load_tenancy(bad, feats=enabled)


class TestCrossValidation:
    def test_committed_tables_are_consistent(self, tenancy, policy):
        assert tenancy_mod.cross_validate(tenancy, policy) == []

    def test_every_tenant_has_its_own_policy_row(self, tenancy, policy):
        """The P2-4 P1-4 hazard: stock and FF differ by 1.04 GiB and must never
        share one row."""
        rows = {t.np_policy_tenant for t in tenancy.tenants.values()}
        assert len(rows) == len(tenancy.tenants)
        for tenant in tenancy.tenants.values():
            row = policy.tenants[tenant.np_policy_tenant]
            assert row.model_bytes == tenant.artifact.bytes
            assert row.model_path == tenant.artifact.path

    def test_ff_and_stock_have_distinct_footprints(self, policy):
        ff = policy.tenants["qwen36_27b_ff_q8"]
        stock = policy.tenants["qwen36_27b_stock_q8"]
        assert ff.model_bytes != stock.model_bytes
        assert ff.model_vram_gib > stock.model_vram_gib

    def test_stock_row_is_marked_derived_not_measured(self, policy):
        """Stock has no grid of its own; the row must say so, or a later reader
        will cite FF's throughput as stock's."""
        assert (
            policy.tenants["qwen36_27b_stock_q8"].evidence_basis
            == "derived_conservative_transfer"
        )
        assert policy.tenants["qwen36_27b_ff_q8"].evidence_basis == "measured"


class TestModeAwareCeilings:
    def test_ff_mtp_off_allows_np16_at_32k(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_ff_q8",
                dynamic_budget_gib=36.26,
                slot_context_tokens=32768,
                mode=lane.MODE_MTP_OFF,
            )
            == 16
        )

    def test_ff_mtp_build_caps_at_np8_at_32k(self, policy):
        """The MTP arm's np16 x L32768 cell was a capacity skip. A mode-blind
        table would have authorised np16 there."""
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_ff_mtp_q8",
                dynamic_budget_gib=35.84,
                slot_context_tokens=32768,
                mode=lane.MODE_MTP_ON,
            )
            == 8
        )

    def test_mtp_build_refuses_mtp_off_mode(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_ff_mtp_q8",
                dynamic_budget_gib=35.84,
                slot_context_tokens=2048,
                mode=lane.MODE_MTP_OFF,
            )
            is None
        )

    def test_stock_refuses_mtp_on(self, policy):
        """Stock is a non-MTP artifact with no MTP grid — nothing to transfer."""
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=37.3,
                slot_context_tokens=2048,
                mode=lane.MODE_MTP_ON,
            )
            is None
        )

    def test_unknown_mode_raises(self, policy):
        with pytest.raises(ValueError, match="unknown mode"):
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=37.3,
                slot_context_tokens=2048,
                mode="turbo",
            )


class TestSaturationCapEnforced:
    def test_loader_rejects_ceiling_above_saturation(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "policy.yaml"
        bad.write_text(
            """
version: 1
lane: gpu_shadow_lane
tenants:
  t:
    evidence_arm: arm
    model_path: /m.gguf
    model_vram_gib: 10.0
    np_throughput_saturation: 16
    budgets:
      - name: solo_resident
        dynamic_budget_gib: 10.0
        ceilings: {"2048": 32}
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="exceeds np_throughput_saturation"):
            lane.load_np_ceiling_policy(bad, feats=enabled)

    def test_committed_policy_respects_its_own_caps(self, policy):
        for tenant in policy.tenants.values():
            for mode_policy in tenant.modes.values():
                for budget in mode_policy.budgets:
                    for ceiling in budget.ceilings.values():
                        if ceiling is not None:
                            assert ceiling <= tenant.np_throughput_saturation


class TestServingShapeLoaderGate:
    """P2-3d: the ceiling check lives on the RESOLUTION PATH, not only in smoke.

    Stage-0's equivalent gate can be skipped by simply not running Stage-0.
    These cannot: load_serving_shape() is what stack-priors calls to produce the
    builder's real -np/-c, so a shape that fails here cannot be compiled at all.
    """

    def _with_shape(self, tmp_path: Path, np_slots: int, slot_context: int) -> Path:
        src = (
            Path(lane.__file__).resolve().parents[2]
            / "orchestration"
            / "gpu_shadow_lane_np_ceiling.yaml"
        ).read_text(encoding="utf-8")
        patched = src.replace(
            "np_slots: 8\n  slot_context_tokens: 8192",
            f"np_slots: {np_slots}\n  slot_context_tokens: {slot_context}",
        )
        assert patched != src, "serving_shape block not found — fixture is stale"
        target = tmp_path / "policy.yaml"
        target.write_text(patched, encoding="utf-8")
        return target

    def test_committed_shape_resolves(self):
        shape = lane.load_serving_shape()
        assert shape == {
            "np_slots": 8,
            "slot_context_tokens": 8192,
            "context_tokens": 65536,
        }

    def test_shape_is_not_feature_gated(self, monkeypatch):
        """Must resolve with the flag OFF — the Step-2 pipeline gates run before
        the flag is flipped, and gating this would break the compile path."""
        monkeypatch.delenv("ORCHESTRATOR_FEATURE_GPU_SHADOW_LANE", raising=False)
        assert lane.load_serving_shape()["np_slots"] == 8

    def test_refuses_shape_above_saturation(self, tmp_path: Path):
        bad = self._with_shape(tmp_path, 32, 32768)
        with pytest.raises(ValueError, match="exceeds the measured throughput saturation"):
            lane.load_serving_shape(bad)

    def test_refuses_shape_no_tenant_admits(self, tmp_path: Path):
        """np16 is within saturation, but 131072-token slots were never measured."""
        bad = self._with_shape(tmp_path, 16, 131072)
        with pytest.raises(ValueError, match="no validated operating point"):
            lane.load_serving_shape(bad)

    def test_refusal_names_the_refusing_rows(self, tmp_path: Path):
        bad = self._with_shape(tmp_path, 16, 131072)
        with pytest.raises(ValueError) as excinfo:
            lane.load_serving_shape(bad)
        message = str(excinfo.value)
        assert "qwen36_27b_stock_q8/mtp_off/phase2_resident_set" in message

    def test_accepts_a_shape_some_tenant_admits(self, tmp_path: Path):
        ok = self._with_shape(tmp_path, 16, 16384)
        assert lane.load_serving_shape(ok)["context_tokens"] == 16 * 16384

    def test_shape_admissibility_partitions_every_row(self, policy):
        admitting, refusing = lane.shape_admissibility(
            policy, np_slots=8, slot_context_tokens=8192
        )
        total = sum(
            len(mode_policy.budgets)
            for tenant in policy.tenants.values()
            for mode_policy in tenant.modes.values()
        )
        assert len(admitting) + len(refusing) == total
        assert not set(admitting) & set(refusing)


class TestAdmissionDesignProvision:
    """P2-5: D1's admission provision, pinned where it can actually drift.

    The spec is prose and the loader is code; the failure mode is one being
    edited without the other. These tests are the link.
    """

    def _spec(self) -> str:
        return (
            Path(lane.__file__).resolve().parents[2] / "docs" / "gpu-shadow-lane.md"
        ).read_text(encoding="utf-8")

    def test_priority_order_matches_the_spec(self):
        spec = self._spec()
        order = list(tenancy_mod.ADMISSION_CLASSES)
        assert order == [
            "escalations",
            "distillation_backfill",
            "shed_batch",
            "degraded_frontdoor_overflow",
        ]
        # Every reserved class name appears in the spec's admission section.
        section = spec.split("## 3. Admission policy")[1].split("## 4.")[0]
        for name in order:
            assert name in section or name.replace("_", " ") in section.lower(), name

    def test_unbuilt_classes_are_exactly_3_and_4(self):
        reserved = set(tenancy_mod.ADMISSION_CLASSES) - tenancy_mod.IMPLEMENTED_ADMISSION_CLASSES
        assert reserved == {"shed_batch", "degraded_frontdoor_overflow"}

    def test_reserved_flags_are_not_registered(self):
        """Named in the spec, deliberately absent from the flag registry — a
        flag for an unbuilt feature reads as 'someone can turn this on'."""
        from src.features import Features

        for field in ("gpu_lane_shed_batch", "gpu_lane_frontdoor_overflow"):
            assert not hasattr(Features(), field), field

    def test_no_preemption_path_exists_at_any_priority(self):
        """§3.2: priority orders admission, never eviction."""
        item = lease.LaneLease(lane="gpu_shadow_lane", regions=frozenset({"q3"}), device=None)
        with pytest.raises(lease.LaneLeaseError):
            item.force_release()
        source = Path(lease.__file__).read_text(encoding="utf-8")
        for forbidden in ("SIGKILL", "SIGTERM", "os.kill", "terminate("):
            assert forbidden not in source, forbidden


class TestLaunchPlanIsDataDriven:
    def test_argv_uses_tenancy_values_not_module_constants(self, tenancy, policy):
        plan = tenancy_mod.resolve_lane_plan(
            tenancy,
            policy,
            tenant_id="qwen36_27b_stock_q8",
            budget_profile="phase2_resident_set",
            np_slots=8,
            slot_context_tokens=8192,
        )
        argv = list(plan.launch_argv)
        assert argv[:3] == ["taskset", "-c", "184-191"]
        assert "--spec-type" not in argv  # MTP off by default (D6)
        assert argv[argv.index("-np") + 1] == "8"
        # NOTE: "-c" appears twice — taskset's cpu-list flag and llama-server's
        # context flag. Take the LAST one, which is the server's.
        assert argv[len(argv) - 1 - argv[::-1].index("-c") + 1] == str(8 * 8192)
        assert argv[argv.index("--reasoning") + 1] == "off"
        assert argv[argv.index("--device") + 1] == "ROCm0"

    def test_mtp_tenant_emits_the_measured_spec_flags(self, tenancy, policy):
        plan = tenancy_mod.resolve_lane_plan(
            tenancy,
            policy,
            tenant_id="qwen36_35b_a3b_q8_bridge",
            budget_profile="solo_resident",
            np_slots=8,
            slot_context_tokens=2048,
        )
        argv = list(plan.launch_argv)
        assert argv[-4:] == ["--spec-type", "draft-mtp", "--spec-draft-n-max", "4"]

    def test_mtp_without_depth_is_a_programming_error(self):
        with pytest.raises(ValueError, match="draft_n_max"):
            lane.build_tenant_launch_plan(
                model_path="/m.gguf", np_slots=1, slot_context_tokens=2048, mtp=True
            )


class TestPlanRefusals:
    def test_over_ceiling_refuses(self, tenancy, policy):
        plan = tenancy_mod.resolve_lane_plan(
            tenancy,
            policy,
            tenant_id="qwen36_27b_stock_q8",
            budget_profile="phase2_resident_set",
            np_slots=16,
            slot_context_tokens=32768,
        )
        assert not plan.admissible
        assert any("exceeds the validated ceiling" in r for r in plan.refusals)

    def test_forbidden_co_residency_refuses_phase2_profile(self, tenancy, policy):
        """The A4 bridge cannot co-fit with the D2 resident set in 64 GiB."""
        plan = tenancy_mod.resolve_lane_plan(
            tenancy,
            policy,
            tenant_id="qwen36_35b_a3b_q8_bridge",
            budget_profile="solo_resident",
            np_slots=8,
            slot_context_tokens=2048,
        )
        assert plan.admissible
        assert plan.mode == lane.MODE_MTP_ON

    def test_proposal_render_is_marked_not_applied(self, tenancy, policy):
        plan = tenancy_mod.resolve_lane_plan(
            tenancy,
            policy,
            tenant_id="qwen36_27b_stock_q8",
            budget_profile="phase2_resident_set",
            np_slots=8,
            slot_context_tokens=8192,
        )
        text = tenancy_mod.render_registry_proposal(plan, tenancy)
        assert "NOT APPLIED" in text
        assert "frozen" in text.lower()


# ---------------------------------------------------------------------------
# P2-1 — region-lock / lease integration
# ---------------------------------------------------------------------------
class TestSmtFolding:
    def test_lane_siblings_fold_onto_physical_cores(self):
        assert lease.fold_smt_to_physical("184-191") == set(range(88, 96))

    def test_lane_occupies_region_q3(self):
        assert lease.lane_host_regions("184-191") == frozenset({"q3"})

    def test_architect_general_shares_cores_despite_no_string_overlap(self):
        """The P2-4 P1-2 blind spot, pinned as a regression test: '0-95' and
        '184-191' share no literal cpu id, but they share physical cores."""
        assert not (lease.parse_cpu_spec("0-95") & lease.parse_cpu_spec("184-191"))
        assert lease.cpuset_shares_physical_cores("0-95", "184-191") == set(range(88, 96))

    def test_q1b_quarter_shares_cores(self):
        assert lease.cpuset_shares_physical_cores("72-95,168-191", "184-191") == set(
            range(88, 96)
        )

    def test_disjoint_quarter_does_not_share(self):
        assert lease.cpuset_shares_physical_cores("0-23,96-119", "184-191") == set()

    def test_preflight_and_lease_agree_on_co_tenancy(self):
        """P2-1a: the fold math has one implementation, and this pins it.

        The probe reports the sibling CLOSURE (both hyperthreads, because an
        operator reading a blocker wants the mask that collided) while the lease
        module answers in PHYSICAL cores. Different ids, same predicate — so
        assert the predicate, across every real cpuset in the fleet plus the
        adversarial cases. If someone re-forks the math, this fails.
        """
        from scripts.server import gpu_shadow_lane_preflight as probe
        from scripts.server.stack_numa import NUMA_CONFIG

        specs = ["184-191", "88-95", "0-95", "0-191", "72-95,168-191", "0-47,96-143", "48-71"]
        for cfg in NUMA_CONFIG.values():
            for cpu_list, _port, _threads in cfg.get("instances", []):
                specs.append(cpu_list)

        for spec in specs:
            probe_says = bool(probe.folded_overlap(spec, "184-191"))
            lease_says = bool(lease.cpuset_shares_physical_cores(spec, "184-191"))
            assert probe_says == lease_says, spec

    def test_closure_and_physical_fold_are_consistent(self):
        """The closure is exactly the physical fold re-expanded to both threads."""
        from scripts.server import gpu_shadow_lane_preflight as probe

        for spec in ("184-191", "0-95", "72-95,168-191"):
            physical = lease.fold_smt_to_physical(spec)
            closure = probe.smt_fold(lease.parse_cpu_spec(spec))
            assert closure == {c for core in physical for c in (core, core + 96)}


class TestLease:
    def test_claim_refused_while_flag_off(self):
        with pytest.raises(lane.GpuShadowLaneDisabled):
            with lease.lane_claim(feats=Features(gpu_shadow_lane=False)):
                pass

    def test_empty_region_set_refuses_rather_than_taking_no_lock(self, enabled: Features):
        with pytest.raises(lease.LaneLeaseError, match="no physical cores"):
            with lease.lane_claim(host_cpuset="", feats=enabled):
                pass

    def test_revoke_drains_at_next_boundary(self):
        item = lease.LaneLease(lane="gpu_shadow_lane", regions=frozenset({"q3"}), device=None)
        assert item.accepting_work
        item.request_revoke("operator needs q3 for E8")
        # Revocation stops NEW work immediately but does not stop work in flight.
        assert not item.accepting_work
        assert item.state == lease.LEASE_REVOKING
        assert not item.overdue
        # The holder reaching its boundary is what actually releases.
        assert item.at_boundary() is True
        assert item.state == lease.LEASE_DRAINING

    def test_ignored_revocation_surfaces_as_overdue(self):
        item = lease.LaneLease(lane="gpu_shadow_lane", regions=frozenset({"q3"}), device=None)
        item.request_revoke("yield")
        item.boundaries_since_revoke = 1
        assert item.overdue

    def test_no_forcible_release_path(self):
        item = lease.LaneLease(lane="gpu_shadow_lane", regions=frozenset({"q3"}), device=None)
        with pytest.raises(lease.LaneLeaseError, match="quiesce-and-drain"):
            item.force_release()

    def test_device_lock_is_exclusive_and_not_a_cpu_region(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
        path = lease.device_lock_path("ROCm0")
        assert "cpu_region" not in path.name
        assert path.name == "gpu_device.ROCm0.lock"
        with lease.gpu_device_lock("ROCm0"):
            payload = lease.read_device_lock_payload("ROCm0")
            assert payload and payload["device"] == "ROCm0"

    def test_second_device_claim_fails_fast(self, tmp_path, monkeypatch):
        """A GPU claim must not queue behind an unrelated bench window."""
        monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
        import subprocess
        import sys
        import textwrap

        with lease.gpu_device_lock("ROCm0"):
            # A second claim from ANOTHER process must be refused immediately.
            # Same-process flock re-acquisition would succeed, so this has to
            # cross a process boundary to test anything real.
            code = textwrap.dedent(
                f"""
                import os, sys
                os.environ["ORCHESTRATOR_TMP_DIR"] = {str(tmp_path)!r}
                sys.path.insert(0, {str(Path(lane.__file__).resolve().parents[2])!r})
                from scripts.server import gpu_shadow_lane_lease as l
                try:
                    with l.gpu_device_lock("ROCm0"):
                        print("ACQUIRED")
                except l.LaneLeaseError:
                    print("REFUSED")
                """
            )
            out = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
            )
            assert "REFUSED" in out.stdout, out.stderr


# ---------------------------------------------------------------------------
# P2-3 — Stage-0 hardening
# ---------------------------------------------------------------------------
def _cpus(spec: str) -> set[int]:
    """Expand a cpuset string — a second implementation, kept out of the module
    under test so the recert expectations below are not derived from it."""
    out: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, hi = chunk.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(chunk))
    return out


_LANE = "184-191"


# The host folds logical CPU n and n+96 onto the same physical core (SMT
# siblings; 184-191 fold to 88-95). This is the machine fact the recert set is
# built on, restated here so the expectation does not come from the fold under
# test.
def _physical(spec: str) -> set[int]:
    return {cpu % 96 for cpu in _cpus(spec)}


def _lane_instances() -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """(literal-overlap, fold-only-overlap) instances, from stack_numa directly."""
    from scripts.server.stack_numa import NUMA_CONFIG

    literal: list[tuple[str, int]] = []
    folded: list[tuple[str, int]] = []
    for role, cfg in NUMA_CONFIG.items():
        for cpu_list, port, _threads in cfg.get("instances", []):
            if not (_physical(cpu_list) & _physical(_LANE)):
                continue
            if _cpus(cpu_list) & _cpus(_LANE):
                literal.append((role, port))
            else:
                folded.append((role, port))
    return literal, folded


class TestRecertSet:
    def test_recert_set_includes_the_smt_blind_spot(self):
        """Every instance that shares the lane's PHYSICAL cores without naming any
        of its logical CPUs must be in the set, flagged `physical_core_overlap`.

        Derived since 2026-08-04. This used to name architect_general as "the
        role that pins 0-95". The W1 cutover moved architect_general ONTO the
        lane (184-191), so it is now a literal `smt_sibling_overlap` entry and
        the example went stale while the mechanism did not — four other
        full-machine instances are still caught by the fold alone. Naming the
        blind spot by its DEFINITION instead of by one role is what stops that
        recurring.
        """
        _literal, folded = _lane_instances()
        assert folded, "no fold-only instance left to detect — check the topology"

        roles = stage0.recert_roles(_LANE)
        missed = {(i.role, i.port) for i in roles if i.basis == "physical_core_overlap"}
        assert set(folded) <= missed
        # ...and the fold is what a raw string check would have missed.
        for role, port in folded:
            assert (role, port) not in {
                (i.role, i.port) for i in roles if i.basis == "smt_sibling_overlap"
            }

    def test_recert_set_includes_q1b_quarters(self):
        """Every instance sharing the lane must be recertified, folded or literal.

        Derived since 2026-08-04. The old literals {8380, 8382, 8485, 8087} are
        all RETIRED ports: 8280/8380/8282/8382/8385/8485 were freed by the
        2026-07-31 "retire quarters, deploy 1 full + 2 halves" topology change
        which records that they must not be revived, and :8087 went away when
        vision_escalation became an alias on worker_vision's :8086. Re-adding
        them would mean reviving retired processes so a test has something to
        match. The property — no lane-sharing instance is omitted — is unchanged.
        """
        literal, folded = _lane_instances()
        assert literal and folded

        ports = {item.port for item in stage0.recert_roles(_LANE)}
        assert {port for _role, port in literal + folded} <= ports

    def test_recert_command_names_the_lane_and_every_contender(self):
        roles = stage0.recert_roles("184-191")
        command = stage0.recert_command(roles)
        assert "gpu_shadow_lane" in command
        for item in roles:
            assert item.role in command


class TestAttestationJudges:
    def test_health_ok(self):
        checks = stage0.judge_health(
            {"health": {"status": "ok"}, "slots": [{"is_processing": False}] * 8},
            expect_slots=8,
        )
        assert all(c.passed for c in checks)

    def test_health_slot_count_mismatch_fails(self):
        checks = stage0.judge_health(
            {"health": {"status": "ok"}, "slots": [{"is_processing": False}] * 4},
            expect_slots=8,
        )
        assert not all(c.passed for c in checks)

    def test_missing_health_is_a_failure_not_a_skip(self):
        checks = stage0.judge_health({"slots": []})
        assert any(c.name == "health.present" and not c.passed for c in checks)

    def test_affinity_physical_cores_pass_but_exact_string_fails(self):
        """88-95 is the same silicon as 184-191, so the physical check passes;
        the GPU host-thread rule is what the exact check enforces."""
        checks = stage0.judge_affinity({"cpus_allowed_list": "88-95"})
        named = {c.name: c.passed for c in checks}
        assert named["affinity.physical_cores"] is True
        assert named["affinity.exact"] is False

    def test_vram_short_fails(self):
        checks = stage0.judge_vram(
            {"total_gib": 40.0, "used_gib": 3.0, "compute_pids": []},
            model_vram_gib=26.7,
            estimated_dynamic_gib=20.4,
        )
        assert any(c.name == "vram.headroom" and not c.passed for c in checks)


class TestDeterministicSmoke:
    def test_smoke_is_green_on_committed_tables(self, tenancy, policy):
        checks = stage0.smoke_checks(tenancy, policy)
        failed = [f"{c.name}: {c.detail}" for c in checks if not c.passed]
        assert not failed, failed

    def test_serving_shape_gate_catches_drift(self, tenancy, policy, monkeypatch):
        """The compiled serving shape must be inside the ceiling table.

        P2-6's ``load_serving_shape`` validates only that np_slots is a measured
        LEVEL and the context is positive — it never consults the ceiling rows
        in the same file. So a shape like np32 x 32768 would compile into a live
        -np/-c while every tenant's ceiling refuses it (32 also exceeds the
        saturation cap of 16). This gate is what notices.
        """
        monkeypatch.setattr(
            stage0,
            "load_serving_shape",
            lambda *a, **k: {
                "np_slots": 32,
                "slot_context_tokens": 32768,
                "context_tokens": 32 * 32768,
            },
        )
        checks = stage0.smoke_checks(tenancy, policy)
        gate = next(c for c in checks if c.name == "serving_shape.within_ceiling")
        assert not gate.passed
        assert "REFUSED BY" in gate.detail

    def test_serving_shape_gate_passes_on_committed_shape(self, tenancy, policy):
        checks = stage0.smoke_checks(tenancy, policy)
        gate = next(c for c in checks if c.name == "serving_shape.within_ceiling")
        assert gate.passed, gate.detail

    def test_smoke_is_deterministic(self, tenancy, policy):
        first = [(c.name, c.passed) for c in stage0.smoke_checks(tenancy, policy)]
        second = [(c.name, c.passed) for c in stage0.smoke_checks(tenancy, policy)]
        assert first == second

    def test_smoke_runs_no_inference_and_touches_no_device(self):
        """Stage-0 must be incapable of I/O against the device or a server.

        Checked at the IMPORT level rather than by substring: the module
        legitimately mentions rocm-smi in prose (it parses rocm-smi-SHAPED
        JSON), and a substring check would have to be loosened until it stopped
        meaning anything. What matters is that it cannot spawn or connect.
        """
        import ast

        tree = ast.parse(Path(stage0.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for forbidden in ("subprocess", "socket", "requests", "httpx", "urllib", "os"):
            assert forbidden not in imported, f"stage0 must not import {forbidden}"

"""Tests for the gpu_shadow_lane scaffolding (gpu-serving-tie-in-program P0-7).

Covers: feature-flag default-off inertness in BOTH test and prod defaults, the
flag-gated np_ceiling policy loader, ceiling lookup semantics (budget-row and
context-bucket selection, null = refuse), the VRAM estimate helper, the
launch-plan builder shape (MTP OFF, measured grid argv), and the zero-coupling
witness against the production launch path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.server import gpu_shadow_lane as lane
from src.features import Features, get_features, reset_features


@pytest.fixture(autouse=True)
def _clean_features_singleton():
    reset_features()
    yield
    reset_features()


@pytest.fixture()
def enabled() -> Features:
    return Features(gpu_shadow_lane=True)


@pytest.fixture()
def policy(enabled: Features) -> lane.NpCeilingPolicy:
    return lane.load_np_ceiling_policy(feats=enabled)


# ---------------------------------------------------------------------------
# Flag defaults + inertness
# ---------------------------------------------------------------------------
class TestFlagInertness:
    def test_default_off_in_test_defaults(self):
        assert Features().gpu_shadow_lane is False
        assert get_features().gpu_shadow_lane is False

    def test_default_off_in_prod_defaults(self):
        assert get_features(production=True).gpu_shadow_lane is False

    def test_env_var_enables(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_FEATURE_GPU_SHADOW_LANE", "1")
        assert get_features().gpu_shadow_lane is True

    def test_loader_refuses_when_flag_off(self):
        with pytest.raises(lane.GpuShadowLaneDisabled):
            lane.load_np_ceiling_policy(feats=Features())

    def test_lane_enabled_reads_explicit_features(self):
        assert lane.lane_enabled(Features()) is False
        assert lane.lane_enabled(Features(gpu_shadow_lane=True)) is True

    def test_orchestrator_stack_has_no_lane_coupling(self):
        """State-A inertness witness (P2-6 rework of the P0-7 zero-string witness).

        Since the P2-4 punch-list landed, the launch layer legitimately contains
        GATED lane branches (mode "gpu_shadow_lane", tenant_role compile
        contract). Inertness is therefore witnessed STRUCTURALLY: no manifest /
        NUMA / port / server entry exists for the lane, so no gated branch can
        fire and every compile output is byte-identical to the pre-lane state.
        The registry proposal (docs/proposals/gpu-shadow-lane-registry-proposal.md)
        is the ONLY thing that may flip these assertions, at the operator-gated
        activation (State B).
        """
        from scripts.server.stack_manifest import (
            HOT_SERVERS,
            PORT_MAP,
            ROLE_LAUNCH_META,
            WARM_SERVERS,
        )
        from scripts.server.stack_numa import NUMA_CONFIG
        from src.registry.registry_compiler import (
            active_roles_from_launch_meta,
            launcher_tenant_roles,
        )

        # No launcher entry, wiring, or port for the lane.
        assert "gpu_shadow_lane" not in ROLE_LAUNCH_META
        assert not any(
            isinstance(meta, dict) and meta.get("mode") == "gpu_shadow_lane"
            for meta in ROLE_LAUNCH_META.values()
        )
        assert "gpu_shadow_lane" not in NUMA_CONFIG
        assert "gpu_shadow_lane" not in PORT_MAP
        assert lane.LANE_PORT not in PORT_MAP.values()

        # No computed server entry carries the lane mode flag or its port.
        for server in HOT_SERVERS + WARM_SERVERS:
            assert not server.get("gpu_shadow_lane")
            assert server.get("port") != lane.LANE_PORT

        # The compile contract is dormant: no tenant_role key anywhere, so the
        # active-role set (and every lean/descriptor/priors compile keyed on it)
        # is byte-identical to the pre-contract behavior.
        assert launcher_tenant_roles(ROLE_LAUNCH_META) == set()
        active = active_roles_from_launch_meta(ROLE_LAUNCH_META)
        assert "gpu_shadow_lane" not in active
        assert "coder_escalation_shadow" not in active

        # Routing stays fully uncoupled (P2-6 witness extension): the chat
        # routing decision path has zero lane references, gated or otherwise.
        routing_source = (
            Path(lane.__file__).resolve().parents[2]
            / "src/api/routes/chat_pipeline/routing_decision.py"
        ).read_text(encoding="utf-8")
        assert "gpu_shadow_lane" not in routing_source
        assert "coder_escalation_shadow" not in routing_source

    def test_no_launcher_tenant_records_in_live_priors(self):
        """The generated stack-priors artifact carries no launcher-tenant
        records while the lane is dormant (State A)."""
        from src.registry.stack_priors import launcher_tenant_role_records

        assert launcher_tenant_role_records() == {}


# ---------------------------------------------------------------------------
# Policy loading
# ---------------------------------------------------------------------------
class TestPolicyLoad:
    def test_loads_committed_policy(self, policy: lane.NpCeilingPolicy):
        assert policy.version == 1
        assert policy.lane == "gpu_shadow_lane"
        assert policy.device == "ROCm0"
        assert set(policy.tenants) == {
            "qwen36_27b_ff_q8",
            "qwen36_27b_ff_mtp_q8",
            "qwen36_27b_stock_q8",
            "qwen36_35b_a3b_q8_bridge",
        }

    def test_candidate_tenant_fields(self, policy: lane.NpCeilingPolicy):
        tenant = policy.tenants["qwen36_27b_stock_q8"]
        assert tenant.evidence_arm == "A3_ff_fable_non_mtp_q8"
        assert tenant.model_path == lane.TENANT_CANDIDATE_MODEL
        assert tenant.kv_bytes_per_token_f16 == 65536
        assert tenant.np_throughput_saturation == 16
        assert {row.name for row in tenant.budgets} == {
            "solo_resident",
            "phase2_resident_set",
        }

    def test_bridge_tenant_measured_cells_only(self, policy: lane.NpCeilingPolicy):
        tenant = policy.tenants["qwen36_35b_a3b_q8_bridge"]
        assert tenant.kv_bytes_per_token_f16 is None
        assert tenant.per_seq_overhead_gib is None

    def test_rejects_wrong_version(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "policy.yaml"
        bad.write_text("version: 2\nlane: gpu_shadow_lane\ntenants: {}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="unsupported version"):
            lane.load_np_ceiling_policy(bad, feats=enabled)

    def test_rejects_wrong_lane(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "policy.yaml"
        bad.write_text("version: 1\nlane: other\ntenants: {}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="lane"):
            lane.load_np_ceiling_policy(bad, feats=enabled)

    def test_rejects_unmeasured_np_level(self, tmp_path: Path, enabled: Features):
        bad = tmp_path / "policy.yaml"
        bad.write_text(
            """
version: 1
lane: gpu_shadow_lane
tenants:
  t:
    evidence_arm: arm
    model_path: /nonexistent
    model_vram_gib: 1.0
    np_throughput_saturation: 16
    budgets:
      - name: r
        dynamic_budget_gib: 10.0
        ceilings: {"2048": 7}
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="not a measured np level"):
            lane.load_np_ceiling_policy(bad, feats=enabled)


# ---------------------------------------------------------------------------
# Ceiling lookup semantics
# ---------------------------------------------------------------------------
class TestNpCeiling:
    def test_phase2_deep_context_drops_to_np8(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=27.0,
                slot_context_tokens=32768,
            )
            == 8
        )

    def test_phase2_mid_context_np16(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=27.0,
                slot_context_tokens=8192,
            )
            == 16
        )

    def test_solo_budget_allows_np16_at_32k(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=37.3,
                slot_context_tokens=32768,
            )
            == 16
        )

    def test_intermediate_context_uses_next_bucket_up(self, policy):
        # 4096 has no bucket; conservative selection uses the 8192 bucket.
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=27.0,
                slot_context_tokens=4096,
            )
            == 16
        )

    def test_budget_between_rows_picks_lower_row(self, policy):
        # 30 GiB available: phase2 row (27.0) applies, solo row (37.3) does not.
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=30.0,
                slot_context_tokens=32768,
            )
            == 8
        )

    def test_budget_below_all_rows_refuses(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=20.0,
                slot_context_tokens=2048,
            )
            is None
        )

    def test_context_above_largest_bucket_refuses(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_27b_stock_q8",
                dynamic_budget_gib=37.3,
                slot_context_tokens=65536,
            )
            is None
        )

    def test_bridge_unmeasured_depth_refuses(self, policy):
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_35b_a3b_q8_bridge",
                dynamic_budget_gib=28.8,
                slot_context_tokens=16384,
                mode=lane.MODE_MTP_ON,
            )
            is None
        )

    def test_bridge_measured_depth_np16(self, policy):
        # The bridge grid ran MTP ON at n_max=4, so its ceilings live under
        # mtp_on. Asking for the measured cell in the right mode answers.
        assert (
            lane.np_ceiling(
                policy,
                "qwen36_35b_a3b_q8_bridge",
                dynamic_budget_gib=28.8,
                slot_context_tokens=2048,
                mode=lane.MODE_MTP_ON,
            )
            == 16
        )

    def test_bridge_refuses_mtp_off_entirely(self, policy):
        """The bridge was never measured with MTP off, so every MTP-off query
        refuses rather than borrowing the MTP-on frontier."""
        for context in (2048, 8192, 16384, 32768):
            assert (
                lane.np_ceiling(
                    policy,
                    "qwen36_35b_a3b_q8_bridge",
                    dynamic_budget_gib=28.8,
                    slot_context_tokens=context,
                    mode=lane.MODE_MTP_OFF,
                )
                is None
            )

    def test_unknown_tenant_raises(self, policy):
        with pytest.raises(KeyError):
            lane.np_ceiling(
                policy, "nope", dynamic_budget_gib=27.0, slot_context_tokens=2048
            )

    def test_nonpositive_context_raises(self, policy):
        with pytest.raises(ValueError):
            lane.np_ceiling(
                policy, "qwen36_27b_stock_q8", dynamic_budget_gib=27.0, slot_context_tokens=0
            )


# ---------------------------------------------------------------------------
# VRAM estimate + launch plan
# ---------------------------------------------------------------------------
class TestEstimateAndPlan:
    def test_estimate_np8_32k(self, policy):
        tenant = policy.tenants["qwen36_27b_stock_q8"]
        estimate = lane.estimated_dynamic_gib(
            tenant, np_slots=8, slot_context_tokens=32768
        )
        # 16 GiB KV + 8*0.15 state + 2.0 reserve
        assert estimate == pytest.approx(19.2, abs=0.01)

    def test_estimate_none_without_kv_model(self, policy):
        tenant = policy.tenants["qwen36_35b_a3b_q8_bridge"]
        assert (
            lane.estimated_dynamic_gib(tenant, np_slots=8, slot_context_tokens=2048)
            is None
        )

    def test_launch_plan_matches_measured_shape(self):
        argv = lane.build_tenant_launch_plan(
            model_path="/models/m.gguf", np_slots=8, slot_context_tokens=8192
        )
        joined = " ".join(argv)
        assert argv[:3] == ["taskset", "-c", "184-191"]
        assert str(lane.LANE_BINARY) in joined
        assert "-np 8" in joined
        assert "-c 65536" in joined  # np * per-slot context
        assert "--device ROCm0" in joined
        assert "-fa on" in joined
        assert "--reasoning off" in joined
        assert "-t 8" in joined and "-tb 8" in joined
        # D6: MTP OFF — no speculative/draft flags in the default lane shape.
        assert "--draft" not in joined and "model-draft" not in joined
        assert f"--port {lane.LANE_PORT}" in joined

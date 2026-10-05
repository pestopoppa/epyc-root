"""P0-1/P0-2 witnesses: the launcher-tenant compile contract + gated mode plumbing.

gpu-serving-tie-in P2-6 (landing the P2-4 adversarial-review punch list).

Contract under test: a ``launcher_only`` ROLE_LAUNCH_META entry may name a
registry role via the optional ``tenant_role`` meta key. When (and ONLY when)
the key is present, the named role compiles through lean-registry /
descriptor / stack-prior stages and yields a launch record resolvable by
``orchestrator_stack._stack_prior_launch`` — without ever being classified
``live_stack`` or joining the start-set. With the key absent (production
today), every stage's output is identical to the pre-contract behavior.

Every stage gets its own witness:
  1. registry_compiler.active_roles_from_launch_meta / launcher_tenant_roles
  2. compile_lean (lean registry projection, byte-for-byte inert without key)
  3. stack_commands._descriptor_active_roles + stack_change_pipeline roles
  4. stack_priors compile (deployment_status=launcher_tenant, serving shape
     from the np_ceiling serving_shape block — never CPU-mode defaults)
  5. orchestrator_stack._stack_prior_launch fallback + the gpu_shadow_lane
     builder / start_server dispatch (P0-2), gated + inert
  6. stack_prewarm lane exclusion (P2-4)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.registry.registry_compiler import (
    active_roles_from_launch_meta,
    compile_lean,
    launcher_tenant_roles,
)

TENANT = "coder_escalation_shadow"

LANE_META_WITHOUT_KEY = {
    "frontdoor": {"tier": "hot", "mode": "default"},
    "eval_batch_frontdoor": {
        "tier": "warm",
        "mode": "eval_batch_frontdoor",
        "launcher_only": True,
    },
}

LANE_META_WITH_KEY = {
    "frontdoor": {"tier": "hot", "mode": "default"},
    "gpu_shadow_lane": {
        "tier": "warm",
        "mode": "gpu_shadow_lane",
        "launcher_only": True,
        "tenant_role": TENANT,
    },
}

FIXTURE_MASTER = {
    "runtime_defaults": {"timeouts": {"roles": {"frontdoor": 30}}},
    "roles": {
        "frontdoor": {"tier": "A", "model": {"name": "M", "path": "/m/frontdoor.gguf"}},
        TENANT: {
            "tier": "B",
            "port": 18100,
            "model": {
                "name": "Qwen3.6-27B",
                "path": "/mnt/raid0/llm/models/Qwen_Qwen3.6-27B-Q8_0.gguf",
                "quant": "Q8_0",
                "kv_cache": {"type_k": "f16", "type_v": "f16"},
            },
            "memory": {"residency": "warm"},
            "server": {
                "endpoint": "http://localhost:18100",
                "device": "ROCm0",
                "reasoning": "off",
                "runtime_requirements": {
                    "binary_dir": "/mnt/raid0/llm/llama.cpp/build-hip/bin",
                    "ld_library_path": ["/mnt/raid0/llm/llama.cpp/build-hip/bin"],
                },
            },
        },
    },
    "server_mode": {"frontdoor": {"port": 8070, "model": "frontdoor.gguf"}},
}


# ---------------------------------------------------------------------------
# Stage 1: launch-meta role extraction
# ---------------------------------------------------------------------------
class TestLaunchMetaContract:
    def test_key_absent_matches_pre_contract_set(self):
        active = active_roles_from_launch_meta(LANE_META_WITHOUT_KEY)
        assert active == {"frontdoor"}
        assert launcher_tenant_roles(LANE_META_WITHOUT_KEY) == set()

    def test_key_present_adds_tenant_not_launcher(self):
        active = active_roles_from_launch_meta(LANE_META_WITH_KEY)
        assert active == {"frontdoor", TENANT}
        assert "gpu_shadow_lane" not in active
        assert launcher_tenant_roles(LANE_META_WITH_KEY) == {TENANT}

    def test_tenant_role_ignored_on_non_launcher_entries(self):
        meta = {"frontdoor": {"tier": "hot", "mode": "default", "tenant_role": "x"}}
        assert launcher_tenant_roles(meta) == set()
        assert active_roles_from_launch_meta(meta) == {"frontdoor"}

    def test_production_meta_is_dormant(self):
        from scripts.server.stack_manifest import ROLE_LAUNCH_META

        assert launcher_tenant_roles(ROLE_LAUNCH_META) == set()


# ---------------------------------------------------------------------------
# Stage 2: lean registry projection
# ---------------------------------------------------------------------------
class TestLeanCompile:
    def _write_master(self, tmp_path: Path) -> Path:
        master = tmp_path / "master.yaml"
        master.write_text(yaml.safe_dump(FIXTURE_MASTER), encoding="utf-8")
        return master

    def test_key_absent_lean_is_byte_identical_to_pre_contract(self, tmp_path):
        master = self._write_master(tmp_path)
        active = active_roles_from_launch_meta(LANE_META_WITHOUT_KEY)
        lean = compile_lean(master, active)
        # Pre-contract semantics reproduced inline: launcher_only skipped,
        # aliases included — no tenant additions.
        legacy_active = {"frontdoor"}
        legacy = compile_lean(master, legacy_active)
        assert yaml.safe_dump(lean, sort_keys=True) == yaml.safe_dump(
            legacy, sort_keys=True
        )
        assert TENANT not in lean["roles"]

    def test_key_present_projects_tenant_role(self, tmp_path):
        master = self._write_master(tmp_path)
        lean = compile_lean(master, active_roles_from_launch_meta(LANE_META_WITH_KEY))
        assert TENANT in lean["roles"]
        assert lean["roles"][TENANT]["model"]["kv_cache"] == {
            "type_k": "f16",
            "type_v": "f16",
        }
        # The launcher process identity itself never becomes a registry role.
        assert "gpu_shadow_lane" not in lean["roles"]


# ---------------------------------------------------------------------------
# Stage 3: descriptor + pipeline role sets
# ---------------------------------------------------------------------------
class TestDescriptorRoleSets:
    def test_descriptor_active_roles_includes_tenant_only_with_key(self, monkeypatch):
        from scripts.server import stack_commands

        monkeypatch.setattr(stack_commands, "ROLE_LAUNCH_META", LANE_META_WITHOUT_KEY)
        assert stack_commands._descriptor_active_roles() == {"frontdoor"}

        monkeypatch.setattr(stack_commands, "ROLE_LAUNCH_META", LANE_META_WITH_KEY)
        assert stack_commands._descriptor_active_roles() == {"frontdoor", TENANT}

    def test_pipeline_manifest_roles_include_tenant_only_with_key(self, monkeypatch):
        import scripts.server.stack_manifest as stack_manifest
        from scripts.registry.stack_change_pipeline import _roles_from_stack_manifest

        monkeypatch.setattr(stack_manifest, "ROLE_LAUNCH_META", LANE_META_WITHOUT_KEY)
        roles = _roles_from_stack_manifest()
        assert TENANT not in roles

        monkeypatch.setattr(stack_manifest, "ROLE_LAUNCH_META", LANE_META_WITH_KEY)
        roles = _roles_from_stack_manifest()
        assert TENANT in roles


# ---------------------------------------------------------------------------
# Stage 4: stack-priors compile (launcher_tenant record + serving shape)
# ---------------------------------------------------------------------------
FIXTURE_DESCRIPTORS = {
    "models": [
        {
            "model_id": "qwen36-27b-dense-q8_0",
            "display_name": "Qwen3.6-27B Q8_0 (GPU shadow tenant)",
            "family": "qwen36",
            "quant": "Q8_0",
            "mem_gb": 28.7,
            "role_bindings": {"roles": [TENANT]},
            "acceleration": {},
            "known_gaps": [],
        }
    ]
}


@pytest.fixture()
def priors_fixture_paths(tmp_path: Path) -> tuple[Path, Path]:
    registry = tmp_path / "registry.yaml"
    registry.write_text(yaml.safe_dump(FIXTURE_MASTER), encoding="utf-8")
    descriptors = tmp_path / "descriptors.yaml"
    descriptors.write_text(yaml.safe_dump(FIXTURE_DESCRIPTORS), encoding="utf-8")
    return registry, descriptors


def _patched_lane_manifest(monkeypatch):
    import scripts.server.stack_manifest as stack_manifest

    monkeypatch.setattr(stack_manifest, "ROLE_LAUNCH_META", LANE_META_WITH_KEY)
    monkeypatch.setattr(
        stack_manifest,
        "PORT_MAP",
        {**stack_manifest.PORT_MAP, "gpu_shadow_lane": 18100},
    )


class TestStackPriorsCompile:
    def _compile_tenant_record(self, priors_fixture_paths, monkeypatch):
        from src.registry.stack_priors import compile_stack_priors

        registry, descriptors = priors_fixture_paths
        _patched_lane_manifest(monkeypatch)
        priors = compile_stack_priors(
            registry_path=registry,
            descriptor_path=descriptors,
            active_roles={TENANT},
            allow_incomplete=True,
        )
        return priors["roles"][TENANT]

    def test_tenant_record_is_launcher_tenant_not_live(
        self, priors_fixture_paths, monkeypatch
    ):
        record = self._compile_tenant_record(priors_fixture_paths, monkeypatch)
        assert record["deployment_status"] == "launcher_tenant"

    def test_tenant_launch_record_matches_proposal_checklist(
        self, priors_fixture_paths, monkeypatch
    ):
        record = self._compile_tenant_record(priors_fixture_paths, monkeypatch)
        launch = record["serving"]["launch"]
        runtime = launch["runtime"]
        cache = runtime["cache"]
        flags = runtime["flags"]

        # Serving shape flows from the np_ceiling serving_shape block (P0-1c):
        # -np 8 x 8192-token slots => total context 65536. NOT the CPU-mode
        # defaults (SERIAL_ROLES->2 slots / 32768 ctx).
        assert cache["slots"] == 8
        assert cache["context_tokens"] == 65536
        assert cache["kv_type_k"] == "f16"
        assert cache["kv_type_v"] == "f16"
        assert cache["mlock"] is False
        assert cache["slot_save_path"] is None

        assert launch["requirements"]["model_path"] == (
            "/mnt/raid0/llm/models/Qwen_Qwen3.6-27B-Q8_0.gguf"
        )
        assert runtime["binary_path"] == (
            "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server"
        )
        assert runtime["env_policy"] == "binary_override_strip_ggml"
        assert runtime["kmp_blocktime"] == 10
        assert flags["device"] == "ROCm0"
        assert flags["reasoning"] == "off"
        assert flags["spec"]["enabled"] is False  # D6: MTP OFF, no spec args

    def test_missing_serving_shape_is_refused_not_defaulted(
        self, priors_fixture_paths, monkeypatch
    ):
        import src.registry.stack_priors as stack_priors

        monkeypatch.setattr(
            stack_priors, "_gpu_shadow_lane_serving_shape", lambda: None
        )
        record = self._compile_tenant_record(priors_fixture_paths, monkeypatch)
        cache = record["serving"]["launch"]["runtime"]["cache"]
        assert cache["slots"] is None  # never the SERIAL_ROLES/2-slot default
        assert any(
            "launcher-tenant serving shape" in gap for gap in record["known_gaps"]
        )

    def test_key_absent_compile_has_no_tenant_record(
        self, priors_fixture_paths, monkeypatch
    ):
        import scripts.server.stack_manifest as stack_manifest
        from src.registry.stack_priors import compile_stack_priors

        registry, descriptors = priors_fixture_paths
        monkeypatch.setattr(stack_manifest, "ROLE_LAUNCH_META", LANE_META_WITHOUT_KEY)
        priors = compile_stack_priors(
            registry_path=registry,
            descriptor_path=descriptors,
            active_roles={TENANT},
            allow_incomplete=True,
        )
        record = priors["roles"][TENANT]
        # Without the meta key the role is a plain benchmark candidate: no
        # launcher-tenant classification, no synthesized launch entries.
        assert record["deployment_status"] == "benchmark_or_candidate"
        assert record["serving"]["launch"]["entries"] == []

    def test_production_manifest_synthesizes_no_tenants(self):
        from src.registry.stack_priors import _stack_manifest_info

        _aliases, stack_roles = _stack_manifest_info()
        assert not any(
            isinstance(cfg, dict) and cfg.get("launcher_only_tenant")
            for cfg in stack_roles.values()
        )


# ---------------------------------------------------------------------------
# Stage 5: artifact accessors + _stack_prior_launch + gated builder (P0-2)
# ---------------------------------------------------------------------------
def _artifact_with(records: dict) -> dict:
    return {"stack_priors_version": 4, "roles": records}


def _tenant_record(model_path: str = "/models/tenant.gguf") -> dict:
    return {
        "role": TENANT,
        "deployment_status": "launcher_tenant",
        "serving": {
            "launch": {
                "requirements": {"model_path": model_path},
                "runtime": {
                    "binary_path": "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server",
                    "binary_dir": "/mnt/raid0/llm/llama.cpp/build-hip/bin",
                    "ld_library_path": ["/mnt/raid0/llm/llama.cpp/build-hip/bin"],
                    "cache": {
                        "slots": 8,
                        "context_tokens": 65536,
                        "kv_type_k": "f16",
                        "kv_type_v": "f16",
                    },
                    "flags": {"device": "ROCm0", "reasoning": "off"},
                },
            }
        },
    }


class TestLaunchResolution:
    def test_accessor_segregation(self, tmp_path):
        from src.registry.stack_priors import (
            launcher_tenant_role_records,
            live_stack_role_records,
        )

        artifact = tmp_path / "stack_priors.yaml"
        records = {
            TENANT: _tenant_record(),
            "frontdoor": {"role": "frontdoor", "deployment_status": "live_stack"},
        }
        artifact.write_text(yaml.safe_dump(_artifact_with(records)), encoding="utf-8")

        live = live_stack_role_records(artifact)
        tenants = launcher_tenant_role_records(artifact)
        assert set(live) == {"frontdoor"}
        assert set(tenants) == {TENANT}

    def test_stack_prior_launch_resolves_tenant_record(self, tmp_path, monkeypatch):
        from scripts.server import orchestrator_stack

        artifact = tmp_path / "stack_priors.yaml"
        artifact.write_text(
            yaml.safe_dump(_artifact_with({TENANT: _tenant_record()})),
            encoding="utf-8",
        )
        monkeypatch.setattr(orchestrator_stack, "STACK_PRIORS_PATH", artifact)

        requirements, runtime = orchestrator_stack._stack_prior_launch(TENANT)
        assert requirements["model_path"] == "/models/tenant.gguf"
        assert runtime["cache"]["slots"] == 8

    def test_live_record_wins_name_collision(self, tmp_path, monkeypatch):
        from scripts.server import orchestrator_stack

        live = _tenant_record("/models/live.gguf")
        live["deployment_status"] = "live_stack"
        # An artifact can only hold one record per name; witness precedence by
        # confirming a live-classified record resolves through the live path.
        artifact = tmp_path / "stack_priors.yaml"
        artifact.write_text(
            yaml.safe_dump(_artifact_with({TENANT: live})), encoding="utf-8"
        )
        monkeypatch.setattr(orchestrator_stack, "STACK_PRIORS_PATH", artifact)
        requirements, _runtime = orchestrator_stack._stack_prior_launch(TENANT)
        assert requirements["model_path"] == "/models/live.gguf"

    def test_unknown_role_still_returns_empty(self, tmp_path, monkeypatch):
        from scripts.server import orchestrator_stack

        artifact = tmp_path / "stack_priors.yaml"
        artifact.write_text(yaml.safe_dump(_artifact_with({})), encoding="utf-8")
        monkeypatch.setattr(orchestrator_stack, "STACK_PRIORS_PATH", artifact)
        assert orchestrator_stack._stack_prior_launch("nope") == ({}, {})


class TestGpuShadowLaneBuilder:
    @pytest.fixture()
    def resolved(self, tmp_path, monkeypatch):
        from scripts.server import orchestrator_stack

        artifact = tmp_path / "stack_priors.yaml"
        artifact.write_text(
            yaml.safe_dump(
                _artifact_with(
                    {TENANT: _tenant_record("/mnt/raid0/llm/models/Qwen_Qwen3.6-27B-Q8_0.gguf")}
                )
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(orchestrator_stack, "STACK_PRIORS_PATH", artifact)
        # Emulate the activation-state NUMA entry (proposal §2) so the builder
        # resolves the lane's -t 8; production NUMA_CONFIG has no entry.
        monkeypatch.setattr(
            orchestrator_stack,
            "NUMA_CONFIG",
            {
                **orchestrator_stack.NUMA_CONFIG,
                "gpu_shadow_lane": {"instances": [("184-191", 18100, 8)], "mlock": False},
            },
        )
        return orchestrator_stack

    def test_builder_consumes_priors_shape_and_lane_flags(self, resolved):
        cmd = resolved.build_server_command(None, 18100, gpu_shadow_lane_mode=True)
        joined = " ".join(cmd)
        assert cmd[0] == "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server"
        assert "-m /mnt/raid0/llm/models/Qwen_Qwen3.6-27B-Q8_0.gguf" in joined
        assert "--port 18100" in joined
        assert "-np 8" in joined
        assert "-c 65536" in joined
        assert "--device ROCm0" in joined
        assert "-ngl all" in joined
        assert "-fa on" in joined
        assert "-t 8" in joined and "-tb 8" in joined
        assert "-ctk f16" in joined and "-ctv f16" in joined
        assert "--reasoning off" in joined
        # D6: MTP OFF — no speculative args; CPU-only device guard must not
        # have overridden the lane device.
        assert "--spec-type" not in joined
        assert "-md" not in cmd
        assert "--device none" not in joined

    def test_builder_matches_reference_launch_plan_shape(self, resolved):
        """Eyeball-parity witness against the lane module's reference argv."""
        from scripts.server.gpu_shadow_lane import build_tenant_launch_plan

        cmd = resolved.build_server_command(None, 18100, gpu_shadow_lane_mode=True)
        plan = build_tenant_launch_plan(
            model_path="/mnt/raid0/llm/models/Qwen_Qwen3.6-27B-Q8_0.gguf",
            np_slots=8,
            slot_context_tokens=8192,
        )
        # The reference plan carries a `taskset -c <cpuset>` prefix (the
        # launcher applies pinning via _numa_prefix instead) — strip it so the
        # `-c` lookup below hits llama-server's context flag, not taskset's.
        plan = plan[3:]

        def flag_value(argv, flag):
            return argv[argv.index(flag) + 1] if flag in argv else None

        for flag in ("-m", "-np", "-c", "-t", "-tb", "-b", "-ub", "-ctk", "-ctv",
                     "--device", "--port", "--reasoning"):
            assert flag_value(cmd, flag) == flag_value(plan, flag), flag

    def test_dispatch_and_start_server_accept_lane_kwarg(self):
        import inspect

        from scripts.server import orchestrator_stack

        assert (
            "gpu_shadow_lane_mode"
            in inspect.signature(orchestrator_stack.build_server_command).parameters
        )
        assert (
            "gpu_shadow_lane_mode"
            in inspect.signature(orchestrator_stack.start_server).parameters
        )


# ---------------------------------------------------------------------------
# Stage 6: prewarm exclusion (P2-4)
# ---------------------------------------------------------------------------
class TestPrewarmExclusion:
    def test_lane_server_never_prewarmed(self):
        from scripts.server.stack_prewarm import collect_targets

        def _explode(*_a, **_k):  # build_command must not run for the lane
            raise AssertionError("build_command called for gpu_shadow_lane server")

        targets = collect_targets(
            [{"port": 18100, "roles": ["gpu_shadow_lane"], "gpu_shadow_lane": True}],
            _explode,
            registry=None,
        )
        assert targets == {}

    def test_non_lane_servers_unaffected(self, tmp_path):
        from scripts.server.stack_prewarm import collect_targets

        gguf = tmp_path / "m.gguf"
        gguf.write_bytes(b"x" * 16)

        def _build(*_a, **_k):
            return ["llama-server", "-m", str(gguf)]

        targets = collect_targets(
            [{"port": 8070, "roles": ["frontdoor"]}], _build, registry=None
        )
        assert len(targets) == 1


# ---------------------------------------------------------------------------
# Serving-shape loader (P0-1c data source)
# ---------------------------------------------------------------------------
class TestServingShape:
    def test_committed_policy_shape(self):
        from scripts.server.gpu_shadow_lane import load_serving_shape

        shape = load_serving_shape()
        assert shape == {
            "np_slots": 8,
            "slot_context_tokens": 8192,
            "context_tokens": 65536,
        }

    def test_missing_block_refuses(self, tmp_path):
        from scripts.server.gpu_shadow_lane import load_serving_shape

        bad = tmp_path / "policy.yaml"
        bad.write_text("version: 1\nlane: gpu_shadow_lane\ntenants: {}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="serving_shape"):
            load_serving_shape(bad)

    def test_invalid_np_refuses(self, tmp_path):
        from scripts.server.gpu_shadow_lane import load_serving_shape

        bad = tmp_path / "policy.yaml"
        bad.write_text(
            "version: 1\nlane: gpu_shadow_lane\n"
            "serving_shape: {np_slots: 7, slot_context_tokens: 8192}\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="not a measured np level"):
            load_serving_shape(bad)

    def test_priors_helper_returns_none_on_failure(self, monkeypatch, tmp_path):
        import src.registry.stack_priors as stack_priors

        def _raise(path=None):
            raise ValueError("boom")

        import scripts.server.gpu_shadow_lane as lane

        monkeypatch.setattr(lane, "load_serving_shape", _raise)
        assert stack_priors._gpu_shadow_lane_serving_shape() is None

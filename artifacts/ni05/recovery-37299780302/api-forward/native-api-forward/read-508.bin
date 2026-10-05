"""Schema checks for the model-capability descriptor seed."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DESCRIPTOR_PATH = REPO_ROOT / "orchestration" / "model_descriptors.yaml"
REGISTRY_PATH = REPO_ROOT / "orchestration" / "model_registry.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open() as fh:
        loaded = yaml.safe_load(fh)
    assert isinstance(loaded, dict)
    return loaded


def test_descriptor_metadata_is_versioned_and_timestamped() -> None:
    descriptors = _load_yaml(DESCRIPTOR_PATH)

    assert descriptors["descriptor_version"] == 3
    compiled_at = descriptors["compiled_at"]
    assert isinstance(compiled_at, str)
    datetime.strptime(compiled_at, "%Y-%m-%dT%H:%M:%SZ")
    assert descriptors["model_id_policy"]["invariant"].endswith("never by role name")


def test_model_records_are_unique_and_not_role_keys() -> None:
    descriptors = _load_yaml(DESCRIPTOR_PATH)
    registry = _load_yaml(REGISTRY_PATH)
    role_names = set((registry.get("roles") or {}).keys())
    server_role_names = set(
        key for key, value in (registry.get("server_mode") or {}).items() if isinstance(value, dict)
    )

    models = descriptors["models"]
    model_ids = [model["model_id"] for model in models]

    assert len(model_ids) == len(set(model_ids))
    assert not set(model_ids) & role_names
    assert not set(model_ids) & server_role_names


def test_every_model_has_consumer_ready_sections() -> None:
    descriptors = _load_yaml(DESCRIPTOR_PATH)

    required_model_fields = {
        "model_id",
        "family",
        "arch",
        "params_b",
        "active_b",
        "quant",
        "mem_gb",
        "ctx_max",
        "modalities",
        "role_bindings",
        "quality",
        "speed",
        "acceleration",
        "serving",
        "known_gaps",
    }
    required_quality_fields = {"suite_vector", "source", "eval_protocol", "measured"}
    required_speed_fields = {"solo_96t_tps", "quarter_48t_tps", "prefill_tps", "source"}
    required_accel_fields = {
        "spec_type",
        "draft_compat",
        "enable_thinking",
        "thinking_control",
        "kv",
    }
    required_serving_fields = {"binary", "numa_policy", "mlock", "ports"}
    required_serving_fields.add("requirements")

    for model in descriptors["models"]:
        assert required_model_fields <= set(model), model["model_id"]
        assert required_quality_fields <= set(model["quality"]), model["model_id"]
        assert required_speed_fields <= set(model["speed"]), model["model_id"]
        assert required_accel_fields <= set(model["acceleration"]), model["model_id"]
        assert required_serving_fields <= set(model["serving"]), model["model_id"]
        assert isinstance(model["serving"]["requirements"], dict)
        assert isinstance(model["known_gaps"], list)
        assert isinstance(model["role_bindings"].get("roles"), list)


def test_vision_descriptors_expose_projector_requirements() -> None:
    """Every descriptor serving a vision role must declare its projector.

    The set under test is DERIVED from `role_bindings` — the same field the
    loaders resolve roles through — rather than from a model-id roster: the VL
    fleet gets re-modelled and consolidated between lineups (one server can
    back both vision roles), but a vision descriptor shipping without an
    `mmproj_path` would launch multimodal serving with no projector.
    """
    descriptors = _load_yaml(DESCRIPTOR_PATH)
    vision_roles = {"worker_vision", "vision_escalation"}

    vision_models = [
        model
        for model in descriptors["models"]
        if vision_roles & set(model["role_bindings"].get("roles") or [])
    ]

    assert vision_models, "no descriptor binds a vision role"
    covered_roles = {
        role
        for model in vision_models
        for role in model["role_bindings"]["roles"]
        if role in vision_roles
    }
    assert covered_roles == vision_roles

    for model in vision_models:
        mmproj = model["serving"]["requirements"].get("mmproj_path")
        assert isinstance(mmproj, str) and mmproj, model["model_id"]
        assert mmproj.endswith(".gguf"), model["model_id"]
        assert Path(mmproj).name.startswith("mmproj"), model["model_id"]


def test_shared_runtime_aliases_do_not_emit_role_server_conflicts() -> None:
    """Shared-runtime aliases bind to their HOST's descriptor, with no conflict gaps.

    2026-09-22 lineup cutover (860b0b2d): the gemma4-26B-A4B worker this test used
    to pin was RETIRED and the worker lane (worker_general / worker_math /
    toolrunner / ...) became aliases on frontdoor's :8070 process. The host, its
    model_id, the alias set and the expected alias overrides are all recomputed from
    the lean registry the descriptors compile from (``server_mode.<host>
    .shared_with``) through the compiler's own binding/identity helpers, instead of
    restating a model_id that the next lineup change would retire again.
    """
    from src.registry.model_descriptors import _model_id_from_configs, _server_for_role

    descriptors = _load_yaml(DESCRIPTOR_PATH)
    registry = _load_yaml(REGISTRY_PATH)
    server_mode = registry["server_mode"]
    roles = registry["roles"]

    conflicts = [
        model
        for model in descriptors["models"]
        if any("server" in gap and "conflict" in gap for gap in model["known_gaps"])
    ]

    assert conflicts == []

    by_model_id = {model["model_id"]: model for model in descriptors["models"]}
    worker_lane_host, _cfg, binding = _server_for_role("worker_general", server_mode)
    assert binding == "shared_with"
    checked_hosts: set[str] = set()
    for host, host_cfg in server_mode.items():
        shared = host_cfg.get("shared_with") if isinstance(host_cfg, dict) else None
        if not isinstance(shared, list):
            continue
        # Only roles the compiler actually binds through THIS host's shared_with
        # (a role with its own server_mode row binds directly, not as an alias).
        aliases = {
            alias
            for alias in shared
            if _server_for_role(alias, server_mode)[0::2] == (host, "shared_with")
        }
        if not aliases:
            continue
        host_model_id = _model_id_from_configs(host_cfg)
        assert host_model_id in by_model_id, (host, host_model_id)
        descriptor = by_model_id[host_model_id]
        bound = set(descriptor["role_bindings"]["roles"])
        assert aliases <= bound, (host, sorted(aliases - bound))
        assert not any(
            "ignored non-live role model metadata" in gap for gap in descriptor["known_gaps"]
        ), host
        # An alias that declares a DIFFERENT model is recorded as an override
        # (the shared runtime wins); one declaring the host's model is not.
        expected_ignored = set()
        for alias in aliases:
            alias_cfg = roles.get(alias)
            alias_model_id = (
                _model_id_from_configs(alias_cfg) if isinstance(alias_cfg, dict) else None
            )
            if alias_model_id and alias_model_id != host_model_id:
                expected_ignored.add(alias_model_id)
        alias_overrides = [
            override
            for override in descriptor["role_bindings"].get("alias_overrides") or []
            if override.get("role") in aliases
        ]
        assert {o.get("ignored_model_id") for o in alias_overrides} == expected_ignored, host
        checked_hosts.add(host)

    # Non-vacuous: the worker lane's host was among the hosts checked, and the
    # worker roles the old fixture named are bound to it.
    assert worker_lane_host in checked_hosts
    worker_lane = by_model_id[_model_id_from_configs(server_mode[worker_lane_host])]
    assert {"worker_general", "worker_math", "toolrunner"} <= set(
        worker_lane["role_bindings"]["roles"]
    )

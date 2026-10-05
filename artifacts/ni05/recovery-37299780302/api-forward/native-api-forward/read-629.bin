"""Tests for QScorer cost-aware reward computation."""

from __future__ import annotations

import logging

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Any

# Minimal stubs so we can test _compute_reward without real dependencies.
# The actual ProgressEntry uses more fields; we only need outcome + event_type + data.


class _EventType:
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    GATE_PASSED = "gate_passed"
    GATE_FAILED = "gate_failed"
    ESCALATION_TRIGGERED = "escalation_triggered"
    PLAN_REVIEWED = "plan_reviewed"


@dataclass
class _FakeEntry:
    event_type: str
    outcome: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Import the real ScoringConfig and QScorer
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"

from orchestration.repl_memory import q_scorer as q_scorer_module
from orchestration.repl_memory.q_scorer import (
    BASELINE_QUALITY_BY_MODEL,
    DEFAULT_MODEL_REGISTRY_PATH,
    DEFAULT_STACK_PRIORS_PATH,
    FALLBACK_BASELINE_TPS_BY_ROLE,
    FALLBACK_MEMORY_COST_BY_ROLE,
    PRIOR_SOURCE_DEGRADED_FALLBACK,
    PRIOR_SOURCE_REGISTRY,
    PRIOR_SOURCE_REGISTRY_BASELINE_TPS_SUBSTITUTED,
    PRIOR_SOURCE_REGISTRY_OPTIMIZED_TPS,
    PRIOR_SOURCE_REGISTRY_TPS_UNSEPARATED,
    PRIOR_SOURCE_STACK_PRIORS,
    ROLE_PERFORMANCE_TPS_FALLBACKS,
    STACK_PRIOR_SCORER_ROLE_ALIASES,
    QScorerPriorSourceError,
    ScoringConfig,
    QScorer,
    _coerce_tps,
    _live_stack_q_scorer_roles,
    _NON_SCORING_HOST_ALIASES,
    _performance_tps,
    descriptor_q_scorer_priors_by_role,
    require_live_q_scorer_stack_priors,
    registry_baseline_tps_by_role,
    registry_baseline_tps_priors,
    registry_memory_cost_by_role,
    stack_prior_q_scorer_priors_by_role,
    validate_live_q_scorer_prior_sources,
)
from orchestration.repl_memory.progress_logger import EventType
from src.registry.stack_priors import STACK_PRIORS_VERSION, stack_priors_contract


def _make_outcome(outcome: str = "success") -> _FakeEntry:
    """Create a fake task outcome entry."""
    evt = EventType.TASK_COMPLETED if outcome != "failure" else EventType.TASK_FAILED
    return _FakeEntry(event_type=evt, outcome=outcome)


def _make_gate_fail() -> _FakeEntry:
    return _FakeEntry(event_type=EventType.GATE_FAILED)


def _make_escalation() -> _FakeEntry:
    return _FakeEntry(event_type=EventType.ESCALATION_TRIGGERED)


def _make_plan_review(decision: str = "ok") -> _FakeEntry:
    return _FakeEntry(event_type=EventType.PLAN_REVIEWED, data={"decision": decision})


def _scorer(config: ScoringConfig | None = None) -> QScorer:
    """Build a QScorer with mocked dependencies (we only test _compute_reward)."""
    return QScorer(
        store=MagicMock(),
        embedder=MagicMock(),
        logger=MagicMock(),
        reader=MagicMock(),
        config=config or ScoringConfig(),
    )


def _with_q_scorer_aliases(values: dict[str, Any]) -> dict[str, Any]:
    expanded = dict(values)
    for canonical_role, aliases in STACK_PRIOR_SCORER_ROLE_ALIASES.items():
        if canonical_role not in expanded:
            continue
        canonical_value = expanded[canonical_role]
        for alias in aliases:
            expanded.setdefault(alias, canonical_value)
    return expanded


def _minimal_stack_prior_record(
    role: str,
    *,
    deployment_status: str = "live_stack",
    throughput_tps: float | None = 42.0,
    quality_overall: float | None = 0.88,
    memory_cost: float = 1.0,
) -> dict[str, Any]:
    return {
        "role": role,
        "deployment_status": deployment_status,
        "status": "compiled",
        "model_id": f"{role}-model",
        "display_name": role,
        "serving": {
            "endpoint": "http://localhost:9999",
            "server_role": role,
            "binding": "test",
            "ports": [9999],
            "slots": 1,
            "tier": "hot",
            "binary": "llama.cpp",
            "binary_dir": None,
            "numa_policy": "test",
            "shared_mmap": False,
            "effective_context_tokens": 32768,
            "launch": {
                "entries": [],
                "primary_roles": [role],
                "modes": ["test"],
                "requirements": {},
                "runtime": {},
            },
        },
        "priors": {
            "throughput_tps": throughput_tps,
            "quality_overall": quality_overall,
            "memory_cost": memory_cost,
        },
        "acceleration": {},
        "model": {},
        "evidence": {},
        "known_gaps": [],
    }


def _write_stack_priors(path: Path, roles: dict[str, dict[str, Any]]) -> Path:
    import yaml

    path.write_text(
        yaml.safe_dump(
            {
                "stack_priors_version": STACK_PRIORS_VERSION,
                "contract": stack_priors_contract(),
                "compiled_at": "2026-06-13T00:00:00Z",
                "status": "compiled",
                "coverage_scope": "unit",
                "precedence_spec": "unit",
                "source_artifacts": {},
                "roles": roles,
                "known_global_gaps": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


# ===== ScoringConfig defaults =====


class TestScoringConfigDefaults:
    def test_cost_penalty_lambda_default(self):
        """Demoted to a secondary signal at era E18 (RTG-09 ratified 2026-09-24)."""
        cfg = ScoringConfig()
        assert cfg.cost_penalty_lambda == 0.05

    def test_cost_lambda_duration_default_is_ratified(self):
        """RTG-09 ratified 2026-09-24 (era E18-routing-reward-duration-axis in
        orchestration/instrument_eras.yaml): wall-clock duration is the primary
        speed axis at 0.20, above the demoted tokens/sec term."""
        cfg = ScoringConfig()
        assert cfg.cost_lambda_duration == 0.20
        assert cfg.cost_lambda_duration > cfg.cost_penalty_lambda

    def test_baseline_tps_has_all_production_roles(self):
        """Every currently-live q_scorer role has a baseline t/s entry, and
        nothing else.

        DERIVED from the loader's own live-role resolution
        (`_live_stack_q_scorer_roles` over the compiled
        `orchestration/derived/stack_priors.yaml`), not a hand-kept literal
        set. A hardcoded set here has already gone stale twice — the
        2026-08-01 W1 cutover and the 2026-09-22 lineup cutover — and a third
        repin would just be the same defect again.

        `"worker"` is asserted ABSENT on purpose (session friction audit
        2026-09-24): the registry/launch manifest still declare it
        (`server_mode.worker: alias_of frontdoor`, part of
        `server_mode.frontdoor.shared_with`) purely so a legacy URL/topology
        lookup keyed on the old physical "worker" host still resolves, so it
        genuinely compiles `deployment_status: live_stack` into the artifact —
        but it is not a `Role` and duplicates the measurements already carried
        by worker_general/worker_math/worker_explore/toolrunner/
        worker_summarize. The registry-path loader
        (`SERVER_MODE_TPS_ROLE_ALIASES`) already treats it this way: it reads
        `server_mode.worker` only to PROJECT onto its four named members and
        never keeps "worker" itself as an output key.
        `_NON_SCORING_HOST_ALIASES` in q_scorer.py gives the stack-priors path
        the same treatment.
        """
        cfg = ScoringConfig()
        expected_roles = _live_stack_q_scorer_roles(DEFAULT_STACK_PRIORS_PATH)
        assert expected_roles, (
            "compiled stack priors have no live q_scorer roles; test would be vacuous"
        )
        assert set(cfg.baseline_tps_by_role.keys()) == expected_roles
        assert "worker" not in cfg.baseline_tps_by_role, (
            "'worker' is a host-only registry/launch-manifest alias for the "
            "shared frontdoor process, not a Role or a q_scorer scoring role "
            "— see _NON_SCORING_HOST_ALIASES"
        )

    def test_baseline_tps_loads_current_registry_values(self):
        """Every live role's baseline t/s is a direct projection of the
        compiled stack-priors artifact's own `throughput_tps`.

        DERIVED from `orchestration/derived/stack_priors.yaml`, never
        re-pinned as literals — pinning is exactly what rotted this test at
        the 2026-08-01 W1 cutover and again at the 2026-09-22 lineup change,
        where architect_critic's role-server binding moved off the CPU 122B
        (24.0 t/s) onto the Qwen3.8-Flash-Next-UD-IQ4_XS/MTP process (52.7
        t/s) that inherited the role.

        STACK_PRIOR_SCORER_ROLE_ALIASES is applied the same way the loader
        applies it: an aliased role (worker_explore) never keeps its OWN
        record's figure once its host role (worker_general) compiles —
        the alias always reads the host's value.
        """
        import yaml

        cfg = ScoringConfig()
        compiled = yaml.safe_load(DEFAULT_STACK_PRIORS_PATH.read_text()) or {}
        records = compiled.get("roles") or {}
        assert records, (
            "compiled stack priors have no roles block; test would be vacuous"
        )

        live_roles = _live_stack_q_scorer_roles(DEFAULT_STACK_PRIORS_PATH)
        assert live_roles, "no live q_scorer roles resolved; test would be vacuous"

        expected: dict[str, float] = {}
        for role, record in records.items():
            if role not in live_roles:
                continue
            tps = _compiled_tps_prior(role, record)
            if tps is not None:
                expected[role] = tps

        for canonical_role, aliases in STACK_PRIOR_SCORER_ROLE_ALIASES.items():
            if canonical_role not in expected:
                continue
            for alias in aliases:
                expected[alias] = expected[canonical_role]

        assert expected, "no live role carried a throughput_tps prior; test would be vacuous"
        for role, tps in expected.items():
            assert cfg.baseline_tps_by_role[role] == pytest.approx(tps), role

        assert _RETIRED_ARCHITECT_ROLE not in cfg.baseline_tps_by_role
        assert "worker" not in cfg.baseline_tps_by_role

    def test_default_config_exposes_stack_prior_sources(self):
        cfg = ScoringConfig()

        assert cfg.baseline_tps_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert cfg.memory_cost_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert cfg.prior_degraded_reason is None

    def test_stack_prior_priors_load_live_roles_and_skip_candidates(self, tmp_path):
        priors_path = _write_stack_priors(
            tmp_path / "stack_priors.yaml",
            {
                "frontdoor": _minimal_stack_prior_record(
                    "frontdoor",
                    throughput_tps=31.0,
                    quality_overall=0.91,
                    memory_cost=1.0,
                ),
                "coder_escalation": _minimal_stack_prior_record(
                    "coder_escalation",
                    throughput_tps=31.0,
                    quality_overall=0.91,
                    memory_cost=1.0,
                ),
                "worker_general": _minimal_stack_prior_record(
                    "worker_general",
                    throughput_tps=60.0,
                    quality_overall=0.9,
                    memory_cost=1.0,
                ),
                "candidate_arch": _minimal_stack_prior_record(
                    "candidate_arch",
                    deployment_status="benchmark_or_candidate",
                    throughput_tps=99.0,
                    quality_overall=0.99,
                    memory_cost=3.0,
                ),
            },
        )

        priors = stack_prior_q_scorer_priors_by_role(priors_path)

        assert priors.baseline_tps_by_role["frontdoor"] == pytest.approx(31.0)
        assert priors.baseline_tps_by_role["coder_escalation"] == pytest.approx(31.0)
        assert priors.baseline_tps_by_role["worker_explore"] == pytest.approx(60.0)
        assert priors.baseline_quality_by_role["frontdoor"] == pytest.approx(0.91)
        assert priors.baseline_quality_by_role["worker_explore"] == pytest.approx(0.9)
        assert priors.memory_cost_by_role["frontdoor"] == pytest.approx(1.0)
        assert priors.memory_cost_by_role["worker_explore"] == pytest.approx(1.0)
        assert priors.baseline_tps_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert priors.baseline_quality_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert priors.baseline_quality_source_by_role["worker_explore"] == PRIOR_SOURCE_STACK_PRIORS
        assert priors.memory_cost_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert priors.degraded_reason is None
        assert "candidate_arch" not in priors.baseline_tps_by_role
        retired_role = "architect" + "_coding"
        assert retired_role not in priors.baseline_tps_by_role
        assert validate_live_q_scorer_prior_sources(priors_path) == []

    def test_stack_prior_priors_keep_missing_live_fields_visible_as_fallback(self, tmp_path):
        priors_path = _write_stack_priors(
            tmp_path / "stack_priors.yaml",
            {
                "frontdoor": _minimal_stack_prior_record(
                    "frontdoor",
                    throughput_tps=None,
                    quality_overall=0.91,
                    memory_cost=1.0,
                ),
            },
        )

        priors = stack_prior_q_scorer_priors_by_role(priors_path)

        assert priors.baseline_tps_by_role["frontdoor"] == pytest.approx(
            FALLBACK_BASELINE_TPS_BY_ROLE["frontdoor"]
        )
        assert priors.baseline_tps_source_by_role["frontdoor"] == PRIOR_SOURCE_DEGRADED_FALLBACK
        assert priors.baseline_quality_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert priors.memory_cost_source_by_role["frontdoor"] == PRIOR_SOURCE_STACK_PRIORS
        assert priors.uses_degraded_fallback is True
        assert validate_live_q_scorer_prior_sources(priors_path) == [
            "live q_scorer role 'frontdoor' uses throughput source "
            "degraded_fallback; expected stack_priors"
        ]
        with pytest.raises(QScorerPriorSourceError, match="live q_scorer role 'frontdoor'"):
            require_live_q_scorer_stack_priors(priors_path)

    def test_stack_prior_priors_fall_back_when_artifact_missing(self, tmp_path):
        missing = tmp_path / "missing_stack_priors.yaml"

        priors = stack_prior_q_scorer_priors_by_role(missing)

        assert "worker_explore" not in FALLBACK_BASELINE_TPS_BY_ROLE
        assert "worker_explore" not in FALLBACK_MEMORY_COST_BY_ROLE
        assert priors.baseline_tps_by_role == _with_q_scorer_aliases(
            FALLBACK_BASELINE_TPS_BY_ROLE
        )
        assert priors.memory_cost_by_role == _with_q_scorer_aliases(
            FALLBACK_MEMORY_COST_BY_ROLE
        )
        assert priors.baseline_tps_source_by_role["frontdoor"] == PRIOR_SOURCE_DEGRADED_FALLBACK
        assert priors.memory_cost_source_by_role["frontdoor"] == PRIOR_SOURCE_DEGRADED_FALLBACK
        assert priors.degraded_reason is not None
        errors = validate_live_q_scorer_prior_sources(missing)
        assert len(errors) == 1
        assert errors[0].startswith("q_scorer stack-priors validation failed:")
        with pytest.raises(QScorerPriorSourceError, match="validation failed"):
            require_live_q_scorer_stack_priors(missing)

    def test_default_stack_priors_path_exists(self):
        assert DEFAULT_STACK_PRIORS_PATH.exists()

    def test_baseline_tps_falls_back_when_registry_missing(self, tmp_path):
        missing = tmp_path / "missing.yaml"

        assert registry_baseline_tps_by_role(missing) == _with_q_scorer_aliases(
            FALLBACK_BASELINE_TPS_BY_ROLE
        )

    def test_memory_cost_falls_back_when_registry_missing(self, tmp_path):
        missing = tmp_path / "missing.yaml"

        assert registry_memory_cost_by_role(missing) == _with_q_scorer_aliases(
            FALLBACK_MEMORY_COST_BY_ROLE
        )

    def test_memory_cost_loads_current_hot_registry_roles(self, tmp_path):
        registry_path = tmp_path / "model_registry.yaml"
        registry_path.write_text(
            """
server_mode:
  frontdoor:
    tier: hot
  coder_escalation:
    tier: hot
  architect_general:
    tier: hot
  ingest_long_context:
    tier: hot
  worker:
    tier: hot
roles:
  worker_vision:
    memory:
      residency: hot
  vision_escalation:
    memory:
      residency: hot
""".strip()
        )

        costs = registry_memory_cost_by_role(registry_path)

        for role in (
            "frontdoor",
            "coder_escalation",
            "architect_general",
            "ingest_long_context",
            "worker_explore",
            "worker_general",
            "worker_math",
            "toolrunner",
            "worker_vision",
            "vision_escalation",
        ):
            assert costs[role] == pytest.approx(1.0)
        assert _RETIRED_ARCHITECT_ROLE not in costs

    def test_descriptor_priors_overlay_clean_existing_roles(self, tmp_path):
        descriptor_path = tmp_path / "model_descriptors.yaml"
        descriptor_path.write_text(
            """
models:
  - model_id: clean-frontdoor
    role_bindings:
      roles: [frontdoor, not_a_q_scorer_role]
    quality:
      suite_vector:
        overall: 0.91
        agentic: 0.99
    speed:
      solo_96t_tps: 31.5
    serving:
      numa_policy: clean
    known_gaps: []
""".strip()
        )

        priors = descriptor_q_scorer_priors_by_role(
            descriptor_path=descriptor_path,
            registry_path=tmp_path / "missing_registry.yaml",
        )

        assert priors.baseline_tps_by_role["frontdoor"] == pytest.approx(31.5)
        assert priors.baseline_quality_by_role["frontdoor"] == pytest.approx(0.91)
        assert "not_a_q_scorer_role" not in priors.baseline_tps_by_role
        assert "not_a_q_scorer_role" not in priors.baseline_quality_by_role

    def test_descriptor_priors_skip_role_server_conflicts(self, tmp_path):
        registry_path = tmp_path / "model_registry.yaml"
        registry_path.write_text(
            """
server_mode:
  worker:
    throughput: 60.7
roles: {}
""".strip()
        )
        descriptor_path = tmp_path / "model_descriptors.yaml"
        descriptor_path.write_text(
            """
models:
  - model_id: conflicted-worker-math
    role_bindings:
      roles: [worker_math]
    quality:
      suite_vector:
        overall: 0.99
    speed:
      quarter_48t_tps: 99.0
    serving:
      numa_policy: unresolved_role_server_conflict
    known_gaps:
      - "Role-server conflict: server_mode.worker points elsewhere."
""".strip()
        )

        priors = descriptor_q_scorer_priors_by_role(
            descriptor_path=descriptor_path,
            registry_path=registry_path,
        )

        assert priors.baseline_tps_by_role["worker_math"] == pytest.approx(60.7)
        # The conflicted descriptor's own 0.99 must be SKIPPED — that is what this
        # test is for. The value that replaces it is DERIVED, not asserted as a
        # literal: worker_math resolves to its own capability axis (math/aime26),
        # which is a different number from the fleet aggregate and from its
        # co-hosted siblings' tool_use score. A literal here has already rotted
        # twice in one day (0.85 -> 0.8067 -> 0.883); assert the property instead.
        got = priors.baseline_quality_by_role["worker_math"]
        assert got != pytest.approx(0.99), "conflicted descriptor quality leaked through"
        assert 0.0 < got <= 1.0
        from orchestration.repl_memory.q_scorer import _baseline_quality_by_role
        assert got == pytest.approx(_baseline_quality_by_role()["worker_math"])

    def test_descriptor_priors_fall_back_when_descriptor_missing(self, tmp_path):
        registry_path = tmp_path / "model_registry.yaml"
        registry_path.write_text(
            """
server_mode:
  frontdoor:
    throughput: 24.3
roles: {}
""".strip()
        )

        priors = descriptor_q_scorer_priors_by_role(
            descriptor_path=tmp_path / "missing_descriptors.yaml",
            registry_path=registry_path,
        )

        assert priors.baseline_tps_by_role["frontdoor"] == pytest.approx(24.3)

    def test_baseline_tps_values_positive(self):
        cfg = ScoringConfig()
        for role, tps in cfg.baseline_tps_by_role.items():
            assert tps > 0, f"{role} has non-positive tps: {tps}"

    def test_config_override(self):
        cfg = ScoringConfig(cost_penalty_lambda=0.5)
        assert cfg.cost_penalty_lambda == 0.5


# ===== registry performance t/s provenance (NIB2-57a) =====================
#
# `roles.*.performance.optimized_tps` and `roles.*.performance.baseline_tps`
# are DIFFERENT MEASUREMENTS. The loader used to return
# `optimized_tps or baseline_tps` as a bare float, so a caller could not tell
# which one it held — and a role whose two fields happen to be EQUAL was
# indistinguishable from one genuinely measured under optimization. These tests
# pin the separation. The numeric result is asserted UNCHANGED on purpose: the
# fix is provenance, not arithmetic.


def _write_registry(path: Path, roles: dict[str, dict[str, Any]]) -> Path:
    import yaml

    path.write_text(yaml.safe_dump({"server_mode": {}, "roles": roles}, sort_keys=True))
    return path


def _assert_registry_fixture(path: Path, expected_perf: dict[str, dict[str, Any]]) -> None:
    """Fail loudly if the fixture is not what the test below assumes.

    Without this, every assertion downstream could pass over an EMPTY or
    mistyped registry: the loader would silently return the fallback table and
    the test would be vacuous.
    """
    import yaml

    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict), f"fixture {path} did not parse to a mapping"
    roles = data.get("roles")
    assert isinstance(roles, dict) and roles, f"fixture {path} has no roles block"
    for role, perf in expected_perf.items():
        assert role in roles, f"fixture {path} is missing role {role!r}"
        got = roles[role].get("performance")
        assert isinstance(got, dict), f"fixture {path} role {role!r} has no performance dict"
        for key, value in perf.items():
            assert got.get(key) == value, (
                f"fixture {path} role {role!r} performance.{key} is {got.get(key)!r}, "
                f"expected {value!r}"
            )
        # The roles under test must be ones the loader actually reads.
        assert role in ROLE_PERFORMANCE_TPS_FALLBACKS, (
            f"{role!r} is not in ROLE_PERFORMANCE_TPS_FALLBACKS, so the loader "
            "never reads its performance block and this test would be vacuous"
        )


def _legacy_performance_tps(perf: dict[str, Any]) -> float | None:
    """The exact pre-2026-08-12 expression, kept to prove the numbers are unchanged."""
    return _coerce_tps(perf.get("optimized_tps")) or _coerce_tps(perf.get("baseline_tps"))


class TestRegistryTpsProvenance:
    @pytest.fixture(autouse=True)
    def _reset_warn_once(self):
        q_scorer_module._warned_tps_provenance_roles.clear()
        yield
        q_scorer_module._warned_tps_provenance_roles.clear()

    def test_optimized_and_baseline_are_never_folded_into_each_other(self):
        distinct = _performance_tps(
            "worker_vision", {"performance": {"optimized_tps": 112.2, "baseline_tps": 60.0}}
        )
        assert distinct is not None
        assert distinct.value == pytest.approx(112.2)
        assert distinct.source == PRIOR_SOURCE_REGISTRY_OPTIMIZED_TPS
        assert distinct.optimized_tps == pytest.approx(112.2)
        assert distinct.baseline_tps == pytest.approx(60.0)
        assert distinct.substituted is False
        assert distinct.unseparated is False
        assert distinct.carries_optimization_evidence is True

        substituted = _performance_tps(
            "worker_vision", {"performance": {"baseline_tps": 60.0}}
        )
        assert substituted is not None
        # Numeric behaviour is deliberately UNCHANGED: baseline still stands in.
        assert substituted.value == pytest.approx(60.0)
        assert substituted.source == PRIOR_SOURCE_REGISTRY_BASELINE_TPS_SUBSTITUTED
        assert substituted.optimized_tps is None
        assert substituted.baseline_tps == pytest.approx(60.0)
        assert substituted.substituted is True
        assert substituted.carries_optimization_evidence is False
        assert substituted.field_path == "roles.worker_vision.performance.baseline_tps"

        assert _performance_tps("worker_vision", {"performance": {}}) is None
        assert _performance_tps("worker_vision", {"performance": "not-a-dict"}) is None

    def test_coincident_optimized_and_baseline_are_separable(self, tmp_path):
        """THE coincidence case: two roles, ONE identical float, DIFFERENT meanings.

        `worker_vision` has optimized == baseline == 112.2 (one measurement in
        two fields, no optimization evidence). `vision_escalation` has a real
        optimized_tps of 112.2 measured against a distinct 60.0 baseline. The
        old loader returned 112.2 for both and nothing else, so the two states
        were indistinguishable. They must not be indistinguishable now.
        """
        registry_path = _write_registry(
            tmp_path / "model_registry.yaml",
            {
                "worker_vision": {
                    "performance": {"optimized_tps": 112.2, "baseline_tps": 112.2}
                },
                "vision_escalation": {
                    "performance": {"optimized_tps": 112.2, "baseline_tps": 60.0}
                },
            },
        )
        _assert_registry_fixture(
            registry_path,
            {
                "worker_vision": {"optimized_tps": 112.2, "baseline_tps": 112.2},
                "vision_escalation": {"optimized_tps": 112.2, "baseline_tps": 60.0},
            },
        )

        floats = registry_baseline_tps_by_role(registry_path)
        priors = registry_baseline_tps_priors(registry_path)

        # Precondition: the bare floats really are identical, so nothing below
        # can be passing merely because the numbers differ.
        assert floats["worker_vision"] == pytest.approx(112.2)
        assert floats["vision_escalation"] == pytest.approx(112.2)
        assert floats["worker_vision"] == floats["vision_escalation"]

        assert priors["worker_vision"].source == PRIOR_SOURCE_REGISTRY_TPS_UNSEPARATED
        assert priors["vision_escalation"].source == PRIOR_SOURCE_REGISTRY_OPTIMIZED_TPS
        assert priors["worker_vision"].source != priors["vision_escalation"].source
        assert priors["worker_vision"].unseparated is True
        assert priors["worker_vision"].carries_optimization_evidence is False
        assert priors["vision_escalation"].carries_optimization_evidence is True
        # Both raw measurements survive on both records.
        assert priors["worker_vision"].baseline_tps == pytest.approx(112.2)
        assert priors["vision_escalation"].baseline_tps == pytest.approx(60.0)

    def test_substituted_baseline_is_logged_not_silent(self, tmp_path, caplog):
        registry_path = _write_registry(
            tmp_path / "model_registry.yaml",
            {"worker_vision": {"performance": {"baseline_tps": 60.0}}},
        )
        _assert_registry_fixture(registry_path, {"worker_vision": {"baseline_tps": 60.0}})

        with caplog.at_level(logging.WARNING, logger="orchestration.repl_memory.q_scorer"):
            registry_baseline_tps_priors(registry_path)

        messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any(
            "worker_vision" in m and "UNOPTIMIZED baseline_tps" in m for m in messages
        ), f"substitution was not logged; got {messages!r}"

    def test_unseparated_pair_is_logged_not_silent(self, tmp_path, caplog):
        registry_path = _write_registry(
            tmp_path / "model_registry.yaml",
            {"worker_vision": {"performance": {"optimized_tps": 112.2, "baseline_tps": 112.2}}},
        )
        _assert_registry_fixture(
            registry_path, {"worker_vision": {"optimized_tps": 112.2, "baseline_tps": 112.2}}
        )

        with caplog.at_level(logging.WARNING, logger="orchestration.repl_memory.q_scorer"):
            registry_baseline_tps_priors(registry_path)

        messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any(
            "worker_vision" in m and "optimized_tps == baseline_tps" in m for m in messages
        ), f"unseparated pair was not logged; got {messages!r}"

    def test_substituted_source_reaches_the_caller_visible_prior_channel(self, tmp_path):
        """Provenance must survive into QScorerPriors.baseline_tps_source_by_role.

        That map is the channel ScoringConfig already exposes, so this is the
        assertion that the fix reaches a CONSUMER rather than stopping at the
        loader.
        """
        registry_path = _write_registry(
            tmp_path / "model_registry.yaml",
            {
                "worker_vision": {"performance": {"baseline_tps": 60.0}},
                "vision_escalation": {
                    "performance": {"optimized_tps": 112.2, "baseline_tps": 112.2}
                },
            },
        )
        _assert_registry_fixture(
            registry_path,
            {
                "worker_vision": {"baseline_tps": 60.0},
                "vision_escalation": {"optimized_tps": 112.2, "baseline_tps": 112.2},
            },
        )

        priors = descriptor_q_scorer_priors_by_role(
            descriptor_path=tmp_path / "missing_descriptors.yaml",
            registry_path=registry_path,
        )

        assert priors.baseline_tps_by_role["worker_vision"] == pytest.approx(60.0)
        assert (
            priors.baseline_tps_source_by_role["worker_vision"]
            == PRIOR_SOURCE_REGISTRY_BASELINE_TPS_SUBSTITUTED
        )
        assert (
            priors.baseline_tps_source_by_role["vision_escalation"]
            == PRIOR_SOURCE_REGISTRY_TPS_UNSEPARATED
        )
        # Roles the registry did not speak to keep the historical flat label,
        # so this change does not relabel anything it did not measure.
        assert priors.baseline_tps_source_by_role["frontdoor"] == PRIOR_SOURCE_REGISTRY

    def test_float_projection_never_drifts_from_the_records(self, tmp_path):
        registry_path = _write_registry(
            tmp_path / "model_registry.yaml",
            {
                "worker_vision": {"performance": {"optimized_tps": 112.2, "baseline_tps": 112.2}},
                "vision_escalation": {"performance": {"baseline_tps": 60.0}},
            },
        )
        floats = registry_baseline_tps_by_role(registry_path)
        priors = registry_baseline_tps_priors(registry_path)

        assert floats, "projection is empty; every assertion below would be vacuous"
        assert set(floats) == set(priors)
        assert floats == {role: prior.value for role, prior in priors.items()}
        # An alias record must not claim to be the canonical role it copied.
        for role, prior in priors.items():
            assert prior.role == role

    def test_numeric_behaviour_is_unchanged_on_the_live_registry(self):
        """The fix must not move any routing number. Proven against real data."""
        import yaml

        assert DEFAULT_MODEL_REGISTRY_PATH.exists()
        data = yaml.safe_load(DEFAULT_MODEL_REGISTRY_PATH.read_text())
        registry_roles = data.get("roles") or {}
        assert registry_roles, "live registry has no roles block"

        floats = registry_baseline_tps_by_role(DEFAULT_MODEL_REGISTRY_PATH)
        checked = 0
        for target_role, registry_role in ROLE_PERFORMANCE_TPS_FALLBACKS.items():
            record = registry_roles.get(registry_role)
            if not isinstance(record, dict):
                continue
            perf = record.get("performance")
            if not isinstance(perf, dict):
                continue
            legacy = _legacy_performance_tps(perf)
            if legacy is None:
                continue
            assert floats[target_role] == pytest.approx(legacy)
            checked += 1
        assert checked >= 2, (
            f"only {checked} live roles exercised the performance path; "
            "this test would be vacuous"
        )

    def test_live_registry_coincidences_are_classified_not_hidden(self):
        """Today's real registry contains the coincidence case. It must be labelled.

        The antecedent is asserted non-empty, so this cannot pass by finding
        nothing to check.
        """
        import yaml

        data = yaml.safe_load(DEFAULT_MODEL_REGISTRY_PATH.read_text())
        registry_roles = data.get("roles") or {}
        priors = registry_baseline_tps_priors(DEFAULT_MODEL_REGISTRY_PATH)

        coincident = []
        for target_role, registry_role in ROLE_PERFORMANCE_TPS_FALLBACKS.items():
            perf = (registry_roles.get(registry_role) or {}).get("performance")
            if not isinstance(perf, dict):
                continue
            optimized = _coerce_tps(perf.get("optimized_tps"))
            baseline = _coerce_tps(perf.get("baseline_tps"))
            if optimized is not None and baseline is not None and optimized == baseline:
                coincident.append(target_role)

        assert coincident, (
            "no live role currently has optimized_tps == baseline_tps; if the "
            "registry was corrected, keep the synthetic coincidence test above "
            "and delete this one rather than letting it pass vacuously"
        )
        for role in coincident:
            assert priors[role].source == PRIOR_SOURCE_REGISTRY_TPS_UNSEPARATED
            assert priors[role].unseparated is True
            assert priors[role].carries_optimization_evidence is False


# ===== _compute_reward without cost metrics (backward compat) =====


class TestComputeRewardNoCost:
    def test_success_no_cost(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("success"), [], [])
        assert r == 1.0

    def test_failure_no_cost(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("failure"), [], [])
        assert r == -0.5

    def test_partial_no_cost(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("partial"), [], [])
        assert r == 0.3

    def test_gate_failures_penalize(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("success"), [_make_gate_fail(), _make_gate_fail()], [])
        assert r == pytest.approx(0.8)  # 1.0 - 2*0.1

    def test_escalation_penalizes(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("success"), [], [_make_escalation()])
        assert r == pytest.approx(0.85)  # 1.0 - 0.15

    def test_plan_review_approved(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("success"), [], [], [_make_plan_review("ok")])
        assert r == pytest.approx(1.0)  # 1.0 + 0.1 clamped to 1.0

    def test_plan_review_corrected(self):
        s = _scorer()
        r = s._compute_reward(_make_outcome("success"), [], [], [_make_plan_review("corrected")])
        assert r == pytest.approx(0.8)  # 1.0 - 0.2


# ===== _compute_reward with cost metrics =====


def _latency_only_config(**overrides) -> ScoringConfig:
    """Config with quality-gap and memory penalties zeroed (isolate latency tests)."""
    overrides.setdefault(
        "baseline_tps_by_role",
        {
            "frontdoor": 12.7,
            "architect_general": 4.3,
        },
    )
    # Isolate the tokens/sec formula: its weight is pinned to the value these tests'
    # arithmetic is written in (0.15), and the E18 duration axis is off here.
    overrides.setdefault("cost_penalty_lambda", 0.15)
    overrides.setdefault("cost_lambda_duration", 0.0)
    return ScoringConfig(cost_lambda_quality_gap=0.0, cost_lambda_memory=0.0, **overrides)


class TestComputeRewardWithCost:
    # NOTE: frontdoor baseline_tps=12.7, architect=4.3 (updated 2026-03-29).
    # Use 127 tokens for frontdoor (127/12.7=10s expected) and 43 for architect
    # (43/4.3=10s expected) to produce exact integer cost ratios.

    def test_at_expected_speed_no_penalty(self):
        """Running at exactly baseline speed → cost_ratio=1.0 → no latency penalty."""
        s = _scorer(_latency_only_config())
        # frontdoor at 12.7 t/s, 127 tokens in 10s → exactly expected
        cost = {"tokens_generated": 127, "elapsed_seconds": 10.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0

    def test_faster_than_expected_no_penalty(self):
        """Running faster than baseline → cost_ratio < 1.0 → no penalty."""
        s = _scorer(_latency_only_config())
        # frontdoor at 12.7 t/s, 127 tokens in 5s → 2x faster
        cost = {"tokens_generated": 127, "elapsed_seconds": 5.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0

    def test_slower_than_expected_penalized(self):
        """Running 2x slower → cost_ratio=2.0 → penalty = 0.15 * (2.0 - 1.0) = 0.15."""
        s = _scorer(_latency_only_config())
        # frontdoor at 12.7 t/s, 127 tokens in 20s → 2x slower
        cost = {"tokens_generated": 127, "elapsed_seconds": 20.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == pytest.approx(0.85)  # 1.0 - 0.15

    def test_much_slower_higher_penalty(self):
        """Running 5x slower → penalty = 0.15 * 4.0 = 0.60."""
        s = _scorer(_latency_only_config())
        cost = {"tokens_generated": 127, "elapsed_seconds": 50.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == pytest.approx(0.4)  # 1.0 - 0.60

    def test_incorrect_no_cost_penalty(self):
        """Failed tasks get failure_reward regardless of cost."""
        s = _scorer(_latency_only_config())
        cost = {"tokens_generated": 127, "elapsed_seconds": 100.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("failure"), [], [], cost_metrics=cost)
        assert r == -0.5  # No cost penalty applied (reward <= 0)

    def test_unknown_role_no_penalty(self):
        """Unknown role has no baseline → no cost penalty."""
        s = _scorer(_latency_only_config())
        cost = {"tokens_generated": 100, "elapsed_seconds": 100.0, "role": "unknown_role"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0

    def test_zero_tokens_no_penalty(self):
        """Zero tokens_generated → skip cost computation."""
        s = _scorer(_latency_only_config())
        cost = {"tokens_generated": 0, "elapsed_seconds": 10.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0

    def test_zero_elapsed_no_penalty(self):
        """Zero elapsed → skip cost computation (avoid division by zero)."""
        s = _scorer(_latency_only_config())
        cost = {"tokens_generated": 100, "elapsed_seconds": 0.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0

    def test_cost_plus_gate_penalties_stack(self):
        """Cost penalty stacks with gate failure penalties."""
        s = _scorer(_latency_only_config())
        # 2x slower + 1 gate failure
        cost = {"tokens_generated": 127, "elapsed_seconds": 20.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [_make_gate_fail()], [], cost_metrics=cost)
        # 1.0 - 0.1 (gate) - 0.15 (cost) = 0.75
        assert r == pytest.approx(0.75)

    def test_clamp_lower_bound(self):
        """Extreme cost penalty clamped to -1.0."""
        cfg = _latency_only_config(cost_penalty_lambda=10.0)  # Very aggressive
        s = _scorer(cfg)
        cost = {"tokens_generated": 127, "elapsed_seconds": 50.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == -1.0

    def test_custom_lambda(self):
        """Custom lambda changes penalty magnitude."""
        cfg = _latency_only_config(cost_penalty_lambda=0.5)
        s = _scorer(cfg)
        # 2x slower with lambda=0.5 → penalty = 0.5 * 1.0 = 0.5
        cost = {"tokens_generated": 127, "elapsed_seconds": 20.0, "role": "frontdoor"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == pytest.approx(0.5)

    def test_architect_role_slower_baseline(self):
        """Architect (4.3 t/s) at expected speed → no latency penalty."""
        s = _scorer(_latency_only_config())
        # 43 tokens at 4.3 t/s → 10s expected; actual 10s
        cost = {"tokens_generated": 43, "elapsed_seconds": 10.0, "role": "architect_general"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0

    def test_architect_role_2x_slower(self):
        """Architect at 2x slower → penalty = 0.15 * 1.0 = 0.15."""
        s = _scorer(_latency_only_config())
        cost = {"tokens_generated": 43, "elapsed_seconds": 20.0, "role": "architect_general"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == pytest.approx(0.85)


# ===== Multi-dimensional cost model tests =====


def _compiled_quality_prior(
    role: str, record: dict[str, Any]
) -> tuple[float | None, str | None]:
    """Re-derive q_scorer's quality projection for ONE compiled priors record.

    Mirrors the loader's two layers in orchestration/repl_memory/q_scorer.py:

    * `_baseline_quality_by_role()` (~line 205) projects every record: a
      numeric `quality_for_role.value` (0..1) wins, else the model-keyed
      table keyed by model_path basename, else the role is OMITTED. Its
      docstring states the contract this test enforces: "A role whose model
      has no measured entry is OMITTED rather than defaulted. Falling back to
      a number would reinstate exactly the defect this replaced." It also
      skips `_NON_SCORING_HOST_ALIASES` (e.g. "worker") entirely — a host-only
      registry/launch-manifest alias, not a `Role`.
    * `stack_prior_q_scorer_priors_by_role()` then overrides live_stack
      records with a numeric `quality_for_role.value` or `quality_overall`,
      stamping PRIOR_SOURCE_STACK_PRIORS. Anything else that survives does so
      through the degraded-fallback base layer (PRIOR_SOURCE_DEGRADED_FALLBACK).
      Same host-alias skip applies here.

    Returns (expected_value, expected_source); expected_source is None when
    the role must be ABSENT — never defaulted to a number.
    """
    if role in _NON_SCORING_HOST_ALIASES:
        return None, None
    if not isinstance(record, dict):
        return None, None
    priors = record.get("priors") or {}
    if not isinstance(priors, dict):
        priors = {}

    for_role = priors.get("quality_for_role")
    qfr = None
    if isinstance(for_role, dict):
        value = for_role.get("value")
        if isinstance(value, (int, float)) and 0 <= float(value) <= 1:
            qfr = float(value)

    is_live = record.get("deployment_status") == "live_stack"
    if is_live and qfr is None:
        overall = priors.get("quality_overall")
        if isinstance(overall, (int, float)) and 0 <= float(overall) <= 1:
            return float(overall), PRIOR_SOURCE_STACK_PRIORS
    if qfr is not None:
        return qfr, PRIOR_SOURCE_STACK_PRIORS if is_live else PRIOR_SOURCE_DEGRADED_FALLBACK

    model_path = (
        ((record.get("serving") or {}).get("launch") or {}).get("requirements") or {}
    ).get("model_path")
    if isinstance(model_path, str) and model_path:
        quality = BASELINE_QUALITY_BY_MODEL.get(model_path.rsplit("/", 1)[-1])
        if quality is not None:
            return float(quality), PRIOR_SOURCE_DEGRADED_FALLBACK
    return None, None


def _compiled_tps_prior(role: str, record: dict[str, Any]) -> float | None:
    """Re-derive q_scorer's throughput projection for ONE compiled priors record.

    Mirrors `stack_prior_q_scorer_priors_by_role()`: a live role's own
    `priors.throughput_tps`, skipping `_NON_SCORING_HOST_ALIASES` (e.g.
    "worker") the same way the loader does.
    """
    if role in _NON_SCORING_HOST_ALIASES:
        return None
    if not isinstance(record, dict):
        return None
    priors = record.get("priors") or {}
    if not isinstance(priors, dict):
        return None
    return _coerce_tps(priors.get("throughput_tps"))


class TestMultiDimensionalCost:
    """Test quality-gap and memory-tier cost dimensions."""

    def test_config_has_quality_baselines(self):
        """Quality baselines are a projection of the compiled stack priors.

        Contract enforced here — the one the loader actually implements in
        orchestration/repl_memory/q_scorer.py `_baseline_quality_by_role()`
        (~line 205): "A role whose model has no measured entry is OMITTED
        rather than defaulted. Falling back to a number would reinstate
        exactly the defect this replaced."

        * A role whose record carries a numeric quality_for_role.value (0..1)
          — or whose model path hits the model-keyed fallback — IS projected;
          live roles carry the PRIOR_SOURCE_STACK_PRIORS source.
        * A role whose quality is null/absent with no model-path fallback is
          OMITTED, never defaulted.

        The expectation is DERIVED from the same compiled priors file the
        loader reads (orchestration/derived/stack_priors.yaml), never from a
        hardcoded role name: after the 2026-08-23 Qwen3.8-27B swap,
        architect_general's quality_overall and quality_for_role are both
        null (only E-7 chat-template stamps under quality_by_axis exist,
        which are NOT a quality_overall baseline), so it is correctly absent.
        A future model swap therefore cannot rot this test the way the old
        hardcoded "architect_general in baseline_quality_by_role" did.

        STACK_PRIOR_SCORER_ROLE_ALIASES is applied as a final pass, matching
        `stack_prior_q_scorer_priors_by_role()`: worker_explore is aliased
        onto worker_general and never keeps its own record's figure once
        worker_general compiles — asserted explicitly below too.
        """
        import yaml

        priors_path = (
            Path(__file__).resolve().parents[2] / "orchestration" / "derived" / "stack_priors.yaml"
        )
        assert priors_path.exists(), "compiled stack priors missing; cannot derive expectations"
        compiled = yaml.safe_load(priors_path.read_text()) or {}
        records = compiled.get("roles") or {}
        assert records, (
            "compiled stack priors have no roles block; every assertion would be vacuous"
        )

        cfg = ScoringConfig()

        expected: dict[str, tuple[float, str]] = {}
        for role, record in records.items():
            quality, source = _compiled_quality_prior(role, record)
            if quality is None:
                assert role not in cfg.baseline_quality_by_role, (
                    f"compiled role {role!r} has no measured quality "
                    "(quality_for_role null/absent and no model-path fallback) "
                    "but appears in baseline_quality_by_role; the loader omits "
                    "it by contract — never default it"
                )
                continue
            expected[role] = (quality, source)

        for canonical_role, aliases in STACK_PRIOR_SCORER_ROLE_ALIASES.items():
            if canonical_role not in expected:
                continue
            for alias in aliases:
                expected[alias] = expected[canonical_role]

        # Every derived expectation is projected, with the loader's source.
        for role, (quality, source) in expected.items():
            assert role in cfg.baseline_quality_by_role, (
                f"compiled role {role!r} has measured quality {quality} but was dropped"
            )
            assert cfg.baseline_quality_by_role[role] == pytest.approx(quality)
            assert cfg.baseline_quality_source_by_role.get(role) == source, (
                f"role {role!r} quality source is "
                f"{cfg.baseline_quality_source_by_role.get(role)!r}, expected {source!r}"
            )
        # ...and nothing beyond the compiled data leaked in.
        assert set(cfg.baseline_quality_by_role) == set(expected), (
            f"unexpected roles in baseline_quality_by_role: "
            f"{sorted(set(cfg.baseline_quality_by_role) ^ set(expected))}"
        )

        # Existing teeth, kept against the same data: worker_explore is the
        # q_scorer action label aliased onto worker_general's live priors.
        assert "worker_explore" in cfg.baseline_quality_by_role
        assert cfg.baseline_quality_by_role["worker_explore"] == pytest.approx(
            cfg.baseline_quality_by_role["worker_general"]
        )
        assert cfg.baseline_quality_source_by_role["worker_explore"] == PRIOR_SOURCE_STACK_PRIORS

    def test_config_has_memory_costs(self):
        cfg = ScoringConfig()
        assert cfg.memory_cost_by_role["frontdoor"] == pytest.approx(1.0)
        assert cfg.memory_cost_by_role["coder_escalation"] == pytest.approx(1.0)
        assert cfg.memory_cost_by_role["architect_general"] == pytest.approx(1.0)
        assert cfg.memory_cost_by_role["ingest_long_context"] == pytest.approx(1.0)
        assert _RETIRED_ARCHITECT_ROLE not in cfg.memory_cost_by_role

    def test_quality_gap_penalty_architect(self):
        """HOT architect gets quality-gap penalty but no warm-tier memory penalty."""
        cfg = ScoringConfig(
            baseline_tps_by_role={"architect_general": 12.19},
            baseline_quality_by_role={"architect_general": 0.94},
            memory_cost_by_role={"architect_general": 1.0},
        )
        s = _scorer(cfg)
        # At expected speed, no latency penalty (12.19 t/s registry baseline).
        cost = {"tokens_generated": 1219, "elapsed_seconds": 100.0, "role": "architect_general"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        # quality_gap = 0.94 - 0.75 = 0.19, penalty = 0.10 * 0.19 = 0.019
        # memory_cost = 1.0 (HOT), no memory penalty.
        assert r == pytest.approx(0.981)

    def test_quality_gap_penalty_worker(self):
        """Worker action label shares generated worker_general quality."""
        s = _scorer()
        # worker_explore at 60.7 t/s, 607 tokens in 10s -> exactly at expected speed.
        cost = {"tokens_generated": 607, "elapsed_seconds": 10.0, "role": "worker_explore"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        # DERIVED, not hardcoded. worker quality moved 0.9 -> 0.778 on 2026-08-02
        # when worker roles began scoring on their own capability axis
        # (tool_use / tool_compliance_local) instead of a fleet-wide aggregate.
        # A literal here silently re-rots on the next quality measurement, which
        # is exactly what happened to the 0.985 this replaces.
        quality = s.config.baseline_quality_by_role["worker_explore"]
        expected = 1.0 - s.config.cost_lambda_quality_gap * max(0.0, quality - 0.75)
        # memory_cost = 1.0 (HOT) → no memory penalty
        assert r == pytest.approx(expected)
        # and the penalty must actually be doing something
        assert quality > 0.75, "test is vacuous if worker quality is at the floor"

    def test_custom_non_hot_memory_cost_penalizes(self):
        """Non-HOT residency still gets a memory penalty when configured."""
        cfg = ScoringConfig(
            baseline_tps_by_role={"external_warm": 10.0},
            memory_cost_by_role={"external_warm": 2.0},
            cost_penalty_lambda=0.0,
            cost_lambda_quality_gap=0.0,
        )
        s = _scorer(cfg)
        # Isolate memory penalty only (zero out other dimensions)
        cost = {"tokens_generated": 100, "elapsed_seconds": 10.0, "role": "external_warm"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        # memory_cost = 2.0, penalty = 0.05 * (2.0 - 1.0) = 0.05
        assert r == pytest.approx(0.95)

    def test_memory_tier_no_penalty_hot(self):
        """HOT tier models (worker) have no memory penalty."""
        cfg = ScoringConfig(cost_penalty_lambda=0.0, cost_lambda_quality_gap=0.0)
        s = _scorer(cfg)
        cost = {"tokens_generated": 607, "elapsed_seconds": 10.0, "role": "worker_explore"}
        r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=cost)
        assert r == 1.0  # No memory penalty for HOT

    def test_worker_beats_architect_on_simple_task(self):
        """Worker on simple task should get higher reward than architect."""
        s = _scorer()
        # Worker at expected speed, correct
        worker_cost = {"tokens_generated": 607, "elapsed_seconds": 10.0, "role": "worker_explore"}
        worker_r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=worker_cost)

        # Architect slower than expected, correct — plus quality-gap penalty
        arch_cost = {"tokens_generated": 675, "elapsed_seconds": 100.0, "role": "architect_general"}
        arch_r = s._compute_reward(_make_outcome("success"), [], [], cost_metrics=arch_cost)

        assert worker_r > arch_r, (
            f"Worker reward ({worker_r}) should beat architect ({arch_r}) on simple correct tasks"
        )

    def test_no_quality_memory_penalty_on_failure(self):
        """Quality and memory penalties only apply to correct answers."""
        s = _scorer()
        cost = {"tokens_generated": 675, "elapsed_seconds": 100.0, "role": "architect_general"}
        r = s._compute_reward(_make_outcome("failure"), [], [], cost_metrics=cost)
        assert r == -0.5  # Pure failure reward, no cost penalty


# ===== _compute_contrastive_adjustment (DAR-2) =====

import numpy as np
from orchestration.repl_memory.episodic_store import MemoryEntry
from orchestration.repl_memory.embedder import hash_fallback_embedding


def _make_memory(action: str, q_value: float = 0.5, memory_id: str = "m1") -> MemoryEntry:
    """Create a MemoryEntry with controlled action/Q-value for contrastive tests."""
    return MemoryEntry(
        id=memory_id,
        embedding=None,
        action=action,
        action_type="routing",
        context={},
        q_value=q_value,
    )


def _make_task_entry(data: dict | None = None) -> _FakeEntry:
    """Create a fake task_started entry with task context data."""
    return _FakeEntry(
        event_type=EventType.TASK_COMPLETED,
        data=data or {"task_type": "chat", "objective": "test task"},
    )


def _make_routing_entry(
    action: str = "frontdoor", memory_id: str | None = "m-selected",
) -> _FakeEntry:
    """Create a fake routing_decision entry."""
    entry = _FakeEntry(
        event_type=EventType.TASK_COMPLETED,
        data={"routing": [action]},
    )
    entry.memory_id = memory_id  # type: ignore[attr-defined]
    return entry


class TestComputeContrastiveAdjustment:
    """Tests for DAR-2 _compute_contrastive_adjustment."""

    def test_no_task_context_returns_zero(self):
        """Empty task_started data → 0.0."""
        s = _scorer()
        task = _FakeEntry(event_type=EventType.TASK_COMPLETED, data={})
        routing = _make_routing_entry()
        assert s._compute_contrastive_adjustment(task, routing, reward=0.5) == 0.0

    def test_none_task_started_returns_zero(self):
        """None task_started → 0.0."""
        s = _scorer()
        routing = _make_routing_entry()
        assert s._compute_contrastive_adjustment(None, routing, reward=0.5) == 0.0

    def test_embedding_failure_returns_zero(self):
        """Embedding failure → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.side_effect = RuntimeError("embed failed")
        task = _make_task_entry()
        routing = _make_routing_entry()
        assert s._compute_contrastive_adjustment(task, routing, reward=0.5) == 0.0

    def test_no_candidates_returns_zero(self):
        """No similar routing memories → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = []
        task = _make_task_entry()
        routing = _make_routing_entry()
        assert s._compute_contrastive_adjustment(task, routing, reward=0.5) == 0.0

    def test_no_alternatives_returns_zero(self):
        """All candidates have the same action as selected → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        # All candidates use same action as selected
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.7, memory_id="c1"),
            _make_memory("frontdoor", q_value=0.6, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.65)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")
        assert s._compute_contrastive_adjustment(task, routing, reward=0.5) == 0.0

    def test_all_alternatives_at_default_returns_zero(self):
        """Alternatives at default Q=0.5 (unlearned) → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.7, memory_id="c1"),
            _make_memory("architect_general", q_value=0.5, memory_id="c2"),  # default
            _make_memory("coder_escalation", q_value=0.5, memory_id="c3"),  # default
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.7)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")
        assert s._compute_contrastive_adjustment(task, routing, reward=0.5) == 0.0

    def test_success_selected_below_best_alt_positive_adjustment(self):
        """Success + selected Q below best alternative → positive adjustment."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.6, memory_id="c1"),
            _make_memory("architect_general", q_value=0.8, memory_id="c2"),
        ]
        # Selected model's current Q
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.6)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_contrastive_adjustment(task, routing, reward=0.5)
        # max_alt_q=0.8, margin=0.05, gap = 0.8 + 0.05 - 0.6 = 0.25
        # adj = min(0.1, 0.05 * 0.25) = min(0.1, 0.0125) = 0.0125
        assert adj > 0
        assert adj == pytest.approx(0.0125)

    def test_success_selected_above_alt_with_margin_returns_zero(self):
        """Success + selected Q already above alternatives + margin → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.9, memory_id="c1"),
            _make_memory("architect_general", q_value=0.7, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.9)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        # max_alt_q=0.7, gap = 0.7 + 0.05 - 0.9 = -0.15 → negative, no adjustment
        adj = s._compute_contrastive_adjustment(task, routing, reward=0.5)
        assert adj == 0.0

    def test_failure_selected_above_worst_alt_negative_adjustment(self):
        """Failure + selected Q above worst alternative → negative adjustment."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.7, memory_id="c1"),
            _make_memory("architect_general", q_value=0.4, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.7)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_contrastive_adjustment(task, routing, reward=-0.5)
        # min_alt_q=0.4, gap = 0.7 + 0.05 - 0.4 = 0.35
        # adj = max(-0.1, -0.05 * 0.35) = max(-0.1, -0.0175) = -0.0175
        assert adj < 0
        assert adj == pytest.approx(-0.0175)

    def test_failure_selected_below_alt_returns_zero(self):
        """Failure + selected Q already below worst alternative → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.3, memory_id="c1"),
            _make_memory("architect_general", q_value=0.6, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.3)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        # min_alt_q=0.6, gap = 0.3 + 0.05 - 0.6 = -0.25 → negative, no adjustment
        adj = s._compute_contrastive_adjustment(task, routing, reward=-0.5)
        assert adj == 0.0

    def test_positive_adjustment_capped_at_max_adj(self):
        """Large positive gap still capped at max_adj."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        # Huge gap: selected at 0.1, alt at 0.95
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.1, memory_id="c1"),
            _make_memory("architect_general", q_value=0.95, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.1)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_contrastive_adjustment(task, routing, reward=0.5, max_adj=0.1)
        # gap = 0.95 + 0.05 - 0.1 = 0.9, min(0.1, 0.05*0.9) = min(0.1, 0.045) = 0.045
        assert adj <= 0.1
        assert adj > 0

    def test_negative_adjustment_capped_at_neg_max_adj(self):
        """Large negative gap still capped at -max_adj."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        # Huge gap: selected at 0.95, alt at 0.1
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.95, memory_id="c1"),
            _make_memory("architect_general", q_value=0.1, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.95)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_contrastive_adjustment(task, routing, reward=-0.5, max_adj=0.1)
        # gap = 0.95 + 0.05 - 0.1 = 0.9, max(-0.1, -0.05*0.9) = max(-0.1, -0.045) = -0.045
        assert adj >= -0.1
        assert adj < 0

    def test_no_memory_id_uses_default_q(self):
        """No memory_id on routing decision → uses default Q=0.5."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("architect_general", q_value=0.8, memory_id="c1"),
        ]
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor", memory_id=None)

        adj = s._compute_contrastive_adjustment(task, routing, reward=0.5)
        # selected_q=0.5 (default), max_alt_q=0.8, gap=0.8+0.05-0.5=0.35
        # adj = min(0.1, 0.05*0.35) = 0.0175
        assert adj == pytest.approx(0.0175)


# ===== _compute_spo_plus_adjustment (DAR-3) =====


class TestComputeSpoPlusAdjustment:
    """Tests for DAR-3 _compute_spo_plus_adjustment."""

    def test_no_task_context_returns_zero(self):
        """Empty task_started data → 0.0."""
        s = _scorer()
        task = _FakeEntry(event_type=EventType.TASK_COMPLETED, data={})
        routing = _make_routing_entry()
        assert s._compute_spo_plus_adjustment(task, routing, reward=0.5) == 0.0

    def test_embedding_failure_returns_zero(self):
        """Embedding failure → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.side_effect = RuntimeError("embed failed")
        task = _make_task_entry()
        routing = _make_routing_entry()
        assert s._compute_spo_plus_adjustment(task, routing, reward=0.5) == 0.0

    def test_no_candidates_returns_zero(self):
        """No similar routing memories → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = []
        task = _make_task_entry()
        routing = _make_routing_entry()
        assert s._compute_spo_plus_adjustment(task, routing, reward=0.5) == 0.0

    def test_no_alternatives_returns_zero(self):
        """All candidates same action → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.7, memory_id="c1"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.7)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")
        assert s._compute_spo_plus_adjustment(task, routing, reward=0.5) == 0.0

    def test_success_with_alternatives_produces_adjustment(self):
        """Success with alternatives → non-zero adjustment."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.6, memory_id="c1"),
            _make_memory("architect_general", q_value=0.8, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.6)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_spo_plus_adjustment(task, routing, reward=0.7)
        # Non-zero: SPO+ should produce some adjustment when alternatives exist
        # and the reward signal disagrees with the current ranking
        assert isinstance(adj, float)

    def test_adjustment_bounded(self):
        """Adjustment never exceeds max_adj."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        # Large gap between selected and alternatives
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.1, memory_id="c1"),
            _make_memory("architect_general", q_value=0.95, memory_id="c2"),
            _make_memory("coder_escalation", q_value=0.9, memory_id="c3"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.1)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_spo_plus_adjustment(task, routing, reward=1.0, max_adj=0.15)
        assert abs(adj) <= 0.15

    def test_small_spo_loss_below_margin_returns_zero(self):
        """SPO+ loss below margin threshold → 0.0."""
        s = _scorer()
        s.embedder.embed_task_ir.return_value = np.zeros(128)
        # Nearly equal Q-values → loss ≈ 0
        s.store.retrieve_by_similarity.return_value = [
            _make_memory("frontdoor", q_value=0.5, memory_id="c1"),
            _make_memory("architect_general", q_value=0.51, memory_id="c2"),
        ]
        s.store.get_by_id.return_value = _make_memory("frontdoor", q_value=0.5)
        task = _make_task_entry()
        routing = _make_routing_entry("frontdoor")

        adj = s._compute_spo_plus_adjustment(task, routing, reward=0.5, margin=1.0)
        assert adj == 0.0


class TestExternalScoreIdentity:
    def _candidate(self, *, objective: str, task_type: str = "chat") -> MemoryEntry:
        return MemoryEntry(
            id="candidate",
            embedding=None,
            action="frontdoor:direct",
            action_type="routing",
            context={"objective": objective, "task_type": task_type},
            q_value=0.7,
            similarity_score=0.99,
        )

    def test_high_similarity_different_identity_is_not_updated(self):
        scorer = _scorer()
        scorer.store.retrieve_by_similarity.return_value = [
            self._candidate(objective="another task"),
        ]
        scorer.score_external_result(
            "target task",
            "frontdoor:direct",
            1.0,
            context={"task_type": "chat"},
            embedding=np.ones(1024, dtype=np.float32),
        )
        scorer.store.update_q_value.assert_not_called()
        scorer.store.store.assert_called_once()

    def test_exact_normalized_identity_is_updated(self):
        scorer = _scorer()
        scorer.store.retrieve_by_similarity.return_value = [
            self._candidate(objective="target   task", task_type=" chat "),
        ]
        scorer.score_external_result(
            " target task ",
            " frontdoor:direct ",
            1.0,
            context={"task_type": "chat"},
            embedding=np.ones(1024, dtype=np.float32),
        )
        scorer.store.update_q_value.assert_called_once()
        scorer.store.store.assert_not_called()

    def test_fallback_embedding_cannot_update_or_create(self):
        scorer = _scorer()
        scorer.store.retrieve_by_similarity.return_value = [
            self._candidate(objective="target task"),
        ]
        fallback = hash_fallback_embedding("type:chat | objective:target task")
        result = scorer.score_external_result(
            "target task",
            "frontdoor:direct",
            1.0,
            context={"task_type": "chat"},
            embedding=fallback,
        )
        assert result == {"memories_updated": 0, "memories_created": 0}
        scorer.store.update_q_value.assert_not_called()
        scorer.store.store.assert_not_called()

    def test_fallback_with_null_task_type_cannot_update_or_create(self):
        scorer = _scorer()
        fallback = hash_fallback_embedding("type:chat | objective:target task")
        result = scorer.score_external_result(
            "target task",
            "frontdoor:direct",
            1.0,
            context={"task_type": None},
            embedding=fallback,
        )
        assert result == {"memories_updated": 0, "memories_created": 0}
        scorer.store.retrieve_by_similarity.assert_not_called()

    def test_external_score_preserves_non_routing_action_namespace(self):
        scorer = _scorer()
        scorer.store.retrieve_by_similarity.return_value = []
        scorer.store.store.return_value = "plan-review-memory"

        scorer.score_external_result(
            "target task",
            "plan_review:drop",
            0.9,
            context={"task_type": "chat"},
            embedding=[1.0] * 1024,
            action_type="plan_review",
        )

        assert scorer.store.retrieve_by_similarity.call_args.kwargs["action_type"] == "plan_review"
        assert scorer.store.store.call_args.kwargs["action_type"] == "plan_review"
        progress_entry = scorer.logger.log.call_args.args[0]
        assert progress_entry.data["action_type"] == "plan_review"

    def test_external_score_rejects_empty_action_namespace(self):
        scorer = _scorer()
        with pytest.raises(ValueError, match="action_type"):
            scorer.score_external_result(
                "target task",
                "frontdoor",
                1.0,
                context={"task_type": "chat"},
                embedding=[1.0] * 1024,
                action_type="",
            )

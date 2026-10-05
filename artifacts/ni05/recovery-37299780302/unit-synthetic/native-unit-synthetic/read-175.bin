#!/usr/bin/env python3
"""Tests for OpenClaw/Lobster concept integration.

Covers Phase 1A (side effects), Phase 1B (ToolOutput), Phase 2A (fallback),
Phase 3A (compaction state), and feature flag validation.
"""

from unittest.mock import patch

from src.features import Features
from src.roles import Role, FailoverReason, get_fallback_roles, _FALLBACK_MAP
from src.tool_registry import (
    SideEffect,
    Tool,
    ToolCategory,
    ToolOutput,
    ToolRegistry,
    ToolPermissions,
)
from src.api.health_tracker import BackendHealthTracker
from src.graph.state import TaskState

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"


def _registry_model_path(role: Role) -> str | None:
    """GGUF path the compiled registry declares for ``role`` (source of truth)."""
    from src.registry_loader import RegistryLoader

    try:
        return RegistryLoader().get_role(role.value).model.path
    except Exception:
        return None


# ============================================================================
# Phase 1A: Side Effect Declaration
# ============================================================================


class TestSideEffect:
    """Tests for SideEffect enum."""

    def test_values(self):
        assert SideEffect.LOCAL_EXEC == "local_exec"
        assert SideEffect.CALLS_LLM == "calls_llm"
        assert SideEffect.MODIFIES_FILES == "modifies_files"
        assert SideEffect.NETWORK_ACCESS == "network_access"
        assert SideEffect.SYSTEM_STATE == "system_state"
        assert SideEffect.READ_ONLY == "read_only"

    def test_str_enum(self):
        assert isinstance(SideEffect.LOCAL_EXEC, str)


class TestToolSideEffects:
    """Tests for Tool side_effects and destructive fields."""

    def test_default_empty(self):
        tool = Tool(
            name="test",
            description="Test",
            category=ToolCategory.DATA,
            parameters={},
        )
        assert tool.side_effects == []
        assert tool.destructive is False

    def test_with_side_effects(self):
        tool = Tool(
            name="exec_code",
            description="Execute code",
            category=ToolCategory.CODE,
            parameters={},
            side_effects=["local_exec", "modifies_files"],
            destructive=True,
        )
        assert tool.side_effects == ["local_exec", "modifies_files"]
        assert tool.destructive is True

    def test_list_tools_includes_side_effects(self):
        registry = ToolRegistry()
        tool = Tool(
            name="risky_tool",
            description="Risky",
            category=ToolCategory.SYSTEM,
            parameters={},
            side_effects=["system_state"],
            destructive=True,
        )
        registry.register_tool(tool)
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["side_effects"] == ["system_state"]
        assert tools[0]["destructive"] is True

    def test_list_tools_omits_empty_side_effects(self):
        registry = ToolRegistry()
        tool = Tool(
            name="safe_tool",
            description="Safe",
            category=ToolCategory.DATA,
            parameters={},
        )
        registry.register_tool(tool)
        tools = registry.list_tools()
        assert "side_effects" not in tools[0]
        assert "destructive" not in tools[0]


# ============================================================================
# Phase 1B: ToolOutput Structured Envelope
# ============================================================================


class TestToolOutput:
    """Tests for ToolOutput dataclass."""

    def test_success_output(self):
        out = ToolOutput(ok=True, status="success", output="result data")
        assert out.to_human() == "result data"
        machine = out.to_machine()
        assert machine["ok"] is True
        assert machine["status"] == "success"
        assert machine["output"] == "result data"

    def test_error_output(self):
        out = ToolOutput(ok=False, status="error", output="something broke")
        assert out.to_human() == "[ERROR] something broke"
        assert out.to_machine()["ok"] is False

    def test_pending_approval(self):
        out = ToolOutput(
            ok=True,
            status="pending_approval",
            requires_approval=True,
            side_effects_declared=["modifies_files", "system_state"],
        )
        human = out.to_human()
        assert "PENDING APPROVAL" in human
        assert "modifies_files" in human

    def test_none_output(self):
        out = ToolOutput(ok=True, output=None)
        assert out.to_human() == ""

    def test_protocol_version(self):
        out = ToolOutput()
        assert out.to_machine()["protocol_version"] == 1

    @patch("src.features.features")
    def test_invoke_returns_tool_output_when_enabled(self, mock_features):
        mock_features.return_value = Features(
            structured_tool_output=True, side_effect_tracking=False
        )

        registry = ToolRegistry()
        tool = Tool(
            name="double",
            description="Double",
            category=ToolCategory.DATA,
            parameters={"value": {"type": "integer", "required": True}},
            handler=lambda value: value * 2,
            side_effects=["local_exec"],
        )
        registry.register_tool(tool)
        registry.set_role_permissions(
            "test", ToolPermissions(allowed_categories=[ToolCategory.DATA])
        )

        result = registry.invoke("double", "test", value=5)
        assert isinstance(result, ToolOutput)
        assert result.ok is True
        assert result.output == 10
        assert result.side_effects_declared == ["local_exec"]

    @patch("src.features.features")
    def test_destructive_tool_pending_approval(self, mock_features):
        mock_features.return_value = Features(
            structured_tool_output=True, side_effect_tracking=True
        )

        registry = ToolRegistry()
        tool = Tool(
            name="delete_all",
            description="Delete everything",
            category=ToolCategory.SYSTEM,
            parameters={},
            handler=lambda: "deleted",
            side_effects=["modifies_files"],
            destructive=True,
        )
        registry.register_tool(tool)
        registry.set_role_permissions(
            "test", ToolPermissions(allowed_categories=[ToolCategory.SYSTEM])
        )

        result = registry.invoke("delete_all", "test")
        assert isinstance(result, ToolOutput)
        assert result.status == "pending_approval"
        assert result.requires_approval is True


# ============================================================================
# Phase 2A: Model Fallback
# ============================================================================


class TestFailoverReason:
    """Tests for FailoverReason enum."""

    def test_values(self):
        assert FailoverReason.CIRCUIT_OPEN == "circuit_open"
        assert FailoverReason.TIMEOUT == "timeout"
        assert FailoverReason.CONNECTION_ERROR == "connection_error"
        assert FailoverReason.OOM == "oom"


class TestFallbackMap:
    """Tests for get_fallback_roles()."""

    def test_architect_general_fallbacks(self):
        """The architect's infrastructure fallback must leave the failing backend.

        This asserted ``[CODER_ESCALATION]`` until the 2026-08-01 W1 cutover made
        coder_escalation an alias on architect_general's own :8083 process
        (registry: ``roles.coder_escalation.alias_of`` +
        ``server_mode.architect_general.shared_with``) — the fallback then retried
        the exact backend whose circuit had just opened. The property is asserted
        against the registry instead of re-pasting a role name.
        """
        roles = get_fallback_roles(Role.ARCHITECT_GENERAL)
        assert roles == list(_FALLBACK_MAP[Role.ARCHITECT_GENERAL])
        assert roles, "architect_general must declare a real fallback"
        for target in roles:
            assert _registry_model_path(target) != _registry_model_path(
                Role.ARCHITECT_GENERAL
            ), f"architect_general -> {target.value} serves the same GGUF"

    def test_every_fallback_edge_leaves_the_failing_model(self):
        """No declared fallback edge may point at the same physical model.

        Table-wide guard for the whole regression class rather than one literal:
        a same-model fallback retries the identical backend behind the identical
        (already-open) circuit — the ``forced_role_fallback`` churn WP-12 exists
        to remove.
        """
        checked = 0
        for role, targets in _FALLBACK_MAP.items():
            source_model = _registry_model_path(role)
            if source_model is None:
                continue
            for target in targets:
                target_model = _registry_model_path(target)
                assert target_model is not None, f"{target.value} is not registry-declared"
                assert target_model != source_model, (
                    f"{role.value} -> {target.value} falls back onto the same GGUF "
                    f"({source_model})"
                )
                checked += 1
        assert checked >= 4, "fallback table lost its edges — guard is vacuous"

    def test_coder_escalation_fallbacks(self):
        roles = get_fallback_roles(Role.CODER_ESCALATION)
        assert Role.FRONTDOOR in roles

    def test_frontdoor_no_fallbacks(self):
        roles = get_fallback_roles(Role.FRONTDOOR)
        assert roles == []

    def test_worker_vision_no_fallbacks(self):
        roles = get_fallback_roles(Role.WORKER_VISION)
        assert roles == []

    def test_ingest_fallback(self):
        """ingest_long_context falls back to a real process of its own.

        This asserted ``ARCHITECT_GENERAL in roles`` until the operator-signed
        2026-09-22 cutover (orchestrator 860b0b2d) made ingest_long_context an
        alias on architect_general's :8083 process, which turned that edge into a
        retry of the backend whose circuit had just opened. Asserted against the
        registry instead of by naming a role.
        """
        roles = get_fallback_roles(Role.INGEST_LONG_CONTEXT)
        assert roles, "ingest_long_context must declare a real fallback"
        for target in roles:
            assert _registry_model_path(target) != _registry_model_path(
                Role.INGEST_LONG_CONTEXT
            ), f"ingest_long_context -> {target.value} serves the same GGUF"

    def test_string_role(self):
        roles = get_fallback_roles("coder_escalation")
        assert Role.FRONTDOOR in roles

    def test_retired_architect_role_string_uses_live_architect_fallbacks(self):
        """A retired architect role string resolves to the LIVE architect's fallbacks.

        Asserted as the equivalence the test name claims, instead of re-encoding
        the fallback topology in a second place (which is what went stale when
        architect_general's fallback moved to architect_critic on 2026-08-01).
        """
        roles = get_fallback_roles(_RETIRED_ARCHITECT_ROLE)
        assert roles == get_fallback_roles(Role.ARCHITECT_GENERAL)
        assert roles, "the live architect must have a fallback for this to have teeth"

    def test_unknown_role(self):
        roles = get_fallback_roles("unknown_role")
        assert roles == []


class TestClassifyFailure:
    """Tests for BackendHealthTracker.classify_failure()."""

    def test_circuit_open(self):
        tracker = BackendHealthTracker()
        assert tracker.classify_failure("Backend unavailable (circuit open)") == "circuit_open"

    def test_timeout(self):
        tracker = BackendHealthTracker()
        assert tracker.classify_failure("Request timed out after 300s") == "timeout"

    def test_oom(self):
        tracker = BackendHealthTracker()
        assert tracker.classify_failure("Out of memory: KV cache exhausted") == "oom"

    def test_connection_error(self):
        tracker = BackendHealthTracker()
        assert tracker.classify_failure("Connection refused") == "connection_error"

    def test_generic_error(self):
        tracker = BackendHealthTracker()
        assert tracker.classify_failure("Something went wrong") == "connection_error"


# ============================================================================
# Phase 3A: Session Compaction State
# ============================================================================


class TestTaskStateCompaction:
    """Tests for compaction_count and new state fields."""

    def test_default_compaction_count(self):
        state = TaskState()
        assert state.compaction_count == 0

    def test_default_resume_token(self):
        state = TaskState()
        assert state.resume_token == ""

    def test_default_pending_approval(self):
        state = TaskState()
        assert state.pending_approval is None


# ============================================================================
# Feature Flag Validation
# ============================================================================


class TestFeatureValidation:
    """Tests for new feature flag validation rules."""

    def test_approval_gates_requires_resume_tokens(self):
        f = Features(approval_gates=True, resume_tokens=False, side_effect_tracking=True)
        errors = f.validate()
        assert any("approval_gates" in e and "resume_tokens" in e for e in errors)

    def test_approval_gates_requires_side_effect_tracking(self):
        f = Features(approval_gates=True, resume_tokens=True, side_effect_tracking=False)
        errors = f.validate()
        assert any("approval_gates" in e and "side_effect_tracking" in e for e in errors)

    def test_approval_gates_valid_when_deps_met(self):
        f = Features(approval_gates=True, resume_tokens=True, side_effect_tracking=True)
        errors = f.validate()
        approval_errors = [e for e in errors if "approval_gates" in e]
        assert len(approval_errors) == 0

    def test_binding_routing_standalone(self):
        f = Features(binding_routing=True)
        errors = f.validate()
        binding_errors = [e for e in errors if "binding_routing" in e]
        assert len(binding_errors) == 0

    def test_new_flags_in_summary(self):
        f = Features()
        summary = f.summary()
        assert "side_effect_tracking" in summary
        assert "structured_tool_output" in summary
        assert "model_fallback" in summary
        assert "content_cache" in summary
        assert "session_compaction" in summary
        assert "depth_model_overrides" in summary
        assert "resume_tokens" in summary
        assert "approval_gates" in summary
        assert "binding_routing" in summary

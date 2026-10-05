"""Tests for internal interaction lifecycle primitives."""

from src.orchestration.interaction import (
    INTERACTION_POLICY_VERSION,
    ArtifactRef,
    Interaction,
    InteractionTelemetry,
    SchedulerPolicy,
)


class _Primitives:
    def get_request_priority(self) -> str:
        return "background"

    def get_request_workload_class(self) -> str:
        return "eval_batch"

    def get_max_queue_wait_ms(self) -> int:
        return 1234

    def get_migration_budget_ms(self) -> int:
        return 55


def test_scheduler_policy_wraps_existing_request_context_fields() -> None:
    policy = SchedulerPolicy.from_primitives(_Primitives(), cancellable=True)

    assert policy.priority == "background"
    assert policy.workload_class == "eval_batch"
    assert policy.max_queue_wait_ms == 1234
    assert policy.migration_budget_ms == 55
    assert policy.cancellable is True
    assert policy.request_context_kwargs() == {
        "priority": "background",
        "workload_class": "eval_batch",
        "max_queue_wait_ms": 1234,
        "migration_budget_ms": 55,
    }


def test_interaction_state_transitions_and_event_payload() -> None:
    interaction = Interaction(
        kind="delegate",
        owner_role="architect_general",
        callee_role="worker_general",
        skill="architect_delegation",
        telemetry=InteractionTelemetry(
            interaction_type="delegate",
            skill="architect_delegation",
        ),
    )

    assert interaction.state == "created"
    interaction.start()
    assert interaction.state == "working"

    event = interaction.emit_event(
        to_role="worker_math",
        task_summary="inspect failure",
        success=True,
        elapsed_ms=12.0,
        tokens_generated=34,
        metadata={"inference_meta": {"transport": "chat"}},
    )
    assert interaction.events == [event]
    assert event.to_delegation_event_payload() == {
        "from_role": "architect_general",
        "to_role": "worker_math",
        "task_summary": "inspect failure",
        "interaction_type": "delegate",
        "success": True,
        "elapsed_ms": 12.0,
        "tokens_generated": 34,
        "inference_meta": {"transport": "chat"},
    }

    interaction.complete(artifact=ArtifactRef(kind="report", ref="r1"))
    assert interaction.state == "completed"
    assert interaction.artifacts[0].ref == "r1"


def test_interaction_telemetry_policy_version() -> None:
    telemetry = InteractionTelemetry(interaction_type="consult", skill="review")

    assert telemetry.as_dict() == {
        "interaction_type": "consult",
        "skill": "review",
        "context_hash": "",
        "interaction_policy_version": INTERACTION_POLICY_VERSION,
    }

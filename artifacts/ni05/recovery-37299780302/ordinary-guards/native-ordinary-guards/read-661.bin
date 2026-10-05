from __future__ import annotations

from scripts.maintenance.repair_episodic_routing_poison import classify_namespace


LIVE = {"frontdoor", "worker_general", "architect_general"}


def test_plan_review_control_actions_move_to_own_namespace() -> None:
    assert (
        classify_namespace("plan_review:drop", "routing", {}, LIVE)
        == "plan_review"
    )


def test_proven_escalation_moves_to_escalation_namespace() -> None:
    context = {"metrics": {"action_type": "escalation"}}
    assert (
        classify_namespace(
            "escalate:worker_general->architect_general",
            "routing",
            context,
            LIVE,
        )
        == "escalation"
    )


def test_nonserving_and_empty_routes_are_quarantined() -> None:
    assert (
        classify_namespace("plan_review", "routing", {}, LIVE)
        == "quarantined_invalid_route"
    )
    assert (
        classify_namespace("", "routing", {}, LIVE)
        == "quarantined_invalid_route"
    )


def test_live_route_and_other_namespaces_are_unchanged() -> None:
    assert classify_namespace("frontdoor:direct", "routing", {}, LIVE) is None
    assert classify_namespace("plan_review:drop", "plan_review", {}, LIVE) is None

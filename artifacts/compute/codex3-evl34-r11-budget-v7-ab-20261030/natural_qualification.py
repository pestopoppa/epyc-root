"""Refuse the pilot unless the sealed control contains a real native delegation."""

import hashlib
import json
from pathlib import Path

from paired_journal import encoded


def event_qualification(events):
    if not isinstance(events, list):
        return False
    roots = [
        e
        for e in events
        if isinstance(e, dict)
        and e.get("type") == "kani_spawn"
        and e.get("depth") == 0
        and e.get("parent") is None
        and isinstance(e.get("id"), str)
    ]
    if len(roots) != 1:
        return False
    root = roots[0]["id"]
    calls = []
    children = []
    delegated = []
    for i, event in enumerate(events):
        if not isinstance(event, dict):
            return False
        if event.get("type") == "kani_message" and event.get("id") == root:
            msg = event.get("msg") or {}
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                for call in msg.get("tool_calls") or []:
                    if (
                        isinstance(call, dict)
                        and (call.get("function") or {}).get("name") == "delegate"
                    ):
                        calls.append(i)
        if (
            event.get("type") == "kani_spawn"
            and event.get("depth") == 1
            and event.get("parent") == root
            and isinstance(event.get("id"), str)
        ):
            children.append((i, event["id"]))
        if event.get("type") == "kani_delegated" and event.get("parent_id") == root:
            delegated.append((i, event.get("child_id")))
    return any(
        call < spawn <= decision and child == delegated_child
        for call in calls
        for spawn, child in children
        for decision, delegated_child in delegated
    )


def inspect_control(journal, declaration_sha, control, prompt_sha):
    identity = {
        "campaign_sha256": declaration_sha,
        "id": control["id"],
        "arm": "redel_delegate_wait",
        "prompt_sha256": prompt_sha,
    }
    key = hashlib.sha256(
        encoded(
            {
                "campaign_sha256": declaration_sha,
                "id": control["id"],
                "arm": identity["arm"],
            }
        )
    ).hexdigest()
    start, end = Path(journal) / (key + ".start"), Path(journal) / (key + ".end")
    if not start.is_file() or not end.is_file():
        return {"qualified": False, "reason": "control_missing_or_unknown"}
    start_bytes, end_bytes = start.read_bytes(), end.read_bytes()
    initial, result = json.loads(start_bytes), json.loads(end_bytes)
    if (
        initial.get("identity") != identity
        or result.get("identity") != identity
        or result.get("start_sha256") != hashlib.sha256(start_bytes).hexdigest()
        or result.get("status") != "complete"
    ):
        raise ValueError("control journal identity mismatch")
    native = result.get("native") or {}
    if (
        native.get("status") != "complete"
        or native.get("flat_server_bound_attested") is not True
    ):
        return {"qualified": False, "reason": "native_route_incomplete"}
    qualified = event_qualification(native.get("native_events"))
    return {
        "qualified": qualified,
        "reason": "delegate_and_linked_child_observed"
        if qualified
        else "no_matched_natural_delegate_and_child",
        "control_id": control["id"],
        "end_sha256": hashlib.sha256(end_bytes).hexdigest(),
    }

"""Bind one native CH-26 capture receipt to one serving request boundary.

The join authenticates neither perf source completeness nor inference exclusion.
It only checks that the request owner retained a native receipt whose target,
phase identity and authenticated marker times match this serving request.
"""
from __future__ import annotations

import re

SCHEMA = "epyc.ch26.observer_request_receipt.v1"
_SHA = re.compile(r"^[0-9a-f]{64}$")


def validate_receipt(receipt, *, request_context, target, placement_window_ns):
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        raise ValueError("native request observer receipt missing or schema differs")
    if receipt.get("status") != "unproven" or receipt.get("measurement_admission") != "none":
        raise ValueError("native observer receipt scope/admission differs")
    if receipt.get("placement") != "unproven" or receipt.get("contention") != "unproven":
        raise ValueError("native observer receipt overstates placement/contention")
    if receipt.get("request_context") != request_context:
        raise ValueError("native observer receipt request context mismatch")
    if (not isinstance(request_context, dict)
            or type(request_context.get("launch_ordinal")) is not int
            or request_context["launch_ordinal"] <= 0
            or request_context.get("phase") not in ("warmup", "measurement")
            or type(request_context.get("slot_index")) is not int
            or request_context["slot_index"] != 0
            or not isinstance(request_context.get("prompt_id"), str)
            or not request_context["prompt_id"].strip()
            or not isinstance(request_context.get("request_sha256"), str)
            or not _SHA.fullmatch(request_context["request_sha256"])):
        raise ValueError("native observer request context malformed")
    digest = receipt.get("evidence_sha256")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("native observer evidence digest missing")
    if receipt.get("observer_id") != "ch26:" + digest:
        raise ValueError("native observer receipt ID is not bound to evidence digest")
    path = receipt.get("evidence_path")
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("native observer evidence path is not absolute")
    window = receipt.get("request_window_ns")
    if (not isinstance(window, list) or len(window) != 2
            or any(type(x) is not int for x in window)
            or not window[0] < window[1]):
        raise ValueError("native observer request marker window is invalid")
    outer = placement_window_ns
    if (not isinstance(outer, list) or len(outer) != 2
            or any(type(x) is not int for x in outer)
            or not outer[0] < outer[1]
            or not outer[0] <= window[0] < window[1] <= outer[1]):
        raise ValueError("native observer timestamps fall outside serving boundary")
    markers = receipt.get("markers")
    if not isinstance(markers, list) or len(markers) != 2:
        raise ValueError("native observer marker pair missing")
    begin, end = markers
    expected_owner_keys = ("pid", "uid", "start_ticks", "boot_id")
    if (not isinstance(begin, dict) or not isinstance(end, dict)
            or (begin.get("kind"), begin.get("seq"), end.get("kind"), end.get("seq"))
            != ("begin", 1, "end", 2)):
        raise ValueError("native observer marker order differs")
    if any(begin.get(k) != end.get(k) for k in expected_owner_keys):
        raise ValueError("native observer owner identity changed")
    if (type(begin.get("pid")) is not int or begin["pid"] <= 0
            or type(begin.get("uid")) is not int or begin["uid"] < 0
            or type(begin.get("start_ticks")) is not int or begin["start_ticks"] < 0
            or not isinstance(begin.get("boot_id"), str) or not begin["boot_id"]):
        raise ValueError("native observer owner identity is malformed")
    if (type(begin.get("timestamp_ns")) is not int
            or type(end.get("timestamp_ns")) is not int
            or type(begin.get("received_ns")) is not int
            or type(end.get("received_ns")) is not int
            or begin["received_ns"] < begin["timestamp_ns"]
            or end["received_ns"] < end["timestamp_ns"]
            or [begin["timestamp_ns"], end["timestamp_ns"]] != window):
        raise ValueError("native observer timestamps differ from receipt window")
    identity = receipt.get("target_identity")
    expected_target = {key: target.get(key) for key in ("pid", "start_ticks", "boot_id")}
    if identity != expected_target:
        raise ValueError("native observer target identity differs from serving target")
    observations = receipt.get("target_observations")
    if not isinstance(observations, list) or len(observations) < 3:
        raise ValueError("native observer target snapshots missing")
    if any(item != expected_target for item in observations):
        raise ValueError("native observer target identity changed during request")
    return {"schema": SCHEMA, "observer_id": receipt["observer_id"],
            "evidence_path": path, "evidence_sha256": digest,
            "request_context": request_context,
            "request_window_ns": list(window), "markers": markers,
            "target_identity": identity, "target_observations": observations,
            "owner_identity": {
                key: begin[key] for key in expected_owner_keys},
            "status": "unproven", "measurement_admission": "none",
            "placement": "unproven", "contention": "unproven"}


def join_event(event, receipt):
    """Validate and attach a receipt, retaining conservative claim fields."""
    if not isinstance(event, dict):
        raise ValueError("serving request event is not an object")
    context = {key: event.get(key) for key in
               ("launch_ordinal", "phase", "slot_index", "prompt_id", "request_sha256")}
    target = event.get("target")
    joined = validate_receipt(receipt, request_context=context, target=target,
                              placement_window_ns=event.get("placement_window_ns"))
    event_copy = dict(event)
    if "native_observer" in event_copy:
        raise ValueError("duplicate native observer attachment")
    event_copy["native_observer"] = joined
    event_copy["placement_continuous"] = "unproven"
    event_copy["contention_continuous"] = "unproven"
    event_copy["measurement_admission"] = "none"
    return event_copy

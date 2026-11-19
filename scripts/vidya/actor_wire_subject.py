"""Unregistered actor-wire operational subject identity; no selection/admissibility policy.

The failed 2026-11-04 planner canary used model applicability for an operational
verifier finding. This module names the captured producer/request instead. It does
NOT expose ledger findings to planners, decide whether a finding is usable, or
claim that a matching request passed. Future integration must preserve the shared
folded ledger verification, refutation and grading rules before presenting evidence.

Only native adapter rows are accepted. The existing strict adapter re-reads the
original finalization and seat evidence; no post-hoc model/device scope is added.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from adapters import autokernel_actor_wire as wire
from claim_tuple import ProjectionError

SUBJECT_SCHEMA = "epyc.vidya.actor_wire_subject.v1"
_FIELDS = {"schema", "producer", "request", "seat_digest", "subject_sha256"}
_HEX = re.compile(r"^[0-9a-f]{64}$")


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise ProjectionError("actor-wire subject: " + reason)


def validate_subject(subject: Any) -> None:
    """Check the identity carrier only. This is neither proof nor admissibility."""
    _need(isinstance(subject, dict) and set(subject) == _FIELDS, "missing/unknown fields")
    _need(subject["schema"] == SUBJECT_SCHEMA, "foreign schema")
    producer = subject["producer"]
    _need(isinstance(producer, dict) and set(producer) == wire.PRODUCER_FIELDS,
          "producer identity fields differ")
    _need(all(isinstance(v, str) and v for v in producer.values()), "empty producer identity")
    request = subject["request"]
    _need(isinstance(request, dict) and set(request) == wire.REQUEST_FIELDS,
          "request identity fields differ")
    _need(request["schema"] == wire.WIRE_SCHEMA, "foreign request schema")
    seats = request["seats"]
    _need(isinstance(seats, list) and bool(seats) and all(isinstance(s, dict) for s in seats),
          "missing captured seats")
    try:
        keys = [wire.digest(seat) for seat in seats]
        _need(keys == sorted(set(keys)), "seats not unique and normalized")
        _need(request["actor_config_digest"] == wire.digest(seats), "actor config digest differs")
        suite = request["suite"]
        _need(isinstance(suite, dict) and bool(suite)
              and all(isinstance(k, str) and k and isinstance(v, str) and _HEX.fullmatch(v)
                      for k, v in suite.items()), "suite source digests malformed")
        _need(subject["seat_digest"] is None or subject["seat_digest"] in keys,
              "selected seat not in original request")
        body = {k: v for k, v in subject.items() if k != "subject_sha256"}
        _need(subject["subject_sha256"] == wire.digest(body), "subject digest differs")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError("actor-wire subject: noncanonical identity") from exc


def subject_for_native(native: dict) -> dict:
    """Name one original matrix or seat row after the strict adapter re-reads it.

    Whole request/config/suite/producer equality is intentional. A seat in a changed
    matrix does not silently inherit a prior matrix's finding. Full captured seat
    objects preserve provider model/client/role/launch/timeout identity without
    turning them into inference-model applicability.
    """
    wire.project(native)  # existing native validation only; no grade or result filtering
    record = native["record"]
    body = {"schema": SUBJECT_SCHEMA, "producer": copy.deepcopy(record["producer"]),
            "request": copy.deepcopy(record["request"]),
            "seat_digest": native.get("seat_digest") if native["kind"] == "seat" else None}
    subject = {**body, "subject_sha256": wire.digest(body)}
    validate_subject(subject)
    return subject


def matches_native(subject: dict, native: dict) -> bool:
    """Exact identity match, including matrix/seat grain; never means usable/PASS.

    Malformed/tampered source or subject raises rather than disappearing as a miss.
    A well-formed identity mismatch returns False. Outcome, date and record digest
    are outside the identity key: PASS/FAIL reruns can concern the same subject;
    the shared folded evidence policy must reconcile them, never this matcher.
    """
    validate_subject(subject)
    return subject == subject_for_native(native)


__all__ = ["SUBJECT_SCHEMA", "validate_subject", "subject_for_native", "matches_native"]

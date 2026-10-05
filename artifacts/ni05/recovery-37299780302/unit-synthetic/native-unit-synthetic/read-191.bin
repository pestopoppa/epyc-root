#!/usr/bin/env python3
"""SC19 (EVL-47) — the producer-written contention-gate capture hook.

The A14 residual echoes the contention GateDecision into every /chat response; this hook
persists that echo, one request-keyed envelope per JSONL line, for the vidya belief kernel.

What is pinned here, in the order this program has been burned:

* capture is **opt-in** — the orchestrator is a production serving path, so the default is
  OFF and the env var is the only switch;
* one request = one envelope even when the gate ran more than once — the locator trap:
  a per-decision line would read one request as N witnesses;
* a `None` payload (no gate ran) writes nothing — an untouched gate is not a measurement;
* a capture failure never raises and never breaks the serving path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from src.scheduling import contention_gate_capture as capture_hook

ENV_VAR = "ORCHESTRATOR_CONTENTION_GATE_CAPTURE"

PAYLOAD = {
    "gate_decisions": [
        {
            "admitted": True,
            "decision": "allow",
            "waited_s": 0.0,
            "candidate_topology_idx": 1,
            "queued_then_admitted": False,
        }
    ],
    "admitted": True,
    "decision": "allow",
    "waited_s": 0.0,
    "candidate_topology_idx": 1,
    "queued_then_admitted": False,
}


def teardown_function() -> None:
    os.environ.pop(ENV_VAR, None)


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_capture_is_opt_in_by_default(tmp_path):
    """No env var -> no file, even with a payload. The serving path must not accumulate."""
    path = tmp_path / "capture.jsonl"
    assert "ORCHESTRATOR_CONTENTION_GATE_CAPTURE" not in os.environ
    assert capture_hook.capture(PAYLOAD, request_id="req-1") is False
    assert not path.exists()


def test_capture_writes_one_envelope_row(tmp_path):
    os.environ[ENV_VAR] = str(tmp_path / "capture.jsonl")
    assert capture_hook.capture(PAYLOAD, request_id="api-abc123") is True

    rows = _read_rows(tmp_path / "capture.jsonl")
    assert len(rows) == 1
    row = rows[0]
    assert row["capture_schema"] == "contention_gate_capture.v1"
    assert row["request_id"] == "api-abc123"
    assert row["ts_utc"]
    assert row["decision_count"] == 1
    assert row["admitted"] is True
    assert row["waited_s"] == 0.0
    assert row["candidate_topology_idx"] == 1
    assert row["gate_decisions"][0]["decision"] == "allow"


def test_request_with_two_decisions_writes_one_row(tmp_path):
    """The locator trap, pinned at the write site: N decisions in ONE request-keyed row."""
    multi = dict(PAYLOAD)
    multi["gate_decisions"] = [
        {
            "admitted": False,
            "decision": "block",
            "waited_s": 0.0,
            "candidate_topology_idx": 3,
            "blocking_roles": ["worker_general"],
            "queued_then_admitted": False,
        },
        {
            "admitted": True,
            "decision": "allow",
            "waited_s": 0.4,
            "candidate_topology_idx": 2,
            "queued_then_admitted": True,
        },
    ]
    multi["decision"] = "allow"
    multi["admitted"] = True
    multi["waited_s"] = 0.4

    os.environ[ENV_VAR] = str(tmp_path / "capture.jsonl")
    assert capture_hook.capture(multi, request_id="api-multi-1") is True

    rows = _read_rows(tmp_path / "capture.jsonl")
    assert len(rows) == 1, "one request must produce exactly one capture row"
    assert rows[0]["request_id"] == "api-multi-1"
    assert rows[0]["decision_count"] == 2
    assert len(rows[0]["gate_decisions"]) == 2
    assert rows[0]["gate_decisions"][0]["blocking_roles"] == ["worker_general"]
    assert rows[0]["gate_decisions"][1]["queued_then_admitted"] is True


def test_none_payload_writes_nothing(tmp_path):
    """No gate ran -> the echo is None -> nothing to measure, so no row."""
    path = tmp_path / "capture.jsonl"
    os.environ[ENV_VAR] = str(path)
    assert capture_hook.capture(None, request_id="api-abc123") is False
    assert not path.exists()


def test_capture_failure_does_not_raise(tmp_path):
    """A capture failure must never break the serving path."""
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("i am a file, not a directory")
    os.environ[ENV_VAR] = str(blocker / "capture.jsonl")

    assert capture_hook.capture(PAYLOAD, request_id="api-abc123") is False
    # The caller's path is unaffected: the hook returned, nothing raised.


def test_rows_append_across_requests(tmp_path):
    os.environ[ENV_VAR] = str(tmp_path / "capture.jsonl")
    assert capture_hook.capture(PAYLOAD, request_id="api-1") is True
    assert capture_hook.capture(PAYLOAD, request_id="api-2") is True
    rows = _read_rows(tmp_path / "capture.jsonl")
    assert [r["request_id"] for r in rows] == ["api-1", "api-2"]

"""SC19 / EVL-47 — the contention-gate capture reader.

What is pinned here, in the order this program has been burned:

* the **locator rule** — one claim per REQUEST, never per decision; a multi-decision
  request produces exactly ONE tuple (a naive per-decision projection would read one
  request as N independent witnesses);
* the **honest-zero state** — an absent/empty capture is not a measurement: zero tuples,
  reported as "no emissions", never fabricated;
* the ladder is not reimplemented — every grade asserted below is whatever
  ``claim_tuple.grade()`` actually returns for the projected tuple;
* a malformed capture is inadmissible as a whole and reports why, without crashing;
* attestation is anchored, not attested — the capture is an off-tree append-only log whose
  producer pins no digest at collect time, so the honest grade is ``Witnessed/Anchored``
  until a producer-authored envelope hash exists.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import contention_gate as reader  # noqa: E402


def envelope(**overrides) -> dict:
    row = {
        "capture_schema": "contention_gate_capture.v1",
        "request_id": "api-abc123",
        "ts_utc": "2026-08-23T12:00:00Z",
        "gate_decisions": [{
            "admitted": True, "decision": "allow", "waited_s": 0.0,
            "candidate_topology_idx": 1, "queued_then_admitted": False,
        }],
        "decision_count": 1,
        "admitted": True,
        "waited_s": 0.0,
        "candidate_topology_idx": 1,
    }
    row.update(overrides)
    return row


def write_capture(path: Path, *rows: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


# --- projection + the shared ladder --------------------------------------------------------

def test_single_decision_request_projects_one_claim_graded_anchored(tmp_path):
    capture = write_capture(tmp_path / "capture.jsonl", envelope())
    natives = reader.native_rows(capture)
    assert len(natives) == 1

    tup = reader.project(natives[0])
    assert tup.measurement_id == "cg_api-abc123"
    assert tup.value == "admitted_immediately"
    assert tup.protocol_id == "contention_gate_capture.v1"
    assert tup.reps == 1 and tup.reps_basis == "requests"
    assert tup.category == "BASELINE"
    assert tup.attestation_locator == str(capture)

    q, t, reasons = ct.grade(tup)
    # The capture is an off-tree append-only log with no producer-pinned digest at collect
    # time: the ladder's honest answer is anchored, not attested.
    assert (q, t) == ("Witnessed", "Anchored"), reasons
    assert any("not hashed" in r for r in reasons)


def test_multi_decision_request_projects_exactly_one_claim(tmp_path):
    """The locator trap, pinned: N decisions in one request = ONE witness, not N."""
    row = envelope(
        request_id="api-multi-1",
        gate_decisions=[
            {"admitted": False, "decision": "block", "waited_s": 0.0,
             "candidate_topology_idx": 3, "blocking_roles": ["worker_general"],
             "queued_then_admitted": False},
            {"admitted": True, "decision": "allow", "waited_s": 0.4,
             "candidate_topology_idx": 2, "queued_then_admitted": True},
        ],
        decision_count=2,
        admitted=True,
        waited_s=0.4,
        candidate_topology_idx=2,
    )
    capture = write_capture(tmp_path / "capture.jsonl", row)

    natives = reader.native_rows(capture)
    assert len(natives) == 1, "one request must produce exactly one native row"
    tup = reader.project(natives[0])
    assert tup.measurement_id == "cg_api-multi-1"
    assert tup.extra["decision_count"] == 2
    assert len(tup.extra["gate_decisions"]) == 2
    assert tup.extra["gate_decisions"][0]["blocking_roles"] == ["worker_general"]
    frames = reader.frames_for_capture(capture, as_of="2026-08-23T13:00:00Z")
    assert len([f for f in frames if f["frame_type"].endswith("claim_proposed/v1")]) == 1


def test_three_requests_produce_three_request_keyed_claims(tmp_path):
    capture = write_capture(
        tmp_path / "capture.jsonl",
        envelope(request_id="api-1"),
        envelope(request_id="api-2", admitted=True, waited_s=2.5,
                 gate_decisions=[{"admitted": True, "decision": "allow", "waited_s": 2.5,
                                  "queued_then_admitted": True}], decision_count=1),
        envelope(request_id="api-3", admitted=False,
                 gate_decisions=[{"admitted": False, "decision": "block", "waited_s": 0.0,
                                  "queued_then_admitted": False}], decision_count=1),
    )
    natives = reader.native_rows(capture)
    ids = [reader.project(n).measurement_id for n in natives]
    assert len(ids) == 3 and len(set(ids)) == 3, "distinct requests merged into one claim"
    for native in natives:
        tup = reader.project(native)
        assert tup.reps == 3, "reps counts the requests the capture scored"
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Witnessed", "Anchored"), reasons


# --- the measured verdict ------------------------------------------------------------------

def test_queued_then_admitted_is_a_measured_verdict(tmp_path):
    """The state the 503-timeout proxy structurally cannot see — now a direct measurement."""
    capture = write_capture(
        tmp_path / "capture.jsonl",
        envelope(admitted=True, waited_s=2.5,
                 gate_decisions=[{"admitted": True, "decision": "allow", "waited_s": 2.5,
                                  "candidate_topology_idx": 2, "queued_then_admitted": True}],
                 decision_count=1, candidate_topology_idx=2),
    )
    tup = reader.project(reader.native_rows(capture)[0])
    assert tup.value == "queued_then_admitted"
    assert tup.extra["queued_then_admitted"] is True
    assert "measured directly" in tup.claim
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_blocked_request_is_a_measured_verdict(tmp_path):
    capture = write_capture(
        tmp_path / "capture.jsonl",
        envelope(admitted=False,
                 gate_decisions=[{"admitted": False, "decision": "block", "waited_s": 0.0,
                                  "reason": "overlap", "queued_then_admitted": False}],
                 decision_count=1),
    )
    tup = reader.project(reader.native_rows(capture)[0])
    assert tup.value == "blocked"
    assert tup.extra["queued_then_admitted"] is False


# --- honest zero: an empty capture is not a measurement ------------------------------------

def test_absent_capture_reports_no_emissions_and_projects_nothing(tmp_path):
    capture = tmp_path / "capture.jsonl"
    assert reader.native_rows(capture) == ()
    assert reader.refusal_reason(capture) == "no emissions"
    assert reader.frames_for_capture(capture, as_of="2026-08-23T13:00:00Z") == []


def test_empty_capture_reports_no_emissions_and_projects_nothing(tmp_path):
    capture = write_capture(tmp_path / "capture.jsonl")
    assert reader.native_rows(capture) == ()
    assert reader.refusal_reason(capture) == "no emissions"
    # The row must stay candidate — no tuple is fabricated from an empty file.
    assert reader.frames_for_capture(capture, as_of="2026-08-23T13:00:00Z") == []


# --- strictness ----------------------------------------------------------------------------

def test_malformed_capture_refuses_with_reason_and_no_crash(tmp_path):
    capture = tmp_path / "capture.jsonl"
    write_capture(capture, envelope())
    with open(capture, "a") as f:
        f.write("{not json\n")
    assert reader.native_rows(capture) == ()
    assert reader.refusal_reason(capture).startswith("malformed")

    # A schema-mismatched envelope also voids the whole file.
    write_capture(capture, envelope(), envelope(capture_schema="something.else/v1"))
    assert reader.native_rows(capture) == ()
    assert "malformed" in reader.refusal_reason(capture)

    # A decision_count mismatch is producer corruption, not a partial run.
    write_capture(capture, envelope(decision_count=2))
    assert reader.native_rows(capture) == ()
    assert "decision_count" in reader.refusal_reason(capture)


def test_project_rejects_bare_or_mutated_native(tmp_path):
    capture = write_capture(tmp_path / "capture.jsonl", envelope())
    native = reader.native_rows(capture)[0]
    tampered = {**native, "row": {**native["row"], "waited_s": "not-a-number"}}
    with pytest.raises(ct.ProjectionError):
        reader.project(tampered)
    with pytest.raises(ct.ProjectionError):
        reader.project({"row": envelope()})  # bypassing native_rows: no request_count
    with pytest.raises(ct.ProjectionError):
        reader.project(native["row"])  # bypassing native_rows entirely


def test_missing_attestation_grades_down_through_the_ladder(tmp_path):
    """A tuple with no attestation reference is a result, not decision-gating."""
    native = {"row": envelope(), "request_count": 1}
    tup = reader.project(native)
    assert tup.attestation_locator == ""
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Verified", "Located"), reasons
    assert any("no attestation reference" in r for r in reasons)


# --- carrier conformance -------------------------------------------------------------------

def test_projection_is_registered_under_the_shared_registry():
    assert "contention-gate-measurement" in ct.registered()


def test_frames_go_through_the_shared_emitter(tmp_path):
    capture = write_capture(
        tmp_path / "capture.jsonl",
        envelope(request_id="api-1"),
        envelope(request_id="api-2"),
    )
    frames = reader.frames_for_capture(capture, as_of="2026-08-23T13:00:00Z")
    assert len(frames) == 6  # 2 requests x (source, claim, support)
    supports = [f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1")]
    assert len(supports) == 2
    for sup in supports:
        assert sup["assertion"]["grade"] == {"Q": "Witnessed", "T": "Anchored"}
        assert sup["assertion"]["protocol_id"] == "contention_gate_capture.v1"
        assert sup["assertion"]["reps"] == 2
        assert sup["assertion"]["category"] == "BASELINE"
    assert len({f["assertion"]["claim_id"] for f in frames
                if f["frame_type"].endswith("claim_proposed/v1")}) == 2

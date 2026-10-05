"""Unit tests for the ROUTE-A1 shape-keyed Step-2 smoke execution bridge.

Covers the two placement-queue drivers (``_drive_admit_overlap_probes`` and
``_drive_rebench_pairs``) via INJECTED probe/sample callables, the admit-vs-queue
classifier, ``execute_step2_smoke``'s aggregation + artifact write, and the
double-gate dry-run fallback. NOTHING here touches a network, a model, or a live
port, and NO test ever sets ``AUTOPILOT_SHAPEKEYED_STEP2_SMOKE`` with a real
transport — every execute path is driven with synthetic injected callables.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.autopilot import shapekeyed_step2_smoke as sk

# Synthetic (role, idx) -> region-set topology. anchor = ingest#1 {q0,q1}
# (node0-half — the corrected default: quarters do not exist in production;
# idx 0 is the FULL 96t shape, idx 1/2 the 48t halves). Chosen so the default
# probe roles yield a known admit/queue mix and vision_escalation exposes
# several disjoint within-role pairs for re-bench.
SYNTH_REGIONS: dict[tuple[str, int], frozenset[str]] = {
    ("ingest_long_context", 1): frozenset({"q0", "q1"}),          # anchor
    ("frontdoor", 0): frozenset({"q0", "q1"}),                    # overlap -> QUEUE
    ("vision_escalation", 0): frozenset({"q2", "q3"}),            # disjoint -> ADMIT
    ("vision_escalation", 1): frozenset({"q2"}),                  # disjoint -> ADMIT
    ("vision_escalation", 2): frozenset({"q3"}),                  # disjoint -> ADMIT
    ("vision_escalation", 3): frozenset({"q0"}),                  # overlap -> QUEUE
    ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),   # overlap -> QUEUE
}
# The SYNTH anchor is passed EXPLICITLY. The module defaults are derived from the
# LIVE lineup (registry server_mode + NUMA_CONFIG) since 2026-09-26, so they name
# roles this synthetic topology does not contain.
SYNTH_ANCHOR = ("ingest_long_context", 1)


def _plan(expectation: str = sk.DEFAULT_EXPECTATION) -> sk.Step2SmokePlan:
    # Explicit probe roles including vision_escalation: the SYNTH fixture exists
    # to exercise the classifier machinery with a balanced admit/queue mix. The
    # production DEFAULT_PROBE_ROLES intentionally excludes vision_escalation
    # (GPU-served, no CPU-region instance — 2026-08-23).
    return sk.build_step2_smoke_plan(
        SYNTH_REGIONS,
        topology_hash="test-topo",
        anchor=SYNTH_ANCHOR,
        probe_roles=("frontdoor", "ingest_long_context", "vision_escalation", "worker_general"),
        expectation=expectation,
    )


def _anchor_held() -> dict[str, list[int]]:
    """Injected anchor-hold scan: the SYNTH anchor (ingest_long_context#1) is held."""
    return {"ingest_long_context": [1]}


# ── admit/queue classifier ────────────────────────────────────────────────────


def test_classify_admit_queue_signal_matrix() -> None:
    c = sk._classify_admit_queue
    # A clean answer with no error => admit.
    assert c({"answer": "OK", "predicted_tps": 40.0}) == sk.DECISION_ADMIT
    # The contention gate's 503 body (parsed) => queue via the "contention" marker.
    assert c({"error": "contention_denied", "detail": "x", "retry_after_s": 5}) == sk.DECISION_QUEUE
    # The same 503 surfaced through call_orchestrator_forced's raise_for_status
    # (empty answer, httpx status string) => queue via the bare-503 rule.
    assert (
        c({"answer": "", "error": "Server error '503 Service Unavailable' for url 'http://localhost:8000/chat'"})
        == sk.DECISION_QUEUE
    )
    # The dispatcher's ContentionDenied reason string => queue.
    assert c({"answer": "", "error": "placement timeout role=frontdoor after 90.0s"}) == sk.DECISION_QUEUE
    # A circuit-open 503 arrives as an [ERROR: ... unavailable] answer + error_code:
    # NOT gate evidence => unscored.
    assert c({"answer": "[ERROR: backend unavailable circuit open]", "error_code": 503,
              "error": "[ERROR: backend unavailable circuit open]"}) is None
    # A generic backend failure => unscored.
    assert c({"answer": "[FAILED: llama backend]", "error_code": 502}) is None
    assert c({"answer": "", "error": "Connection refused"}) is None
    # Pre-classified decision strings pass through; junk => None.
    assert c("admit") == sk.DECISION_ADMIT
    assert c("QUEUE") == sk.DECISION_QUEUE
    assert c("weird") is None
    assert c(None) is None
    assert c(42) is None
    assert c({"answer": "   "}) is None  # empty-after-strip, no error
    assert c({}) is None


# ── topology-aware probe classification (re-placement evidence) ────────────────


def _gate_response(idx: int, role: str = "vision_escalation") -> dict:
    """A clean admit response echoing the contention-gate verdict (bridge residual 1)."""
    return {
        "answer": "OK",
        "tokens_generated": 4,
        "contention_gate": {
            "admitted": True,
            "decision": "allow",
            "waited_s": 0.0,
            "candidate_topology_idx": idx,
            "queued_then_admitted": False,
            "reason": "all pairs + n-way allow",
            "role": role,
        },
    }


def test_classify_probe_outcome_extracts_topology_evidence() -> None:
    plan = _plan()
    # vision#3 {q0} is an overlapping candidate; echo idx=0 (vision#0 {q2,q3}).
    spec = next(p for p in plan.probes if p.candidate.instance_idx == 3)
    ev = sk._classify_probe_outcome(_gate_response(0), spec, SYNTH_REGIONS)
    assert isinstance(ev, dict)
    assert ev["decision"] == sk.DECISION_ADMIT
    assert ev["candidate_topology_idx"] == 0
    assert ev["role"] == "vision_escalation"
    assert tuple(ev["regions"]) == ("q2", "q3")  # resolved from plan's instance_regions


def test_classify_probe_outcome_falls_back_without_gate_evidence() -> None:
    plan = _plan()
    spec = next(p for p in plan.probes if p.candidate.instance_idx == 3)
    # (a) Clean admit with NO contention_gate -> plain "admit" (old classification).
    assert sk._classify_probe_outcome({"answer": "OK"}, spec, SYNTH_REGIONS) == sk.DECISION_ADMIT
    # (b) Queue/503 path (no gate echo) -> plain "queue".
    assert (
        sk._classify_probe_outcome(
            {"answer": "", "error": "Server error '503 Service Unavailable'"},
            spec, SYNTH_REGIONS,
        )
        == sk.DECISION_QUEUE
    )
    # (c) Gate present but admitted=False -> not evidence -> falls back.
    no_admit = _gate_response(0)
    no_admit["contention_gate"]["admitted"] = False
    assert sk._classify_probe_outcome(no_admit, spec, SYNTH_REGIONS) == sk.DECISION_ADMIT
    # (d) Non-int candidate_topology_idx -> falls back.
    bad_idx = _gate_response(0)
    bad_idx["contention_gate"]["candidate_topology_idx"] = None
    assert sk._classify_probe_outcome(bad_idx, spec, SYNTH_REGIONS) == sk.DECISION_ADMIT
    # (e) Unknown (role, idx) not in instance_regions -> falls back.
    unknown = _gate_response(99)
    assert sk._classify_probe_outcome(unknown, spec, SYNTH_REGIONS) == sk.DECISION_ADMIT
    # (f) Backend error with an echo -> NOT clean gate evidence -> unscored.
    err = _gate_response(0)
    err["answer"] = "[ERROR: backend unavailable circuit open]"
    err["error"] = "[ERROR: backend unavailable circuit open]"
    assert sk._classify_probe_outcome(err, spec, SYNTH_REGIONS) is None
    # (g) Pre-classified strings pass through unchanged.
    assert sk._classify_probe_outcome("queue", spec, SYNTH_REGIONS) == sk.DECISION_QUEUE


# ── admit-overlap driver (injected probe_fn) ──────────────────────────────────


def test_drive_admit_overlap_probes_scores_against_plan() -> None:
    # seam mode: the overlap->queue bracket this driver was built for. The
    # standing default is "replacement" (see the replacement-mode tests below).
    plan = _plan(sk.EXPECTATION_SEAM)
    # 6 probes: 3 disjoint (ADMIT) + 3 overlapping (QUEUE).
    assert len(plan.probes) == 6
    assert sum(1 for p in plan.probes if p.expected_decision == sk.DECISION_ADMIT) == 3
    assert sum(1 for p in plan.probes if p.expected_decision == sk.DECISION_QUEUE) == 3

    seen_priority: set[str] = set()
    seen_workload: set[str] = set()

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        # Assert every probe rides the placement queue (background/eval_batch).
        seen_priority.add(spec.request_priority)
        seen_workload.add(spec.workload_class)
        assert spec.transport == sk.PLACEMENT_QUEUE_TRANSPORT
        if spec.expected_decision == sk.DECISION_ADMIT:
            return {"answer": "OK", "tokens_generated": 4, "predicted_tps": 40.0}
        # Simulate the contention gate's fail-closed 503 (as surfaced through
        # call_orchestrator_forced): empty answer + httpx 503 error string.
        return {"answer": "", "error": "Server error '503 Service Unavailable' for url 'http://localhost:8000/chat'"}

    observed = sk._drive_admit_overlap_probes(
        plan, seed=7, probe_fn=fake_probe, anchor_hold_fn=_anchor_held
    )

    assert seen_priority == {sk.PLACEMENT_REQUEST_PRIORITY}   # "background"
    assert seen_workload == {sk.PLACEMENT_WORKLOAD_CLASS}     # "eval_batch"
    # Every probe classified back to its region-derived expectation.
    assert observed == {p.probe_id: p.expected_decision for p in plan.probes}

    summary = sk.aggregate_admit_overlap(plan.probes, observed, expectation=sk.EXPECTATION_SEAM)
    assert summary["n_evaluated"] == 6
    assert summary["n_pass"] == 6
    assert summary["all_pass"] is True


def test_drive_admit_overlap_probes_omits_unscored_outcomes() -> None:
    plan = _plan(sk.EXPECTATION_SEAM)
    # First probe returns a non-gate backend error -> must be OMITTED (unscored).
    dropped = plan.probes[0].probe_id

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        if spec.probe_id == dropped:
            return {"answer": "[ERROR: backend crashed]", "error_code": 500}
        if spec.expected_decision == sk.DECISION_ADMIT:
            return {"answer": "OK"}
        return {"answer": "", "error": "503 Service Unavailable /chat"}

    observed = sk._drive_admit_overlap_probes(
        plan, seed=1, probe_fn=fake_probe, anchor_hold_fn=_anchor_held
    )
    assert dropped not in observed
    assert len(observed) == 5

    summary = sk.aggregate_admit_overlap(plan.probes, observed, expectation=sk.EXPECTATION_SEAM)
    assert summary["n_evaluated"] == 5  # the dropped probe is not counted
    assert summary["n_pass"] == 5
    # all_pass is over the evaluated set; the omitted probe scores pass=None.
    assert any(row["pass"] is None and row["probe_id"] == dropped for row in summary["rows"])


def test_drive_admit_overlap_probes_timeout_path_classifies_queue() -> None:
    """The 90s/60s background-queue-budget timeout (fail-closed 503) is QUEUE.

    PROBE_TIMEOUT_S=120 maps to a bounded max_queue_wait_ms; an overlapping
    candidate exhausts it and surfaces as the contention handler's 503 through
    call_orchestrator_forced (empty answer + httpx 503 error text). The driver
    must classify that exact timeout shape as "queue", never as unscored.
    """
    plan = _plan(sk.EXPECTATION_SEAM)

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        if spec.expected_decision == sk.DECISION_ADMIT:
            return {"answer": "OK", "tokens_generated": 4}
        # The queue-budget-exhausted contention timeout, exactly as surfaced
        # through call_orchestrator_forced's raise_for_status branch.
        return {
            "answer": "",
            "error": (
                "Server error '503 Service Unavailable' for url "
                "'http://localhost:8000/chat'"
            ),
            "failure_reason": "http_status",
        }

    observed = sk._drive_admit_overlap_probes(
        plan, seed=9, probe_fn=fake_probe, anchor_hold_fn=_anchor_held
    )
    assert observed == {p.probe_id: p.expected_decision for p in plan.probes}
    queue_ids = [p.probe_id for p in plan.probes if p.expected_decision == sk.DECISION_QUEUE]
    assert all(observed[qid] == sk.DECISION_QUEUE for qid in queue_ids)


def test_drive_admit_overlap_probes_empty_queue_fails_closed() -> None:
    """An empty probe queue cannot produce the bracket — refuse before probing."""
    plan = _plan()
    plan.probes = []  # simulate a placement queue with no candidates

    def _boom(spec: sk.AdmitOverlapProbeSpec, *, seed: int):  # pragma: no cover
        raise AssertionError("no probe may fire on an empty queue")

    with pytest.raises(RuntimeError, match="signal structurally unobtainable"):
        sk._drive_admit_overlap_probes(plan, seed=3, probe_fn=_boom, anchor_hold_fn=_anchor_held)


def test_drive_admit_overlap_probes_anchor_not_held_fails_closed() -> None:
    """Anchor precondition: the operator must hold the anchor; unverified ⇒ fail closed."""
    plan = _plan()

    def _boom(spec: sk.AdmitOverlapProbeSpec, *, seed: int):  # pragma: no cover
        raise AssertionError("no probe may fire when the anchor is not verifiably held")

    # (a) Empty holder scan (locks disabled / stack down) — cannot verify.
    with pytest.raises(RuntimeError, match="anchor-hold precondition cannot be verified"):
        sk._drive_admit_overlap_probes(
            plan, seed=3, probe_fn=_boom, anchor_hold_fn=lambda: {}
        )
    # (b) Anchor role holds a DIFFERENT instance — not the anchor placement.
    with pytest.raises(RuntimeError, match="anchor-hold precondition cannot be verified"):
        sk._drive_admit_overlap_probes(
            plan, seed=3, probe_fn=_boom,
            anchor_hold_fn=lambda: {"ingest_long_context": [2]},
        )
    # (c) Anchor role absent from the scan entirely.
    with pytest.raises(RuntimeError, match="anchor-hold precondition cannot be verified"):
        sk._drive_admit_overlap_probes(
            plan, seed=3, probe_fn=_boom, anchor_hold_fn=lambda: {"frontdoor": [0]}
        )


def test_drive_admit_overlap_probes_one_sided_signal_fails_closed() -> None:
    """All-queue (or all-admit) expectations are structurally unobtainable.

    Mirrors the handoff's stale-default hazard: with the FULL ingest instance as
    anchor, every candidate overlaps → all probes expect QUEUE → the bracket has
    no disjoint side. The driver must refuse rather than "still report".
    """
    full_anchor_regions = {
        ("ingest_long_context", 1): frozenset({"q0", "q1", "q2", "q3"}),
        ("frontdoor", 0): frozenset({"q0", "q1"}),
        ("vision_escalation", 0): frozenset({"q2", "q3"}),
    }
    plan = sk.build_step2_smoke_plan(
        full_anchor_regions,
        topology_hash="test-topo",
        anchor=SYNTH_ANCHOR,
        probe_roles=("frontdoor", "ingest_long_context", "worker_general"),
        expectation=sk.EXPECTATION_SEAM,
    )
    assert len(plan.probes) > 0
    assert all(p.expected_decision == sk.DECISION_QUEUE for p in plan.probes)

    def _boom(spec: sk.AdmitOverlapProbeSpec, *, seed: int):  # pragma: no cover
        raise AssertionError("no probe may fire on a structurally unobtainable plan")

    with pytest.raises(RuntimeError, match="signal structurally unobtainable"):
        sk._drive_admit_overlap_probes(
            plan, seed=3, probe_fn=_boom,
            anchor_hold_fn=lambda: {"ingest_long_context": [0]},
        )


def test_verify_anchor_held_pure_pass_and_fail_paths() -> None:
    plan = _plan()
    # Pure checker: no I/O, no injection seam needed — holder map is the input.
    # The SYNTH anchor is ingest#1 (node0 half — corrected default).
    sk._verify_anchor_held(plan, {"ingest_long_context": [1]})
    sk._verify_anchor_held(plan, {"ingest_long_context": [1, 2]})
    with pytest.raises(RuntimeError, match="anchor-hold precondition cannot be verified"):
        sk._verify_anchor_held(plan, {})
    with pytest.raises(RuntimeError, match="anchor-hold precondition cannot be verified"):
        sk._verify_anchor_held(plan, {"ingest_long_context": [0]})


def test_verify_probe_signal_pure_refuses_one_sided_or_empty() -> None:
    plan = _plan()
    sk._verify_probe_signal(plan)  # 3 admit + 3 queue → valid bracket
    plan.probes = []
    with pytest.raises(RuntimeError, match="signal structurally unobtainable"):
        sk._verify_probe_signal(plan)


# ── expectation modes: "replacement" (standing default) ────────────────────────


def test_replacement_plan_expects_admit_for_every_candidate() -> None:
    plan = _plan()  # default expectation
    assert plan.expectation == sk.EXPECTATION_REPLACEMENT
    assert len(plan.probes) == 6
    # The standing restatement: even overlapping candidates are expected to be
    # re-placed onto a disjoint instance and admitted — so every probe expects
    # "admit" and the requested-candidate overlap stays a recorded fact.
    assert all(p.expected_decision == sk.DECISION_ADMIT for p in plan.probes)
    assert sum(1 for p in plan.probes if p.disjoint) == 3
    assert sum(1 for p in plan.probes if not p.disjoint) == 3
    assert plan.to_dict()["expectation"] == sk.EXPECTATION_REPLACEMENT


def test_replacement_overlapping_candidate_admit_disjoint_passes() -> None:
    """The 2026-08-24 fleet behavior: overlap-requested, re-placed, admitted."""
    plan = _plan()
    spec = next(p for p in plan.probes if not p.disjoint)
    # vision#3 {q0} requested; the placement machine re-places onto vision#0 {q2,q3}.
    observed = sk._drive_admit_overlap_probes(
        plan, seed=1, anchor_hold_fn=_anchor_held,
        probe_fn=lambda s, *, seed: (
            _gate_response(0) if s.probe_id == spec.probe_id else {"answer": "OK"}
        ),
    )
    assert observed[spec.probe_id]["candidate_topology_idx"] == 0

    summary = sk.aggregate_admit_overlap(plan.probes, observed)
    row = next(r for r in summary["rows"] if r["probe_id"] == spec.probe_id)
    assert row["verdict"] == sk.DECISION_ADMIT_DISJOINT
    assert row["pass"] is True
    assert "marker" not in row
    assert summary["n_co_placement"] == 0
    assert summary["n_pass"] == len(plan.probes)


def test_replacement_overlapping_candidate_admit_overlap_fails_co_placement() -> None:
    """An admit whose echoed candidate_topology_idx OVERLAPS the anchor is the
    co-placement safety-invariant violation — ALWAYS a failure, marked."""
    plan = _plan()
    spec = next(p for p in plan.probes if not p.disjoint)
    # Echo idx=3: vision#3 {q0} — the requested instance itself, overlapping the
    # held anchor {q0,q1}. The gate co-placed: that is the invariant breach.
    observed = sk._drive_admit_overlap_probes(
        plan, seed=2, anchor_hold_fn=_anchor_held,
        probe_fn=lambda s, *, seed: (
            _gate_response(3) if s.probe_id == spec.probe_id else {"answer": "OK"}
        ),
    )
    summary = sk.aggregate_admit_overlap(plan.probes, observed)
    row = next(r for r in summary["rows"] if r["probe_id"] == spec.probe_id)
    assert row["verdict"] == sk.DECISION_ADMIT_OVERLAP
    assert row["marker"] == sk.CO_PLACEMENT_MARKER
    assert row["pass"] is False
    assert summary["n_co_placement"] == 1
    assert summary["all_pass"] is False
    assert summary["expectation"] == sk.EXPECTATION_REPLACEMENT


def test_replacement_overlapping_candidate_queue_fails_queued_unexpected() -> None:
    """A queue while the standing expectation is replacement means the flag-on
    seam armed — a distinct failure outcome that still goes red."""
    plan = _plan()
    spec = next(p for p in plan.probes if not p.disjoint)
    observed = sk._drive_admit_overlap_probes(
        plan, seed=3, anchor_hold_fn=_anchor_held,
        probe_fn=lambda s, *, seed: (
            {"answer": "", "error": "Server error '503 Service Unavailable'"}
            if s.probe_id == spec.probe_id
            else {"answer": "OK"}
        ),
    )
    assert observed[spec.probe_id] == sk.DECISION_QUEUE

    summary = sk.aggregate_admit_overlap(plan.probes, observed)
    row = next(r for r in summary["rows"] if r["probe_id"] == spec.probe_id)
    assert row["observed"] == sk.DECISION_QUEUE
    assert row["verdict"] == sk.DECISION_QUEUED_UNEXPECTED
    assert row["pass"] is False
    assert summary["n_queued_unexpected"] == 1
    assert summary["all_pass"] is False


def test_replacement_disjoint_candidate_admit_passes_unchanged() -> None:
    """Disjoint candidates keep expected=admit (same as before the restatement)."""
    plan = _plan()
    spec = next(p for p in plan.probes if p.disjoint)
    # Plain admit without gate echo — old classification path.
    observed = sk._drive_admit_overlap_probes(
        plan, seed=4, anchor_hold_fn=_anchor_held,
        probe_fn=lambda s, *, seed: (
            {"answer": "OK"} if s.probe_id == spec.probe_id else {"answer": "OK"}
        ),
    )
    summary = sk.aggregate_admit_overlap(plan.probes, observed)
    row = next(r for r in summary["rows"] if r["probe_id"] == spec.probe_id)
    assert row["observed"] == sk.DECISION_ADMIT
    assert row["verdict"] == sk.DECISION_ADMIT
    assert row["pass"] is True
    assert summary["all_pass"] is True


def test_replacement_missing_contention_gate_falls_back_to_old_classification() -> None:
    """A response without contention_gate falls back to _classify_admit_queue:
    a clean admit scores as a plain "admit" pass (verdict visible), a 503 as
    "queue" -> queued_unexpected failure."""
    plan = _plan()
    overlap_spec = next(p for p in plan.probes if not p.disjoint)

    # (a) Clean admit, no echo.
    summary = sk.aggregate_admit_overlap(
        plan.probes,
        {overlap_spec.probe_id: sk._classify_probe_outcome(
            {"answer": "OK"}, overlap_spec, SYNTH_REGIONS
        )},
    )
    row = next(r for r in summary["rows"] if r["probe_id"] == overlap_spec.probe_id)
    assert row["observed"] == sk.DECISION_ADMIT
    assert row["verdict"] == sk.DECISION_ADMIT
    assert row["pass"] is True

    # (b) Queue/503 path, no echo.
    summary = sk.aggregate_admit_overlap(
        plan.probes,
        {overlap_spec.probe_id: sk._classify_probe_outcome(
            {"answer": "", "error": "contention_denied 503"}, overlap_spec, SYNTH_REGIONS
        )},
    )
    row = next(r for r in summary["rows"] if r["probe_id"] == overlap_spec.probe_id)
    assert row["verdict"] == sk.DECISION_QUEUED_UNEXPECTED
    assert row["pass"] is False


def test_replacement_drive_with_gate_echo_end_to_end() -> None:
    """Full replacement bracket: every candidate admits, gate echo present,
    disjoint placements -> all pass; one co-placement -> red."""
    plan = _plan()

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        # Every role instance admits with an echo of ITS OWN idx (for disjoint
        # candidates that is disjoint from the anchor; for overlapping ones it
        # co-places — unless re-placed, which the next test simulates).
        return _gate_response(spec.candidate.instance_idx, spec.candidate.role)

    observed = sk._drive_admit_overlap_probes(
        plan, seed=5, probe_fn=fake_probe, anchor_hold_fn=_anchor_held
    )
    assert all(isinstance(v, dict) for v in observed.values())
    summary = sk.aggregate_admit_overlap(plan.probes, observed)
    # The 3 overlapping-requested probes echoed an overlapping idx -> co-placement.
    assert summary["n_co_placement"] == 3
    assert summary["n_pass"] == 3
    assert summary["all_pass"] is False
    assert all(
        r["marker"] == sk.CO_PLACEMENT_MARKER
        for r in summary["rows"] if not r["disjoint"]
    )
    assert all(r["pass"] for r in summary["rows"] if r["disjoint"])


def test_replacement_replaced_overlap_all_pass() -> None:
    """The 2026-08-24 measured outcome as a PASSING standing smoke: overlapping
    requests are re-placed onto the disjoint instance and admitted."""
    plan = _plan()

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        if spec.disjoint:
            return _gate_response(spec.candidate.instance_idx, spec.candidate.role)
        # Overlapping-requested: the placement machine re-places onto a disjoint
        # instance of the same role. vision#3 -> vision#0 {q2,q3}; frontdoor#0
        # and worker_general#0 have no disjoint sibling in the SYNTH topology, so
        # fall back to a plain admit (no echo).
        if spec.candidate.role == "vision_escalation":
            return _gate_response(0, spec.candidate.role)
        return {"answer": "OK"}

    observed = sk._drive_admit_overlap_probes(
        plan, seed=6, probe_fn=fake_probe, anchor_hold_fn=_anchor_held
    )
    summary = sk.aggregate_admit_overlap(plan.probes, observed)
    assert summary["n_evaluated"] == 6
    assert summary["n_pass"] == 6
    assert summary["n_co_placement"] == 0
    assert summary["n_queued_unexpected"] == 0
    assert summary["all_pass"] is True
    # Replacement rows carry verdicts; a clean admit w/o echo is verdict "admit".
    assert {r["verdict"] for r in summary["rows"]} <= {
        sk.DECISION_ADMIT_DISJOINT, sk.DECISION_ADMIT,
    }


# ── expectation modes: "seam" (2026-08-24-compatible flag-on model) ────────────


def test_seam_overlapping_queue_passes_admit_fails_byte_compatible() -> None:
    """The original bracket (overlap -> queue): queue passes, admit fails — the
    2026-08-24 behavior — and the report stays byte-compatible with that
    artifact's shape: no verdict/marker/expectation keys anywhere."""
    plan = _plan(sk.EXPECTATION_SEAM)
    overlap_spec = next(p for p in plan.probes if not p.disjoint)

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        if spec.expected_decision == sk.DECISION_ADMIT:
            return {"answer": "OK"}
        if spec.probe_id == overlap_spec.probe_id:
            # This overlapping candidate ADMITS (the 2026-08-24 live behavior) —
            # in seam mode that is a FAILURE, exactly as the artifact recorded.
            return _gate_response(0)
        return {"answer": "", "error": "Server error '503 Service Unavailable'"}

    observed = sk._drive_admit_overlap_probes(
        plan, seed=7, probe_fn=fake_probe, anchor_hold_fn=_anchor_held
    )
    summary = sk.aggregate_admit_overlap(
        plan.probes, observed, expectation=sk.EXPECTATION_SEAM
    )
    row = next(r for r in summary["rows"] if r["probe_id"] == overlap_spec.probe_id)
    # The gate echo collapses to its plain decision string in seam mode.
    assert row["observed"] == sk.DECISION_ADMIT
    assert row["expected"] == sk.DECISION_QUEUE
    assert row["pass"] is False
    assert summary["n_pass"] == 5  # 3 disjoint admits + 2 genuinely queued overlaps
    assert summary["n_fail"] == 1
    assert summary["all_pass"] is False

    # Byte-compatibility with the 2026-08-24 route-a1 artifact:
    # rows carry exactly {probe_id, disjoint, expected, observed, pass} ...
    assert set(row.keys()) == {"probe_id", "disjoint", "expected", "observed", "pass"}
    # ... and the summary carries exactly the artifact's top-level keys.
    assert set(summary.keys()) == {
        "all_pass", "kind", "n_admit_expected", "n_evaluated", "n_fail",
        "n_pass", "n_probes", "n_queue_expected", "observation_only", "rows",
        "runner_version",
    }
    assert all(set(r.keys()) == set(row.keys()) for r in summary["rows"])
    assert "verdict" not in summary and "marker" not in summary
    assert summary["kind"] == "admit_overlap_probe_summary"
    assert summary["runner_version"] == sk.RUNNER_VERSION


def test_seam_replaced_admit_is_still_a_failure() -> None:
    """Even with re-placement evidence present, seam mode counts the observed
    decision (admit) against the overlap->queue expectation: FAIL."""
    plan = _plan(sk.EXPECTATION_SEAM)
    overlap_spec = next(p for p in plan.probes if not p.disjoint)
    summary = sk.aggregate_admit_overlap(
        plan.probes,
        {overlap_spec.probe_id: {
            "decision": sk.DECISION_ADMIT, "candidate_topology_idx": 0,
            "role": "vision_escalation", "regions": ("q2", "q3"),
        }},
        expectation=sk.EXPECTATION_SEAM,
    )
    row = next(r for r in summary["rows"] if r["probe_id"] == overlap_spec.probe_id)
    assert row["observed"] == sk.DECISION_ADMIT
    assert row["pass"] is False
    assert set(row.keys()) == {"probe_id", "disjoint", "expected", "observed", "pass"}


# ── re-bench driver (injected sample_fn) ──────────────────────────────────────


def test_drive_rebench_pairs_collects_samples() -> None:
    plan = _plan()
    # 4 disjoint within-role vision pairs.
    assert len(plan.rebench_pairs) == 4
    pair_ids = {p.pair_id for p in plan.rebench_pairs}
    assert pair_ids == {"q0+q2q3", "q2+q3", "q0+q2", "q0+q3"}

    calls: list[tuple[str, int]] = []

    def fake_sample(pair: sk.RebenchPairSpec, *, seed: int, target_samples: int):
        calls.append((pair.pair_id, target_samples))
        assert pair.transport == sk.PLACEMENT_QUEUE_TRANSPORT
        # A clean super-linear allow: mean ~1.20, tiny CV.
        return [1.200 + 0.001 * i for i in range(target_samples)]

    samples = sk._drive_rebench_pairs(plan, seed=3, sample_fn=fake_sample)
    assert set(samples) == pair_ids
    assert all(len(v) == sk.DEFAULT_TARGET_SAMPLES for v in samples.values())
    assert all(ts == sk.DEFAULT_TARGET_SAMPLES for _, ts in calls)

    rows = sk.aggregate_rebench(plan.rebench_pairs, samples, floor=plan.floor,
                                cv_threshold=plan.cv_threshold)
    assert len(rows) == 4
    for row in rows:
        assert row["n_samples"] == sk.DEFAULT_TARGET_SAMPLES
        assert row["met_sample_target"] is True
        assert row["verdict"] == "allow"
        assert row["clean"] is True
        assert row["ratified_allow"] is True
        # Bench index = model/quant, never role.
        assert row["model"] == sk.VISION_DEFAULT_MODEL
        assert row["quant"] == sk.VISION_DEFAULT_QUANT
        assert row["ratio_delta_vs_prior"] is not None


# ── execute_step2_smoke: aggregation + artifact write (injected fns) ───────────


def test_execute_step2_smoke_writes_artifact_with_injected_fns(tmp_path: Path) -> None:
    plan = _plan(sk.EXPECTATION_SEAM)
    out = tmp_path / "nested" / "smoke_report.json"

    def fake_probe(spec: sk.AdmitOverlapProbeSpec, *, seed: int):
        if spec.expected_decision == sk.DECISION_ADMIT:
            return {"answer": "OK"}
        return {"answer": "", "error": "contention_denied 503"}

    def fake_sample(pair: sk.RebenchPairSpec, *, seed: int, target_samples: int):
        return [1.15 + 0.0005 * i for i in range(target_samples)]

    report = sk.execute_step2_smoke(
        plan,
        output_path=out,
        seed=42,
        probe_fn=fake_probe,
        sample_fn=fake_sample,
        anchor_hold_fn=_anchor_held,
    )

    assert report["kind"] == "shapekeyed_step2_smoke_report"
    assert report["smoke_pass"] is True
    assert report["admit_overlap"]["all_pass"] is True
    assert report["admit_overlap"]["n_pass"] == 6
    assert report["n_rebench_ratified_allow"] == 4
    assert report["observation_only"] is True

    # Artifact written (nested dirs created) and round-trips to the same report.
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == report


# ── double-gate dry-run: unchanged + bridge never reached ─────────────────────


def test_env_gate_closed_returns_dry_run_and_never_calls_bridge(monkeypatch) -> None:
    monkeypatch.delenv(sk.SHAPEKEYED_STEP2_INFERENCE_ENV, raising=False)
    plan = _plan()

    # execute=False -> dry-run, no inference.
    res = sk.run_shapekeyed_step2_smoke(plan, execute=False)
    assert res["mode"] == "dry_run"
    assert res["inference_ran"] is False
    assert res["n_probes"] == 6
    assert res["n_rebench_pairs"] == 4
    assert res["plan"]["kind"] == "shapekeyed_step2_smoke_plan"

    # execute=True but env gate closed -> STILL dry-run, and the bridge must not be
    # invoked. Poison the bridge to prove the dry-run path never reaches it.
    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("execute_step2_smoke must not run when the env gate is closed")

    monkeypatch.setattr(sk, "execute_step2_smoke", _boom)
    res2 = sk.run_shapekeyed_step2_smoke(plan, execute=True)
    assert res2["mode"] == "dry_run"
    assert res2["inference_ran"] is False
    assert sk.SHAPEKEYED_STEP2_INFERENCE_ENV in res2["reason"]


# ── CLI/defaults: expectation mode ─────────────────────────────────────────────


def test_expectation_defaults_to_replacement() -> None:
    # CLI default ...
    args = sk.build_arg_parser().parse_args([])
    assert args.expectation == sk.EXPECTATION_REPLACEMENT
    # ... and plan-build default agree (replacement is the STANDING expectation).
    assert sk.DEFAULT_EXPECTATION == sk.EXPECTATION_REPLACEMENT
    plan = sk.build_step2_smoke_plan(SYNTH_REGIONS, topology_hash="test-topo", anchor=SYNTH_ANCHOR)
    assert plan.expectation == sk.EXPECTATION_REPLACEMENT
    assert all(p.expected_decision == sk.DECISION_ADMIT for p in plan.probes)


def test_cli_expectation_choice_is_validated() -> None:
    p = sk.build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["--expectation", "bogus"])


def test_main_dry_run_prints_the_expectation_mode(monkeypatch, capsys) -> None:
    monkeypatch.delenv(sk.SHAPEKEYED_STEP2_INFERENCE_ENV, raising=False)
    # Default dry-run announces the standing replacement mode.
    assert sk.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["expectation"] == sk.EXPECTATION_REPLACEMENT
    assert payload["n_queue_expected"] == 0

    # --expectation seam is threaded through the plan and printed.
    assert sk.main(["--expectation", sk.EXPECTATION_SEAM]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["expectation"] == sk.EXPECTATION_SEAM
    assert payload["n_queue_expected"] >= 1


def test_default_anchor_and_probes_are_live_cpu_hosts() -> None:
    """The defaults must name live CPU host fleets, so the seam bracket has teeth.

    They pinned ingest_long_context / worker_general until the operator-signed
    2026-09-22 cutover (orchestrator 860b0b2d) made both aliases with no NUMA
    instances of their own. The anchor then resolved to EMPTY regions, and the
    default plan checked nothing.
    """
    from src.registry.registry_loader import load_server_mode, serving_host_rows

    hosts = set(serving_host_rows(load_server_mode()))
    assert sk.DEFAULT_PROBE_ROLES, "no default probe roles derived"
    assert set(sk.DEFAULT_PROBE_ROLES) <= hosts, sk.DEFAULT_PROBE_ROLES
    assert sk.DEFAULT_ANCHOR_ROLE in sk.DEFAULT_PROBE_ROLES

    regions = sk.load_instance_regions()
    anchor_regions = regions.get((sk.DEFAULT_ANCHOR_ROLE, sk.DEFAULT_ANCHOR_IDX))
    assert anchor_regions, "default anchor resolves to no CPU regions"
    plan = sk.build_step2_smoke_plan(regions, expectation=sk.EXPECTATION_SEAM)
    decisions = {p.expected_decision for p in plan.probes}
    assert decisions == {sk.DECISION_ADMIT, sk.DECISION_QUEUE}, decisions

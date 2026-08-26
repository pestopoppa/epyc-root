"""SC21 — the contention-matrix run reader.

What is pinned here, in the order this program has been burned:

* the **locator rule** — one claim per RUN, never per pair or per file; a run's
  `per_sample` rows and multiple candidate sets produce exactly ONE tuple (a per-pair or
  per-sample projection would read one run as N independent witnesses, the SC6-HAZARD
  class);
* the **pre-hook refusal** — a run written before the producer stamped
  `decision_grade` (orchestrator `77e5a214`) carries no host-state warrant; the strict
  reader refuses it with a `pre-hook:` reason and emits zero tuples, never
  reconstructing anything on read (the warm OP-21 corpus is exactly this state);
* the **host-state scope limit** — `decision_grade` attests HOST STATE only; the tuple
  itself carries the limit so a reader can never take `decision_grade: true` as "this
  ratio is statistically solid";
* the **blockers-as-disposition-input rule** — a stamped-but-blocked run projects WITH
  its `decision_grade_blockers` named in the claim, so a blocked run can never be
  mistaken for support of its verdict;
* the ladder is not reimplemented — every grade asserted below is whatever
  ``claim_tuple.grade()`` actually returns for the projected tuple;
* attestation is hashed at collect time — out-of-tree artifacts honestly land at
  `Witnessed/Anchored`; an in-tree run reaches `Witnessed/Attested` because the ladder
  resolves its repo-relative attestation path.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import contention_matrix as reader  # noqa: E402

CLEAN_STAMP = {
    "host_health_status": "clean",
    "decision_grade": True,
    "decision_grade_blockers": [],
    "host_health_warnings": [],
    "host_provenance": {"hostname": "node0", "attestation_status": "collected"},
}


def _sample(index: int, ratio: float = 1.168) -> dict:
    return {
        "sample": index,
        "solo_tps": {"frontdoor": 13.89, "ingest_long_context": 11.45},
        "par_tps": {"frontdoor": 9.25, "ingest_long_context": 7.33},
        "seq_aggregate_tps": 12.55,
        "parallel_aggregate_tps": 14.66,
        "ratio": ratio,
    }


def _entry(**overrides) -> dict:
    samples = overrides.pop("samples", 12)
    entry = {
        "roles": ["frontdoor", "ingest_long_context"],
        "size": 2,
        "topology_hash": "171f86f9188211e9",
        "ports": {"frontdoor": 8080, "ingest_long_context": 8185},
        "measured_at": "2026-08-24T10:28:44.023523+00:00",
        "ratio": 1.198,
        "cv": 0.1044,
        "samples": samples,
        "seq_aggregate_tps": 12.51,
        "parallel_aggregate_tps": 14.87,
        "verdict": "allow",
        "per_sample": [_sample(i) for i in range(samples)],
    }
    entry.update(overrides)
    return entry


def _block_yaml(entries: list[dict], *, stamp: dict | None = None) -> str:
    lines: list[str] = []
    if stamp is not None:
        lines.append(f'host_health_status: "{stamp["host_health_status"]}"')
        lines.append(f"decision_grade: {str(stamp['decision_grade']).lower()}")
        blockers = stamp.get("decision_grade_blockers") or []
        if blockers:
            lines.append("decision_grade_blockers:")
            lines.extend(f"  - {json.dumps(b)}" for b in blockers)
        else:
            lines.append("decision_grade_blockers: []")
        warnings = stamp.get("host_health_warnings") or []
        if warnings:
            lines.append("host_health_warnings:")
            lines.extend(f"  - {json.dumps(w)}" for w in warnings)
        else:
            lines.append("host_health_warnings: []")
        provenance = stamp.get("host_provenance")
        if provenance is not None:
            lines.append("host_provenance:")
            lines.extend(f"  {k}: {json.dumps(v)}" for k, v in provenance.items())
        lines.append("")
    lines.append("n_way:")
    for e in entries:
        lines.append(f"  - roles: [{', '.join(repr(r) for r in e['roles'])}]")
        lines.append(f"    size: {e['size']}")
        lines.append(f'    topology_hash: "{e["topology_hash"]}"')
        lines.append(f"    seq_aggregate_tps: {e['seq_aggregate_tps']}")
        lines.append(f"    parallel_aggregate_tps: {e['parallel_aggregate_tps']}")
        lines.append(f"    ratio: {e['ratio']}")
        lines.append(f"    samples: {e['samples']}")
        lines.append(f"    cv: {e['cv']}")
        lines.append(f'    verdict: "{e["verdict"]}"')
        lines.append(f'    measured_at: "{e["measured_at"]}"')
    return "\n".join(lines) + "\n"


def write_run(root: Path, name: str, *, entries: list[dict] | None = None,
              stamp: dict | None = None, results_overrides: dict | None = None,
              manifest: dict | None = None) -> Path:
    run_dir = root / name
    run_dir.mkdir(parents=True, exist_ok=True)
    entries = entries or [_entry()]
    manifest = manifest or {
        "task_id": "OP-21 overlap decision-grade re-measure (cv <= 0.05)",
        "topology_hash": "171f86f9188211e9",
        "candidate_sets": [{
            "roles": ["frontdoor", "ingest_long_context"],
            "note": "OVERLAP (true production geometry)",
            "assignment": {"frontdoor": {"port": 8080},
                           "ingest_long_context": {"port": 8185}},
        }],
    }
    results = {
        "task_id": "J4b",
        "topology_hash": "171f86f9188211e9",
        "generated_at": "2026-08-24T10:28:44.023621+00:00",
        "manifest": f"data/contention_matrix/{name}/manifest.json",
        "n_way": entries,
    }
    results.update(results_overrides or {})
    (run_dir / reader.MANIFEST_FILE).write_text(json.dumps(manifest, indent=2) + "\n")
    (run_dir / reader.RESULTS_FILE).write_text(json.dumps(results, indent=2) + "\n")
    (run_dir / reader.BLOCK_FILE).write_text(_block_yaml(entries, stamp=stamp))
    return run_dir


# --- projection + the shared ladder --------------------------------------------------------

def test_posthook_clean_run_projects_one_claim(tmp_path):
    run = write_run(tmp_path, "op21-overlap-decisiongrade-20260824", stamp=CLEAN_STAMP)
    natives = reader.native_rows(run)
    assert len(natives) == 1

    tup = reader.project(natives[0])
    assert tup.measurement_id == "cm_op21-overlap-decisiongrade-20260824"
    assert tup.metric == "contention_ratio"
    assert tup.value == 1.198
    assert tup.protocol_id == "contention_matrix.nway_results.v1"
    assert tup.reps == 1 and tup.reps_basis == "runs"
    assert tup.category == "BASELINE"
    assert tup.metric_direction == "higher_better"
    assert tup.date == "2026-08-24"
    assert len(tup.attestation_sha256) == 64
    assert tup.attestation_locator == str(run)
    assert tup.extra["decision_grade"] is True
    assert tup.extra["host_health_status"] == "clean"
    assert tup.extra["decision_grade_blockers"] == []
    assert tup.extra["entry_count"] == 1
    assert tup.extra["per_sample_count"] == 12

    # The SC21 scope limit is carried IN the claim, not just the docs: decision_grade
    # attests HOST STATE only, never ratio solidity.
    assert "HOST STATE only" in tup.claim
    assert "never evidence that the ratio is statistically solid" in tup.claim

    q, t, reasons = ct.grade(tup)
    # The fixture lives OUT of the repo tree, so the honest ladder answer is
    # Witnessed/Anchored — hashed at collect time, not pinned at a repo-relative path.
    assert (q, t) == ("Witnessed", "Anchored"), reasons


def test_posthook_blocked_run_projects_with_blockers_carried(tmp_path):
    blocker = "host uptime 14.1 d exceeds the clean window (P-BENCH-1)"
    stamp = {
        "host_health_status": "warn",
        "decision_grade": False,
        "decision_grade_blockers": [blocker],
        "host_health_warnings": [blocker],
    }
    run = write_run(tmp_path, "op21-overlap-decisiongrade-20260824", stamp=stamp)
    natives = reader.native_rows(run)
    assert len(natives) == 1

    tup = reader.project(natives[0])
    assert tup.extra["decision_grade"] is False
    assert tup.extra["host_health_status"] == "warn"
    assert tup.extra["decision_grade_blockers"] == [blocker]
    assert tup.extra["host_health_warnings"] == [blocker]
    # The blockers are the refuted/conflicted disposition input and the claim says so.
    assert "NOT decision-grade" in tup.claim
    assert "refuted/conflicted disposition input" in tup.claim
    assert blocker in tup.claim


# --- the locator rule ----------------------------------------------------------------------

def test_multi_entry_run_is_exactly_one_claim(tmp_path):
    """Two candidate sets + per_sample rows in one run = ONE witness, not many."""
    run = write_run(
        tmp_path, "op21-overlap-rebench-20260823T0855Z", stamp=CLEAN_STAMP,
        entries=[
            _entry(measured_at="2026-08-23T08:53:34.729176+00:00", ratio=0.977,
                   cv=0.1018, samples=3, verdict="borderline"),
            _entry(ports={"frontdoor": 8080, "ingest_long_context": 8285},
                   measured_at="2026-08-23T08:54:55.841815+00:00", ratio=1.36,
                   cv=0.0179, samples=3, verdict="allow"),
        ])
    natives = reader.native_rows(run)
    assert len(natives) == 1, "one run must produce exactly one native row"
    tup = reader.project(natives[0])
    assert tup.measurement_id == "cm_op21-overlap-rebench-20260823T0855Z"
    assert tup.value == 0.977, "the run's headline value is its first declared set"
    assert tup.extra["entry_count"] == 2
    assert [e["verdict"] for e in tup.extra["entries"]] == ["borderline", "allow"]
    assert tup.extra["per_sample_count"] == 6
    assert "2 candidate set(s)" in tup.claim
    frames = reader.frames_for_run(run, as_of="2026-08-24T12:00:00Z")
    assert len([f for f in frames if f["frame_type"].endswith("claim_proposed/v1")]) == 1


# --- pre-hook refusal: absence is not back-filled ------------------------------------------

def test_prehook_run_is_refused_and_projects_nothing(tmp_path):
    """A verdict-only block (no decision_grade stamp) = pre-hook warrant, refused."""
    run = write_run(tmp_path, "op21-overlap-rebench-20260823T0855Z")  # stamp=None
    assert reader.native_rows(run) == ()
    reason = reader.refusal_reason(run)
    assert reason is not None and reason.startswith("pre-hook")
    assert "77e5a214" in reason
    assert reader.frames_for_run(run, as_of="2026-08-24T12:00:00Z") == []


def test_absent_run_reports_no_emissions(tmp_path):
    run = tmp_path / "op21-overlap-decisiongrade-20260824"
    assert reader.native_rows(run) == ()
    assert reader.refusal_reason(run) == "no emissions"
    assert reader.frames_for_run(run, as_of="2026-08-24T12:00:00Z") == []


# --- strictness ----------------------------------------------------------------------------

def test_schema_guard_refuses_malformed_runs(tmp_path):
    # Missing artifact file voids the run as a whole.
    run = write_run(tmp_path, "torn", stamp=CLEAN_STAMP)
    (run / reader.RESULTS_FILE).unlink()
    assert reader.native_rows(run) == ()
    assert "malformed" in reader.refusal_reason(run)
    assert "missing j4b_nway_results.json" in reader.refusal_reason(run)

    # Non-JSON results envelope.
    run = write_run(tmp_path, "garbage", stamp=CLEAN_STAMP)
    (run / reader.RESULTS_FILE).write_text("{not json\n")
    assert reader.native_rows(run) == ()
    assert "malformed" in reader.refusal_reason(run)

    # Empty n_way list is producer corruption, not a partial run.
    run = write_run(tmp_path, "empty", stamp=CLEAN_STAMP, results_overrides={"n_way": []})
    assert reader.native_rows(run) == ()
    assert "n_way" in reader.refusal_reason(run)

    # A verdict outside the producer vocabulary.
    run = write_run(tmp_path, "badverdict", stamp=CLEAN_STAMP,
                    entries=[_entry(verdict="maybe")])
    assert reader.native_rows(run) == ()
    assert "verdict" in reader.refusal_reason(run)

    # decision_grade=true with non-empty blockers violates the producer's fail-safe
    # contract (grade true <=> clean and no blockers).
    broken = dict(CLEAN_STAMP, decision_grade=True,
                  decision_grade_blockers=["stale uptime"])
    run = write_run(tmp_path, "inconsistent", stamp=broken)
    assert reader.native_rows(run) == ()
    assert "decision_grade=true" in reader.refusal_reason(run)


def test_project_rejects_bare_or_mutated_native(tmp_path):
    run = write_run(tmp_path, "op21-overlap-decisiongrade-20260824", stamp=CLEAN_STAMP)
    native = reader.native_rows(run)[0]
    tampered = {**native, "results": {**native["results"], "n_way": []}}
    with pytest.raises(ct.ProjectionError):
        reader.project(tampered)
    with pytest.raises(ct.ProjectionError):
        reader.project({})  # bypassing native_rows: no run_dir
    with pytest.raises(ct.ProjectionError):
        reader.project(native["results"])  # bypassing native_rows entirely
    # A pre-hook block cannot be smuggled through project() either.
    prehook = write_run(tmp_path, "prehook")
    smuggled = {
        "run_dir": str(prehook), "run_name": "prehook",
        "manifest": native["manifest"], "results": native["results"],
        "block": None, "result_sha256": native["result_sha256"],
    }
    with pytest.raises(ct.ProjectionError):
        reader.project(smuggled)


# --- attestation honesty -------------------------------------------------------------------

def test_in_tree_run_reaches_witnessed_attested(tmp_path, monkeypatch):
    """An artifact inside the repo tree pins by repo-relative path: the ladder says so."""
    run = write_run(tmp_path, "op21-overlap-decisiongrade-20260824", stamp=CLEAN_STAMP)
    monkeypatch.setattr(ct, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(reader, "REPO_ROOT", tmp_path)
    tup = reader.project(reader.native_rows(run)[0])
    assert tup.attestation_path == "op21-overlap-decisiongrade-20260824/j4b_nway_results.json"
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested"), reasons


# --- carrier conformance -------------------------------------------------------------------

def test_projection_is_registered_under_the_shared_registry():
    assert "contention-matrix-measurement" in ct.registered()


def test_frames_go_through_the_shared_emitter(tmp_path):
    run = write_run(tmp_path, "op21-overlap-decisiongrade-20260824", stamp=CLEAN_STAMP)
    frames = reader.frames_for_run(run, as_of="2026-08-24T12:00:00Z")
    assert len(frames) == 3  # source, claim, support
    claim = [f for f in frames if f["frame_type"].endswith("claim_proposed/v1")]
    support = [f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1")]
    assert len(claim) == 1 and len(support) == 1
    assert support[0]["assertion"]["grade"] == {"Q": "Witnessed", "T": "Anchored"}
    assert support[0]["assertion"]["protocol_id"] == "contention_matrix.nway_results.v1"
    assert support[0]["assertion"]["reps"] == 1
    assert support[0]["assertion"]["category"] == "BASELINE"
    assert support[0]["assertion"]["metric_direction"] == "higher_better"
    assert support[0]["provenance"]["reps_basis"] == "runs"
    source = [f for f in frames if f["frame_type"].endswith("source_observed/v1")]
    assert source[0]["assertion"]["locator"] == str(run)


# --- the warm corpus, priced ---------------------------------------------------------------

@pytest.mark.skipif(
    not Path("/mnt/raid0/llm/epyc-orchestrator/data/contention_matrix").is_dir(),
    reason="orchestrator contention corpus absent")
def test_warm_corpus_is_prehook_refused_until_first_posthook_run():
    """The live corpus (OP-21 rebench + decision-grade attempt) is verdict-only and
    predates the host-health stamp: zero rows, each refusal naming why. This trips the
    moment a post-hook run lands, which is exactly when the source-table row must flip."""
    corpus = Path("/mnt/raid0/llm/epyc-orchestrator/data/contention_matrix")
    for name in ("op21-overlap-decisiongrade-20260824",
                 "op21-overlap-rebench-20260823T0855Z"):
        run = corpus / name
        assert run.is_dir(), f"warm corpus run {name} missing"
        reason = reader.refusal_reason(run)
        assert reason is not None and reason.startswith("pre-hook"), (name, reason)
        assert reader.native_rows(run) == ()

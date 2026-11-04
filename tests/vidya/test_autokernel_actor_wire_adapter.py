"""VB-AK-NATIVE-WIRE-WRITE: strict reader for native actor-wire matrix finalization.

Pins: verifier-class projection through the one ladder (no grader here); PASS/FAIL/aborted/unvisited
verbatim; native-provider checks and mocked controls are separate tuples; legacy (pre-finalization)
artefacts decline; every mutation of a v1 finalization is REFUSED.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import autokernel_actor_wire as w  # noqa: E402
from ledger import Ledger  # noqa: E402

AS_OF = "2026-11-03T12:00:00Z"
H = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731


def make_seat(kind, role):
    return {"role": role, "backend": {"kind": kind, "model": f"{kind}-m", "binary": f"/bin/{kind}"},
            "client_sha256": H("client-" + kind), "seat": {"bounded": False, "arm": role},
            "timeout_s": 20, "read_only": role == "critic", "launch_config": {"x": 1}}


def request(seats):
    uniq = {w.digest(s): s for s in seats}
    seats = [uniq[k] for k in sorted(uniq)]
    return {"schema": w.WIRE_SCHEMA, "seats": seats, "actor_config_digest": w.digest(seats),
            "suite": {"actor_wire_gate.py": H("g"), "actors.py": H("a")}}


def result_for(seat, requests):
    return {"checks": {c: True for c in w.CHECKS}, "evidence_kinds": copy.deepcopy(w.EVIDENCE_KINDS),
            "requests_sha256": w.digest(requests), "request_count": len(requests),
            "provider_protocol": w.PROTOCOLS[seat["backend"]["kind"]],
            "readonly_denial": "passed" if seat["read_only"] else "not-readonly"}


def build(tmp_path, *, verdicts=("PASS", "FAIL"), abort=None, write_evidence=True, cleanup_uncertain=False):
    """3 requested seats; len(verdicts) attempted in order; remainder unvisited."""
    req = request([make_seat("codex", "planner"), make_seat("claude", "critic"),
                   make_seat("opencode", "author")])
    seats = req["seats"]
    outcomes, results, evidence, cleanup = [], {}, {}, {}
    for i, verdict in enumerate(verdicts):
        key, seat = w.digest(seats[i]), seats[i]
        o = {"seat": key, "backend": seat["backend"]["kind"], "role": seat["role"], "status": verdict}
        reqs = [{"path": "/v1/x", "body": {"n": i}}]
        if verdict == "PASS":
            results[key] = result_for(seat, reqs)
        else:
            o["error"] = "AssertionError: large reply not byte exact"
        outcomes.append(o)
        sha = None
        if write_evidence:
            body = {"seat": seat, "requests": reqs, "suite": req["suite"], "native_captures": {},
                    "diagnostics": {}}
            raw = json.dumps(body).encode()
            (tmp_path / f"{key}.json").write_bytes(raw)
            sha = hashlib.sha256(raw).hexdigest()
        evidence[key] = {"sha256": sha}
        cleanup[key] = {"receipts": 2, "all_verified": True}
    status = "PASS" if (len(verdicts) == 3 and abort is None and "FAIL" not in verdicts) else "FAIL"
    record = w.seal({
        "schema": w.FINAL_SCHEMA, "finalized_utc": "2026-11-03T10:00:00Z",
        "producer": {"repo": "epyc-inference-research", "commit": "a" * 40,
                     "module": "scripts/kernel_rnd/autokernel/loop/actor_wire_test.py"},
        "request": req, "status": status, "outcomes": outcomes, "attempted": len(outcomes),
        "expected": 3, "abort": abort, "unvisited": [w.digest(s) for s in seats[len(outcomes):]],
        "results": results, "evidence": evidence,
        "cleanup": {"cleanup_uncertain": cleanup_uncertain, "seats": cleanup}})
    path = tmp_path / "actor-wire-final.json"
    path.write_text(json.dumps(record))
    return path, record


def reseal_write(path, record):
    path.write_text(json.dumps(w.seal(record)))


def project_all(path):
    return [w.project(n) for n in w.native_rows(path)]


def test_projects_pass_fail_with_unvisited_verbatim(tmp_path):
    path, record = build(tmp_path, verdicts=("PASS", "FAIL"))
    tuples = project_all(path)
    by = {(t.metric, t.extra.get("seat_digest")): t for t in tuples}
    # matrix + (native, mocked) for the PASS seat + one FAIL tuple: native and mocked never merged
    assert len(tuples) == 4
    assert {t.metric for t in tuples} == {w.METRIC_MATRIX, w.METRIC_NATIVE, w.METRIC_MOCKED,
                                          w.METRIC_SEAT_FAIL}
    matrix = by[(w.METRIC_MATRIX, None)]
    assert matrix.value == 0 and "unvisited" in matrix.decided_proposition
    assert matrix.extra["unvisited"] == record["unvisited"] and len(record["unvisited"]) == 1
    fail = next(t for t in tuples if t.metric == w.METRIC_SEAT_FAIL)
    assert fail.value == 0 and "large reply not byte exact" in fail.decided_proposition
    native = next(t for t in tuples if t.metric == w.METRIC_NATIVE)
    mocked = next(t for t in tuples if t.metric == w.METRIC_MOCKED)
    assert native.value == mocked.value == 1
    assert "NATIVE-provider" in native.decided_proposition and "template_echo" not in native.decided_proposition
    assert "MOCKED" in mocked.decided_proposition and "not native protocol proof" in mocked.decided_proposition
    assert native.measurement_id != mocked.measurement_id
    for t in tuples:
        assert t.source_class == "verifier" and t.binding_kind == "identity"
        assert t.claim == t.decided_proposition and "no merge-validity claim" in t.claim
        assert t.extra["authority"] == w.AUTHORITY and t.protocol_id == ""
        assert ct.grade(t)  # the one ladder decides


def test_aborted_preserved_verbatim(tmp_path):
    path, record = build(tmp_path, verdicts=("PASS",), abort="CleanupUncertain: owned call survivors")
    matrix = next(t for t in project_all(path) if t.metric == w.METRIC_MATRIX)
    assert matrix.value == 0 and "CleanupUncertain: owned call survivors" in matrix.decided_proposition
    assert matrix.extra["abort"] == "CleanupUncertain: owned call survivors"
    assert matrix.extra["attempted"] == 1 and len(matrix.extra["unvisited"]) == 2


def test_full_pass_matrix_is_complete(tmp_path):
    path, _ = build(tmp_path, verdicts=("PASS", "PASS", "PASS"))
    tuples = project_all(path)
    assert len(tuples) == 1 + 3 * 2
    assert next(t for t in tuples if t.metric == w.METRIC_MATRIX).value == 1


def test_missing_evidence_recorded_absent_not_skipped(tmp_path):
    (tmp_path / "a").mkdir()
    full, _ = build(tmp_path / "a", verdicts=("PASS",))
    bare_dir = tmp_path / "b"
    bare_dir.mkdir()
    bare, _ = build(bare_dir, verdicts=("PASS",), write_evidence=False)
    a = next(t for t in project_all(full) if t.metric == w.METRIC_NATIVE)
    b = next(t for t in project_all(bare) if t.metric == w.METRIC_NATIVE)
    assert a.attestation_present is True and b.attestation_present is False
    assert a.attestation_verified is True and b.attestation_verified is None
    assert b.extra["evidence"]["reason"] == "producer wrote none"
    assert ct.grade(b)[0] in ("Judged", "Unverified") or ct.grade(b)


@pytest.mark.parametrize("name", ["actor-wire-pass.json", "matrix-results.json"])
def test_legacy_artifacts_decline(tmp_path, name):
    req = request([make_seat("codex", "planner")])
    legacy = {"schema": w.WIRE_SCHEMA, **req, "status": "PASS", "results": {}} if "pass" in name else \
        {"status": "PASS", "diagnostic_only": True, "outcomes": [], "attempted": 0, "expected": 1,
         "abort": None, "unvisited": []}
    p = tmp_path / name
    p.write_text(json.dumps(legacy))
    assert w.native_rows(p) == ()
    assert w.native_rows(tmp_path / "absent.json") == ()


def mutate(fn):
    def apply(tmp_path):
        path, record = build(tmp_path, verdicts=("PASS", "FAIL"))
        fn(record)
        return path, record
    return apply


MUTATIONS = {
    "extra_field": lambda r: r.update(bogus=1),
    "missing_field": lambda r: r.pop("cleanup"),
    "pre_hook": lambda r: r.update(finalized_utc="2026-11-02T10:00:00Z"),
    "status_flip_pass": lambda r: r.update(status="PASS"),
    "attempted": lambda r: r.update(attempted=5),
    "expected": lambda r: r.update(expected=9),
    "unvisited_dropped": lambda r: r.update(unvisited=[]),
    "outcome_status": lambda r: r["outcomes"][0].update(status="OK"),
    "fail_without_error": lambda r: r["outcomes"][1].pop("error"),
    "fail_blank_error": lambda r: r["outcomes"][1].update(error="  "),
    "outcome_reordered": lambda r: r["outcomes"].reverse(),
    "outcome_role": lambda r: r["outcomes"][0].update(role="critic"),
    "abort_blank": lambda r: r.update(abort=""),
    "check_false": lambda r: next(iter(r["results"].values()))["checks"].update(actor_timeout=False),
    "check_dropped": lambda r: next(iter(r["results"].values()))["checks"].pop("rc1_salvage"),
    "kinds_merged": lambda r: next(iter(r["results"].values())).update(
        evidence_kinds={"native_provider": list(w.CHECKS), "mocked_process_controls": []}),
    "no_requests": lambda r: next(iter(r["results"].values())).update(request_count=0),
    "bad_protocol": lambda r: next(iter(r["results"].values())).update(provider_protocol="messages"),
    "results_for_fail": lambda r: r["results"].update({r["outcomes"][1]["seat"]: next(iter(r["results"].values()))}),
    "request_digest": lambda r: r["request"].update(actor_config_digest=H("z")),
    "seat_unsorted": lambda r: r["request"]["seats"].reverse(),
    "suite_bad": lambda r: r["request"]["suite"].update(a="nothex"),
    "evidence_missing_seat": lambda r: r["evidence"].pop(next(iter(r["evidence"]))),
    "cleanup_pass_unverified": lambda r: r["cleanup"]["seats"][r["outcomes"][0]["seat"]].update(all_verified=False),
    "cleanup_uncertain_not_aborted": lambda r: r["cleanup"].update(cleanup_uncertain=True),
    "cleanup_missing_seat": lambda r: r["cleanup"]["seats"].pop(r["outcomes"][0]["seat"]),
    "producer_blank": lambda r: r["producer"].update(commit=""),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_refused_even_when_resealed(tmp_path, name):
    path, record = mutate(MUTATIONS[name])(tmp_path)
    reseal_write(path, record)  # a consistent self-hash must not launder an inconsistent record
    with pytest.raises(ct.ProjectionError):
        w.native_rows(path)


def test_other_schema_version_declines(tmp_path):
    path, record = build(tmp_path)
    record["schema"] = "epyc.autokernel.actor_wire_final.v2"
    path.write_text(json.dumps(record))
    assert w.native_rows(path) == ()


def test_self_hash_tamper_refused(tmp_path):
    path, record = build(tmp_path)
    record["outcomes"][1]["error"] = "edited after the fact"
    path.write_text(json.dumps(record))  # not resealed
    with pytest.raises(ct.ProjectionError, match="record_sha256"):
        w.native_rows(path)


def test_evidence_tamper_refused(tmp_path):
    path, record = build(tmp_path)
    key = record["outcomes"][0]["seat"]
    (tmp_path / f"{key}.json").write_text("{}")
    with pytest.raises(ct.ProjectionError, match="pin"):
        w.native_rows(path)


def test_evidence_requests_must_rederive(tmp_path):
    path, record = build(tmp_path)
    key = record["outcomes"][0]["seat"]
    ev = tmp_path / f"{key}.json"
    body = json.loads(ev.read_text())
    body["requests"][0]["body"]["n"] = 99
    raw = json.dumps(body).encode()
    ev.write_bytes(raw)
    record["evidence"][key]["sha256"] = hashlib.sha256(raw).hexdigest()
    reseal_write(path, record)
    with pytest.raises(ct.ProjectionError, match="requests_sha256"):
        w.native_rows(path)


def test_project_refuses_stale_or_forged_row(tmp_path):
    path, _ = build(tmp_path)
    row = copy.deepcopy(w.native_rows(path)[0])
    row["record"]["status"] = "PASS"
    with pytest.raises(ct.ProjectionError):
        w.project(row)
    with pytest.raises(ct.ProjectionError):
        w.project({"path": 3})


def test_mirror_matches_research_gate_constants():
    assert len(w.CHECKS) == 9 and w.NATIVE_CHECKS + w.MOCKED_CONTROLS == w.CHECKS
    assert set(w.PROTOCOLS) == {"codex", "claude", "opencode"}


def test_registered_verifier_class_and_no_ladder():
    assert w.SOURCE_KIND in ct.registered()
    assert ct._SOURCE_CLASS[w.SOURCE_KIND] == "verifier"


def test_cli_ingest_end_to_end(tmp_path, capsys):
    fx = tmp_path / "fx"
    fx.mkdir()
    build(fx, verdicts=("PASS", "FAIL"))
    # legacy siblings in the same directory decline, they do not refuse the run
    (fx / "matrix-results.json").write_text(json.dumps({"status": "FAIL"}))
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "ak-actor-wire", "--path", str(fx),
                   "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == [] and report["rows_projected"] == 4
    rows = [r.frame for r in Ledger(ledger).read_all()]
    assert any(f["frame_type"].endswith("evidence_supports_claim/v1") for f in rows)

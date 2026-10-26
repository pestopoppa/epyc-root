"""Native four-load M4.2b projection and fail-closed proof tests; model-free.

All unmodified fixture bytes are native. Mutation cases are explicitly synthetic;
the pinned producer's pure verdict function supplies their independent oracle.
No live ledger, store binary, model/server, API or network is accessed.
"""
import importlib.util
import json
import shutil
import statistics
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from adapters import pb_hol, _pb_hol_m42b as paired  # noqa: E402
import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from ledger import Ledger  # noqa: E402

FX = Path(__file__).parent / "fixtures/belief_p1/pb_hol_m42b"
OUT = "out/w-m4-2b-champion-control-20261024T1240Z"
AS_OF = "2026-10-25T00:00:00Z"


def load(path):
    return json.loads(path.read_text())


def dump(path, doc):
    path.write_text(json.dumps(doc) + "\n")


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def write_rows(path, doc):
    path.write_text("".join(json.dumps(r) + "\n" for r in doc))


@pytest.fixture
def native(tmp_path, monkeypatch):
    run = tmp_path / "native"
    shutil.copytree(FX, run)
    read = paired._read
    # Test-only transport redirection: preserve the exact recorded path and bytes.
    def fixture_read(path):
        if path == paired.PRIOR_VERDICT:
            path = run / "PRIOR-VERDICT.json"
        return read(path)
    monkeypatch.setattr(paired, "_read", fixture_read)
    return run


def tuple_for(native):
    ns = pb_hol.native_rows(native)
    assert len(ns) == 1
    return pb_hol.project(ns[0])


def oracle(native):
    spec = importlib.util.spec_from_file_location("native_m42b_fixture_oracle", native / "verdict.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prior = {"path": str(paired.PRIOR_VERDICT), "sha256": paired.PRIOR_VERDICT_SHA,
             "conditions": {k: load(native / "PRIOR-VERDICT.json")["conditions"][k] for k in paired.DECIDED}}
    verdict = mod.verdict(native / OUT, prior)
    dump(native / "VERDICT.json", verdict)
    record = load(native / "RUN_RECORD.json")
    record.update(verdict=verdict["verdict"], outcome=verdict["outcome"])
    dump(native / "RUN_RECORD.json", record)
    return verdict


def mutate_runs(native, f):
    for load_dir in sorted((native / OUT).glob("L*")):
        rp = load_dir / "pb_hol_1.jsonl"
        rr = rows(rp)
        f(load_dir.name, rr)
        write_rows(rp, rr)
        summary = load(load_dir / "summary.json")
        for label, arm in summary["arms"].items():
            values = [r["short_ttft_ms"] for r in rr if r.get("kind") == "run" and not r.get("skipped")
                      and (r.get("arm") == label or (r.get("arm") == "C" and label == f"C-{r.get('phase')}"))
                      and type(r.get("short_ttft_ms")) in (int, float)]
            arm.update(ttft_ms=values, median_ms=statistics.median(values))
        dump(load_dir / "summary.json", summary)


def test_native_four_load_projection_and_no_new_warrant(native):
    t = tuple_for(native)
    assert (t.value, t.unit, t.metric_direction, t.reps) == (22.014, "ratio", "lower_better", 3)
    assert [p["loads"] for p in t.extra["c2"]["pairs"]] == [[1, 2], [2, 3], [3, 4]]
    assert t.extra["c2"]["pooled_paired_ratio"] == 0.9984
    assert t.observation["outcome_native"] == "PASS" and t.observation["outcome"] == "null"
    assert t.observation["retrofit"] is True and t.protocol_id == "" and t.category == "CANDIDATE"
    assert ct.grade(t)[:2] == ("Judged", "Located")
    assert ct.grade(t) == ct.grade(replace(t, observation={}, applicability={}))
    assert "not independent" in t.reps_basis
    assert t.applicability["kernel"]["execution_digest"] == paired.ROLE_SHA["candidate"]
    assert len(t.extra["read_time_sha256"]) == 18  # 2 records, 5 source files, prior anchor, 2 window records, 8 load files
    assert "read" in t.extra["digest_caveat"]
    assert t.attestation_sha256 == "433b410ea0152382dfa82c05184026fd125c559bd61b15f5eb25557c3825557b"
    _, _, evidence = ct.to_frames(t, as_of=AS_OF, adapter_id=pb_hol.ADAPTER_ID, authority=pb_hol.AUTHORITY)
    assert evidence["assertion"]["value"] == "22.014"


def test_locator_aliases_and_scratch_dry_ingest_deduplicate(native, tmp_path):
    aliases = [native, native / "out", native / OUT, native / OUT / "L2-candidate"]
    for p in aliases:
        assert ingest_sources.SOURCES["pb-hol"].units(p) == [native]
        assert tuple_for(p).measurement_id == tuple_for(native).measurement_id
    ledger = Ledger(tmp_path / "ledger")
    report = ingest_sources.ingest(ledger, "pb-hol", aliases, as_of=AS_OF, dry_run=True, only_new=True)
    assert report["rows_projected"] == 4 and report["frames_emitted"] == 3 and report["refused"] == []
    assert ingest_sources.SOURCES["pb-hol"].default is None


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra", "role", "number", "window", "escape", "incomplete", "rc", "trip"])
def test_load_record_near_misses_refuse(native, change):
    p = native / OUT / "loads.jsonl"
    rr = rows(p)
    if change == "missing": rr.pop()
    elif change == "duplicate": rr[2] = rr[0]
    elif change == "extra": rr.append(rr[0])
    else:
        key, value = {"role": ("role", "candidate"), "number": ("load", 5), "window": ("window_id", "other"),
                      "escape": ("dir", "../L1-champion"), "incomplete": ("status", "partial"),
                      "rc": ("harness_rc", 1), "trip": ("trip", "guard")}[change]
        rr[0][key] = value
    write_rows(p, rr)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


@pytest.mark.parametrize("key,value", [("planned_loads_done", 3), ("replacements_used", 1), ("stopped", "deadline"), ("out", "../other")])
def test_incomplete_or_unsafe_run_record_refuses(native, key, value):
    p = native / "RUN_RECORD.json"
    doc = load(p); doc[key] = value; dump(p, doc)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


@pytest.mark.parametrize("name", ["PREDECLARATION.md", "AMENDMENT-M4.2b-paired.md", "verdict.py", "pb_hol_1.py", "diag_sampler.py", "PRIOR-VERDICT.json"])
def test_missing_or_hash_mismatched_native_anchor_refuses(native, name):
    p = native / name
    raw = p.read_bytes()
    p.write_bytes(raw + b"\n")
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)
    p.unlink()
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


@pytest.mark.parametrize("field", ["c2", "loads", "conditions", "window", "verdict", "outcome", "decided_from"])
def test_tampered_native_verdict_refuses(native, field):
    p = native / "VERDICT.json"
    doc = load(p); doc[field] = {}; dump(p, doc)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


@pytest.mark.parametrize("proof", ["port_ownership", "graphs_proof", "residency"])
def test_missing_original_proof_refuses(native, proof):
    p = native / OUT / "L1-champion/pb_hol_1.jsonl"
    write_rows(p, [r for r in rows(p) if r.get("kind") != proof])
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


def test_wrong_role_digest_summary_and_jsonl_disagreement_refuse(native):
    p = native / OUT / "L1-champion/summary.json"
    doc = load(p); doc["servers"][0]["binary_sha256"] = paired.ROLE_SHA["candidate"]; dump(p, doc)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


def test_symlink_duplicate_window_extra_load_and_unrecognised_alias_refuse(native):
    p = native / OUT / "L1-champion/summary.json"
    saved = p.with_suffix(".saved"); p.rename(saved); p.symlink_to(saved)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)
    p.unlink(); saved.rename(p)
    other = native / "out/w-foreign"; other.mkdir()
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)
    other.rmdir()
    other = native / OUT / "L5-champion"; other.mkdir()
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)
    other.rmdir()
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native / "not-a-record")


def test_summary_numbers_cannot_override_native_rows(native):
    p = native / OUT / "L2-candidate/summary.json"
    doc = load(p); doc["arms"]["B-off512"]["ttft_ms"][0] += 1; dump(p, doc)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


def test_paired_collision_chronology_is_not_the_older_flat_predicate(native):
    def invalidate(_name, rr):
        for r in rr:
            if r.get("kind") == "run" and str(r.get("arm")).startswith("B-"):
                r["long_finished_before_abort"] = False
                r.update(long_t_send=0, long_ttft_ms=1, short_t_send=1)
                assert pb_hol._m4_valid(r)  # old predicate misses this no-collision case
    mutate_runs(native, invalidate)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


@pytest.mark.parametrize("factor,want", [(1.2, "FAIL_HIGH"), (0.8, "FAIL_LOW")])
def test_native_two_sided_failure_with_producer_oracle(native, factor, want):
    def shift(name, rr):
        for r in rr:
            if name.endswith("candidate") and r.get("kind") == "run" and str(r.get("arm")).startswith("B-"):
                r["short_ttft_ms"] *= factor
    mutate_runs(native, shift)
    v = oracle(native)
    assert v["c2"]["cond"] == want and v["verdict"] == "FAIL"
    t = tuple_for(native)
    assert t.value == v["c2"]["C2_paired"] and t.observation["outcome_native"] == want
    assert "outcome" not in t.observation


def test_drift_is_only_a_flag_using_native_producer_oracle(native):
    def drift(_name, rr):
        solo = [r for r in rr if r.get("kind") == "run" and r.get("arm") == "C"]
        for r in solo[3:]: r["short_ttft_ms"] += 20
    mutate_runs(native, drift)
    v = oracle(native)
    assert v["c2"]["cond"] == "PASS_WINDOW_DRIFT" and v["verdict"] == "PASS"
    t = tuple_for(native)
    assert t.value == 22.014 and t.observation["outcome_native"] == "PASS_WINDOW_DRIFT"
    assert len(t.extra["c2"]["flagged_pairs"]) == 3


def test_caller_native_dictionary_cannot_skip_revalidation(native):
    ns = pb_hol.native_rows(native)
    ns[0]["verdict"]["c2"]["C2_paired"] = 1
    with pytest.raises(ct.ProjectionError): pb_hol.project(ns[0])


@pytest.mark.parametrize("bind_proof", [False, True])
def test_readback_and_cross_load_recipe_inconsistency_refuse(native, bind_proof):
    sp = native / OUT / "L2-candidate/summary.json"
    summary = load(sp)
    argv = summary["servers"][0]["readback"]["proc_cmdline"]
    argv[argv.index("-b") + 1] = "2048"
    dump(sp, summary)
    if bind_proof:
        rp = native / OUT / "L2-candidate/pb_hol_1.jsonl"
        rr = rows(rp)
        for r in rr:
            if r.get("kind") == "port_ownership": r["argv"] = argv
        write_rows(rp, rr)
    with pytest.raises(ct.ProjectionError): pb_hol.native_rows(native)


@pytest.mark.parametrize("relative,key", [("RUN_RECORD.json", "predeclaration_sha256"), (OUT + "/window.json", "window_id")])
def test_duplicate_native_window_or_source_key_refuses_even_identical_value(native, relative, key):
    p = native / relative
    raw = p.read_text().rstrip()
    # Same duplicate value is still ambiguous custody; never let last-key-wins pass it.
    duplicate = json.dumps(key) + ":" + json.dumps(load(p)[key])
    p.write_text(raw[:-1] + "," + duplicate + "}\n")
    with pytest.raises(ct.ProjectionError, match="invalid JSON"):
        pb_hol.native_rows(native)


def test_duplicate_native_jsonl_key_refuses(native):
    p = native / OUT / "L1-champion/pb_hol_1.jsonl"
    raw = p.read_text()
    p.write_text(raw.replace('{"kind": "port_ownership",', '{"kind": "port_ownership", "kind": "port_ownership",', 1))
    with pytest.raises(ct.ProjectionError, match="invalid JSONL"):
        pb_hol.native_rows(native)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")], ids=["NaN", "Infinity", "negative-Infinity"])
@pytest.mark.parametrize("field", ["long_progress_at_send", "long_ttft_ms"])
def test_nonstandard_collision_progress_or_timing_refuses_at_parser(native, field, value):
    p = native / OUT / "L1-champion/pb_hol_1.jsonl"
    rr = rows(p)
    run = next(r for r in rr if r.get("kind") == "run" and str(r.get("arm")).startswith("B-"))
    run[field] = [1, value] if field == "long_progress_at_send" else value
    # Deliberately emits nonstandard JSON constants to prove the INPUT parser refuses;
    # do not change or depend on the native collision predicate/arithmetic.
    write_rows(p, rr)
    with pytest.raises(ct.ProjectionError, match="invalid JSONL"):
        pb_hol.native_rows(native)


@pytest.mark.parametrize("field", ["long_progress_at_send", "long_ttft_ms"])
def test_collision_numeric_exponent_overflow_cannot_bypass_finite_parser(native, field):
    p = native / OUT / "L1-champion/pb_hol_1.jsonl"
    rr = rows(p)
    run = next(r for r in rr if r.get("kind") == "run" and str(r.get("arm")).startswith("B-"))
    run[field] = [1, 1234567.75] if field == "long_progress_at_send" else 1234567.75
    write_rows(p, rr)
    p.write_text(p.read_text().replace("1234567.75", "1e999"))
    with pytest.raises(ct.ProjectionError, match="invalid JSONL"):
        pb_hol.native_rows(native)

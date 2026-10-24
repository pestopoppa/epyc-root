"""VB-UFH12-PARITY: EmbeddingGemma-2 reference-parity gate -> OBSERVATION tuples graded by the one shared ladder."""
import copy
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import repl_embedder_parity as rp  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/champ-gemma-emb2-20261020b/out-gate-probe45")
N_DOCS, N_Q = 6, 3

DOCS = {"st-bf16": [0.9995, 0.9991, 0.9999, 0.9993, 0.9997, 0.9994],
        "gguf-bf16": [0.99999, 0.99998, 0.999991, 0.99997, 0.99999, 0.99998],
        "gguf-q8_0": [0.9961, 0.9972, 0.9958, 0.9969, 0.9963, 0.9975]}
QS = {"st-bf16": [0.9996, 0.9992, 0.9998], "gguf-bf16": [0.99999, 0.99997, 0.99998],
      "gguf-q8_0": [0.9941, 0.9962, 0.9955]}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _identity(model, dtype, runtime):
    ident = {"model": model, "revision": "r" * 40, "dim": 768, "dtype": dtype, "prompt_hash": "p" * 64,
             "runtime": runtime}
    ident["digest"] = rp.derive_index_digest(ident)
    return ident


def _stats(cos, nonfinite=0):
    return {"n": len(cos), "nonfinite_vectors": nonfinite, "cos_min": min(cos), "cos_mean": sum(cos) / len(cos),
            "per_item_cos": cos}


def _items():
    texts = [f"chunk text number {i}" for i in range(N_DOCS)]
    return {
        "files": [{"path": "/x/a.py", "sha256": "a" * 64, "kind": "code", "chars": 10}],
        "chunk_max_chars": 800, "dense_input_max_chars": 800, "n_chunks": N_DOCS, "chunk_kinds": {"code": N_DOCS},
        "chunks": [{"section": "/x/a.py", "start": i, "end": i + 5,
                    "text_sha256": hashlib.sha256(t.encode()).hexdigest()} for i, t in enumerate(texts)],
        "doc_texts": texts,
        "queries": [{"id": f"q{i}", "text": f"query {i}", "code_intent": False} for i in range(N_Q)],
        "query_set_kind": "proxy-first-line", "query_set_is_ufh07": False,
    }


def _lane(lane, docs, qs, nf_d=0, nf_q=0):
    kind = "gguf" if lane.startswith("gguf") else "st"
    dtype = {"st-bf16": "bf16", "gguf-bf16": "bf16", "gguf-q8_0": "q8_0"}[lane]
    runtime = "llama-server-experimental" if kind == "gguf" else "sentence-transformers/transformers/torch-cpu"
    thr = rp.PREDECLARED_THRESHOLDS[lane]
    d, q = _stats(docs, nf_d), _stats(qs, nf_q)
    both = min(d["cos_min"], q["cos_min"])
    return {"threshold": thr, "verdict": rp.derive_verdict(nf_d + nf_q, both, thr),
            "nonfinite_vectors_total": nf_d + nf_q, "cos_min_all_items": both, "docs": d, "queries": q,
            "lane": {"lane": lane, "arm_id": f"eg2-{lane}-768", "index_identity": _identity("m/" + lane, dtype, runtime),
                     "threads": 4, "n_docs": len(docs), "n_queries": len(qs)}}


def parity_doc(items, nonfinite_lane=None):
    lanes = {ln: _lane(ln, DOCS[ln], QS[ln]) for ln in DOCS}
    if nonfinite_lane:
        docs = list(DOCS[nonfinite_lane])
        docs[1] = -1.0
        lanes[nonfinite_lane] = _lane(nonfinite_lane, docs, QS[nonfinite_lane], nf_d=1)
    lanes["st-fp32-textonly"] = {"threshold": None, "verdict": None, "nonfinite_vectors_total": 0,
                                 "cos_min_all_items": 1.0, "docs": _stats([1.0] * N_DOCS), "queries": _stats([1.0] * N_Q),
                                 "lane": {"lane": "st-fp32-textonly", "arm_id": "x", "threads": 4}}
    meta = {k: v for k, v in items.items() if k != "doc_texts"}
    return {"gate": {"thresholds": rp.PREDECLARED_THRESHOLDS, "rule": rp.RULE, "min_chunks": 200,
                     "reference_lane": "st-fp32-full"},
            "reference": {"lane": {"lane": "st-fp32-full", "arm_id": "eg2-st-fp32-768",
                                   "index_identity": _identity("m/ref", "fp32", "sentence-transformers/transformers/torch-cpu"),
                                   "threads": 8}, "nonfinite_vectors": 0},
            "lanes": lanes, "items": meta,
            "scope_complete": rp.derive_scope_complete(items["n_chunks"], len(items["queries"]), items["query_set_is_ufh07"]),
            "scope_note": "PARTIAL: synthetic"}


ST_VERSIONS = {"torch": "2.4.0", "transformers": "5.20.1", "sentence_transformers": "6.1.0"}


def runtime_meta():
    st = lambda: {"runtime": "sentence-transformers/transformers/torch-cpu", "argv": ["repl_emb_parity_gate.py", "encode"],
                  "versions": dict(ST_VERSIONS)}
    gg = lambda: {"runtime": "llama-server production-consolidated-v10", "argv": ["llama-server", "-m", "m.gguf", "-fa", "auto"],
                  "binary_sha256": "b" * 64, "flash_attn_requested": "auto", "flash_attn_resolved": "on"}
    return {"st-fp32-full": st(), "st-bf16": st(), "gguf-bf16": gg(), "gguf-q8_0": gg()}


def write(tmp_path, *, meta=None, tweak=None, nonfinite_lane=None, items=None):
    items = items or _items()
    par = parity_doc(items, nonfinite_lane)
    if tweak:
        tweak(par)
    (tmp_path / "items.json").write_text(json.dumps(items))
    (tmp_path / "parity.json").write_text(json.dumps(par))
    return rp.write_belief_measurements(
        tmp_path, run_id="gp1-dry", producer="repl_emb_parity_gate.py", parity_path=tmp_path / "parity.json",
        items_path=tmp_path / "items.json", runtime_meta=meta if meta is not None else runtime_meta(), emitted_at=_now())


def test_round_trip_every_gated_lane_three_metrics_graded(tmp_path):
    side = write(tmp_path)
    natives = rp.native_rows(side)
    assert len(natives) == 9  # three gated lanes x three metrics; the text-only lane and the reference are not rows
    assert {n["row"]["extra"]["lane"] for n in natives} == set(rp.PREDECLARED_THRESHOLDS)
    for n in natives:
        t = rp.project(n)
        e = n["row"]["extra"]
        assert t.protocol_id == "" and t.attestation_present is True and t.source_kind == rp.SOURCE_KIND
        assert ct.grade(t)[:2] == ("Judged", "Located")
        assert t.observation["outcome_native"] == "PASS" and e["gate_verdict"] == "PASS"
        assert e["reference"]["lane"] == "st-fp32-full" and e["scope_complete"] is False
        assert e["query_set_kind"] == "proxy-first-line" and len(e["input_set_digest"]) == 64
    by = {(n["row"]["extra"]["lane"], n["row"]["metric"]): n["row"] for n in natives}
    q8 = by[("gguf-q8_0", rp.M_MIN)]
    allv = DOCS["gguf-q8_0"] + QS["gguf-q8_0"]
    assert q8["value"] == min(allv) and q8["metric_direction"] == "higher_better"
    assert by[("gguf-q8_0", rp.M_MEAN)]["value"] == pytest.approx(sum(allv) / len(allv))
    nf = by[("gguf-q8_0", rp.M_NONFINITE)]
    assert nf["value"] == 0 and nf["metric_direction"] == "lower_better"
    assert q8["extra"]["binary_sha256"] == "b" * 64 and q8["extra"]["flash_attn_resolved"] == "on"
    assert by[("st-bf16", rp.M_MIN)]["extra"]["binary_sha256"] is None
    assert by[("st-bf16", rp.M_MIN)]["extra"]["versions"] == ST_VERSIONS
    assert rp.frames_for_sidecar(side, as_of=_now())


def test_nonfinite_lane_fails_the_gate_and_counts(tmp_path):
    side = write(tmp_path, nonfinite_lane="gguf-bf16")
    rows = {(n["row"]["extra"]["lane"], n["row"]["metric"]): n["row"] for n in rp.native_rows(side)}
    assert rows[("gguf-bf16", rp.M_NONFINITE)]["value"] == 1
    assert rows[("gguf-bf16", rp.M_MIN)]["value"] == -1.0
    assert rows[("gguf-bf16", rp.M_MIN)]["extra"]["gate_verdict"] == "FAIL"
    assert rows[("st-bf16", rp.M_MIN)]["extra"]["gate_verdict"] == "PASS"
    assert ct.grade(rp.project({"row": rows[("gguf-bf16", rp.M_NONFINITE)], "sidecar_path": "",
                                "attestation_present": True}))[:2] == ("Judged", "Located")


def test_a_cos_min_below_threshold_is_a_recorded_fail_not_dropped(tmp_path):
    def tweak(par):
        par["lanes"]["gguf-q8_0"] = _lane("gguf-q8_0", [0.9790] + DOCS["gguf-q8_0"][1:], QS["gguf-q8_0"])
    side = write(tmp_path, tweak=tweak)
    row = next(n["row"] for n in rp.native_rows(side)
               if n["row"]["extra"]["lane"] == "gguf-q8_0" and n["row"]["metric"] == rp.M_MIN)
    assert row["extra"]["gate_verdict"] == "FAIL" and row["value"] == pytest.approx(0.979)


def test_complete_scope_is_rederived_not_trusted(tmp_path):
    items = _items()
    items["query_set_kind"] = "file:/x/probe45-intake1357.jsonl"
    items["query_set_is_ufh07"] = True
    side = write(tmp_path, items=items)  # 6 chunks and 3 queries: still PARTIAL even with the named query file
    assert all(n["row"]["extra"]["scope_complete"] is False for n in rp.native_rows(side))
    row = json.loads(side.read_text().splitlines()[0])
    row["extra"]["scope_complete"] = True
    assert any("scope_complete does not re-derive" in p for p in rp.row_problems(ns.seal(row)))


def test_values_must_rederive_from_the_per_item_cosines(tmp_path):
    side = write(tmp_path)
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    cmin = next(r for r in rows if r["metric"] == rp.M_MIN)
    assert rp.row_problems(cmin) == []
    assert any("re-derived" in p for p in rp.row_problems(ns.seal(dict(cmin, value=0.5))))
    bent = copy.deepcopy(cmin)
    bent["extra"]["docs_cos"][0] = 0.1  # per-item changed, summary kept
    assert any("do not re-derive" in p for p in rp.row_problems(ns.seal(bent)))
    flipped = copy.deepcopy(cmin)
    flipped["extra"]["gate_verdict"] = "FAIL"
    assert any("gate_verdict does not re-derive" in p for p in rp.row_problems(ns.seal(flipped)))
    thr = copy.deepcopy(cmin)
    thr["extra"]["threshold"] = 0.5
    assert any("predeclared threshold" in p for p in rp.row_problems(ns.seal(thr)))
    nf = copy.deepcopy(next(r for r in rows if r["metric"] == rp.M_NONFINITE))
    nf["extra"]["nonfinite_docs"] = 2
    assert rp.row_problems(ns.seal(nf))
    dig = copy.deepcopy(cmin)
    dig["extra"]["input_set"]["queries_digest"] = "0" * 64
    assert any("input_set_digest does not re-derive" in p for p in rp.row_problems(ns.seal(dig)))


def test_tampered_or_foreign_rows_void_the_file(tmp_path):
    side = write(tmp_path)
    lines = side.read_text().splitlines()
    row = json.loads(lines[0])
    row["claim"] += " (edited)"  # not re-sealed
    side.write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
    assert rp.native_rows(side) == ()
    with pytest.raises(ct.ProjectionError):
        rp.project({"row": {"schema": "other"}})
    with pytest.raises(ct.ProjectionError):
        rp.project({"row": dict(json.loads(lines[1]), protocol_id="P-X-1")})


def test_no_sidecar_zero_rows(tmp_path):
    assert rp.native_rows(tmp_path / rp.SIDECAR_NAME) == ()


def test_mutated_attestation_grades_down(tmp_path):
    side = write(tmp_path)
    (tmp_path / "parity.json").write_text((tmp_path / "parity.json").read_text() + " ")
    nat = rp.native_rows(side)
    assert len(nat) == 9
    for n in nat:
        t = rp.project(n)
        assert t.attestation_present is False and t.attestation_verified is None
        assert ct.grade(t)[:2] == ("Judged", "Located")


@pytest.mark.parametrize("lane,key", [
    ("gguf-bf16", "binary_sha256"), ("gguf-bf16", "flash_attn_requested"), ("gguf-bf16", "flash_attn_resolved"),
    ("gguf-bf16", "argv"), ("gguf-bf16", "runtime"), ("st-bf16", "versions"), ("st-bf16", "argv"),
    ("st-fp32-full", "versions"), ("st-fp32-full", "runtime")])
def test_missing_identity_is_refused_never_defaulted(tmp_path, lane, key):
    meta = runtime_meta()
    del meta[lane][key]
    with pytest.raises(rp.CaptureError, match="runtime meta|incomplete|required"):
        write(tmp_path, meta=meta)
    assert not (tmp_path / rp.SIDECAR_NAME).exists()


def test_missing_lane_meta_and_partial_versions_refused(tmp_path):
    meta = runtime_meta()
    del meta["gguf-q8_0"]
    with pytest.raises(rp.CaptureError, match="no entry for lane"):
        write(tmp_path, meta=meta)
    meta = runtime_meta()
    del meta["st-bf16"]["versions"]["torch"]
    with pytest.raises(rp.CaptureError, match="versions"):
        write(tmp_path, meta=meta)
    meta = runtime_meta()
    meta["gguf-bf16"]["flash_attn_resolved"] = "default"
    with pytest.raises(rp.CaptureError, match="flash_attn_resolved"):
        write(tmp_path, meta=meta)
    meta = runtime_meta()
    meta["gguf-bf16"]["binary_sha256"] = "nothex"
    with pytest.raises(rp.CaptureError, match="binary_sha256"):
        write(tmp_path, meta=meta)


def test_writer_refuses_inconsistent_gate_record(tmp_path):
    def wrong_verdict(par):
        par["lanes"]["st-bf16"]["verdict"] = "FAIL"
    with pytest.raises(rp.CaptureError, match="does not re-derive"):
        write(tmp_path, tweak=wrong_verdict)

    def wrong_thr(par):
        par["lanes"]["gguf-bf16"]["threshold"] = 0.5
    with pytest.raises(rp.CaptureError, match="predeclared"):
        write(tmp_path, tweak=wrong_thr)

    def bad_scope(par):
        par["scope_complete"] = True
    with pytest.raises(rp.CaptureError, match="scope_complete"):
        write(tmp_path, tweak=bad_scope)

    def drop_scope(par):
        del par["scope_complete"]
    with pytest.raises(rp.CaptureError, match="scope_complete"):
        write(tmp_path, tweak=drop_scope)


def test_items_json_must_be_the_set_the_run_used(tmp_path):
    items = _items()
    par = parity_doc(items)
    other = copy.deepcopy(items)
    other["doc_texts"][0] = "different text"
    (tmp_path / "items.json").write_text(json.dumps(other))
    (tmp_path / "parity.json").write_text(json.dumps(par))
    with pytest.raises(rp.CaptureError, match="text_sha256"):
        rp.write_belief_measurements(tmp_path, run_id="r", producer="p", parity_path=tmp_path / "parity.json",
                                     items_path=tmp_path / "items.json", runtime_meta=runtime_meta(), emitted_at=_now())


def test_retrospective_parity_json_is_never_backfilled(tmp_path):
    items = _items()
    (tmp_path / "items.json").write_text(json.dumps(items))
    p = tmp_path / "parity.json"
    p.write_text(json.dumps(parity_doc(items)))
    old = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc).timestamp()
    os.utime(p, (old, old))
    with pytest.raises(rp.CaptureError, match="retrospective"):
        rp.write_belief_measurements(tmp_path, run_id="r", producer="p", parity_path=p, items_path=tmp_path / "items.json",
                                     runtime_meta=runtime_meta(), emitted_at=_now())


def test_reader_refuses_a_row_emitted_long_after_the_file(tmp_path):
    side = write(tmp_path)
    row = json.loads(side.read_text().splitlines()[0])
    row["emitted_at"] = row["date"] = "2099-01-01T00:00:00Z"
    assert any("retrospective" in p for p in rp.row_problems(ns.seal(row)))


def test_cli_write(tmp_path, capsys):
    items = _items()
    (tmp_path / "items.json").write_text(json.dumps(items))
    (tmp_path / "parity.json").write_text(json.dumps(parity_doc(items)))
    (tmp_path / "meta.json").write_text(json.dumps(runtime_meta()))
    args = ["write", "--parity", str(tmp_path / "parity.json"), "--items", str(tmp_path / "items.json"),
            "--runtime-meta", str(tmp_path / "meta.json"), "--out-dir", str(tmp_path), "--run-id", "r"]
    assert rp.main(args) == 0
    assert json.loads(capsys.readouterr().out)["rows"] == 9


@pytest.mark.skipif(not (REAL / "parity.json").is_file(), reason="2026-10-20 probe45 gate record absent")
def test_real_2026_10_20_record_has_the_shape_the_reader_needs_but_is_not_backfilled(tmp_path, monkeypatch):
    for name in ("parity.json", "items.json"):
        shutil.copy2(REAL / name, tmp_path / name)  # copy2 keeps the 2026-10-20 mtime
    meta = runtime_meta()
    with pytest.raises(rp.CaptureError, match="retrospective"):
        rp.write_belief_measurements(tmp_path, run_id="real", producer="p", parity_path=tmp_path / "parity.json",
                                     items_path=tmp_path / "items.json", runtime_meta=meta, emitted_at=_now())
    # shape fidelity only (NOT a back-fill): with the lag guard lifted the writer re-derives from the real record
    monkeypatch.setattr(rp, "MAX_CAPTURE_LAG_S", 10 ** 9)
    side = rp.write_belief_measurements(tmp_path, run_id="real", producer="p", parity_path=tmp_path / "parity.json",
                                        items_path=tmp_path / "items.json", runtime_meta=meta, emitted_at=_now())
    natives = rp.native_rows(side)
    real = json.loads((tmp_path / "parity.json").read_text())
    assert len(natives) == 3 * len([1 for r in real["lanes"].values() if r["threshold"] is not None])
    for n in natives:
        e = n["row"]["extra"]
        assert e["scope_complete"] is True and e["n_docs"] == 211 and e["n_queries"] == 45
        assert e["gate_verdict"] == real["lanes"][e["lane"]]["verdict"]
        assert math.isfinite(n["row"]["value"])

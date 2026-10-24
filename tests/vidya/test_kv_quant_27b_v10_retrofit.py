"""Retrofit reader for the 2026-09-22 pre-hook v10 MI210 KV-quant run directories (VB-KVQ-V10-RETRO)."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

VIDYA = Path(__file__).resolve().parents[2] / "scripts/vidya"
sys.path.insert(0, str(VIDYA))

from adapters import kv_quant_27b_v10 as kv  # noqa: E402
import claim_tuple as ct  # noqa: E402
import loop_beliefs as lb  # noqa: E402
import ingest_sources as ing  # noqa: E402

BUILD = "gpu-20260921-ffc1bac82"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _w(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1), encoding="utf-8")


def _record(depth: str, i: int, decode_tps: float) -> dict:
    tokens, ptok = 400 + i, 2000 + i
    return {"completion_tokens": tokens, "decode_ms": tokens / decode_tps * 1000.0, "depth": depth,
            "finish_reason": "stop", "prompt_tokens": ptok, "prompt_ms": ptok / 800.0 * 1000.0,
            "response_sanity": {"passed": True}, "semantic_validation": {"passed": True}}


def _cell(run: Path, ident: dict, name: str, ktype: str, depth: str, tps: float, status="ok") -> None:
    cd = run / "runs" / f"{name}_{depth}_rep1"
    if status != "ok":
        _w(cd / "result.json", {"cell": name, "depth": depth, "rep": 1, "status": "error", "error": "boom"})
        return
    recs = [_record(depth, i, tps) for i in range(3)]
    res = {"cell": name, "depth": depth, "rep": 1, "status": "ok", "records": recs,
           "completion_tokens": sum(r["completion_tokens"] for r in recs),
           "decode_ms": sum(r["decode_ms"] for r in recs),
           "prompt_tokens": sum(r["prompt_tokens"] for r in recs),
           "prompt_ms": sum(r["prompt_ms"] for r in recs),
           "kv_k_mib": 100.0, "kv_v_mib": 100.0, "post_cleanup_clean": True,
           "residency": {"passed": True, "full_target_offload": True, "kv_types_and_positive_buffers": True,
                         "requested_kv": {"k": ktype, "v": ktype}}}
    res["decode_tps"] = res["completion_tokens"] / res["decode_ms"] * 1000.0
    res["prompt_tps"] = res["prompt_tokens"] / res["prompt_ms"] * 1000.0
    _w(cd / "result.json", res)
    _w(cd / "server_argv.json", [ident["binary"]["binary"], "-m", ident["target_model"]["path"], "-c", "65536",
                                 "-ngl", "all", "-dev", "ROCm0", "-fa", "on", "--cache-type-k", ktype,
                                 "--cache-type-v", ktype])


@pytest.fixture()
def sweep(tmp_path, monkeypatch):
    kv._run_identity.cache_clear()
    harness = b"# stub harness\n"
    monkeypatch.setattr(kv, "PRODUCER_SHA256", _sha(harness))
    root = tmp_path / "sweep"

    def make(tag: str, cells, ts: str = "20260922T135201Z") -> Path:
        run = root / f"run-20260922{tag}" / f"run-{ts}"
        build = tmp_path / f"kernels/builds/{BUILD}/bin"
        build.mkdir(parents=True, exist_ok=True)
        binary = build / "llama-server"
        binary.write_bytes(b"binary")
        lib = build / "libggml-hip.so.0"
        lib.write_bytes(b"lib")
        model = tmp_path / "Qwen3.8-27B-Q8_0.gguf"
        model.write_bytes(b"weights")
        (run).mkdir(parents=True, exist_ok=True)
        (run / "harness_source.py").write_bytes(harness)
        msha = "a" * 64
        ident = {"valid": True, "reason": "ok", "harness_valid": True,
                 "binary": {"binary": str(binary), "binary_sha256": _sha(b"binary"),
                            "expected_binary_sha256": _sha(b"binary"), "binary_sha256_matches": True,
                            "linkage_receipt": {"inspected_libraries": [{"path": str(lib), "sha256": _sha(b"lib")}]}},
                 "source": {"head_matches": True, "branch_matches": True, "clean": True,
                            "head": "ffc1bac82eeca6f9099e1ccd9ba49703c460a115",
                            "expected_head": "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"},
                 "harness": {"sha256": _sha(harness)}, "harness_snapshot": {"sha256": _sha(harness)},
                 "target_model": {"path": str(model), "sha256": msha, "bytes": len(b"weights")}}
        _w(run / "identities.json", ident)
        _w(run / "plan.json", {"target_model": {"sha256": msha}})
        for name, ktype, depth, tps, status in cells:
            _cell(run, ident, name, ktype, depth, tps, status)
        return run

    make.root = root
    return make


OK_CELLS = [("A_f16_kv", "f16", "d2k", 33.0, "ok"), ("B_q8_0_kv", "q8_0", "d2k", 32.0, "ok"),
            ("B_q8_0_kv", "q8_0", "d32k", 24.0, "ok")]


def test_ok_cells_project_two_metrics_each_judged_located(sweep):
    run = sweep("c", OK_CELLS)
    rows = kv.retrofit_rows(run)
    assert len(rows) == 6
    tuples = [kv.project_retrofit(r) for r in rows]
    for t in tuples:
        assert t.protocol_id == "" and t.reps == 1 and t.observation["retrofit"] is True
        assert t.applicability["knob_family"] == "kv_profile" and t.applicability["backend"] == "gpu"
        assert t.applicability["model_sha256"] == "a" * 64 and t.applicability["build_sha"] == "ffc1bac82"
        q, tt, reasons = ct.grade(t)
        assert (q, tt) == ("Judged", "Located"), (q, tt, reasons)
    dec = {t.measurement_id: t for t in tuples if t.metric == "gpu_decode_tps"}
    q8 = next(t for k, t in dec.items() if "B_q8_0_kv:d2k" in k)
    assert q8.value == pytest.approx(32.0, rel=1e-6)
    assert q8.observation["anchor_value"] == pytest.approx(33.0, rel=1e-6)   # f16 same depth
    d32 = next(t for k, t in dec.items() if "d32k" in k)
    assert "anchor_value" not in d32.observation                              # f16 d32k absent: no anchor
    f16 = next(t for k, t in dec.items() if "A_f16_kv" in k)
    assert f16.category == "BASELINE" and q8.category == "CANDIDATE"


def test_error_runs_decline_and_never_project(sweep):
    run = sweep("b", [("A_f16_kv", "f16", "d2k", 0.0, "error"), ("B_q8_0_kv", "q8_0", "d2k", 0.0, "error")])
    assert kv.retrofit_rows(run) == []


def test_refuses_on_rehash_mismatch(sweep):
    run = sweep("c", OK_CELLS)
    (run / "harness_source.py").write_bytes(b"tampered")
    with pytest.raises(ct.ProjectionError, match="harness_source"):
        kv.retrofit_rows(run)
    kv._run_identity.cache_clear()
    run2 = sweep("c", OK_CELLS)
    binary = Path(json.loads((run2 / "identities.json").read_text())["binary"]["binary"])
    binary.write_bytes(b"swapped")
    with pytest.raises(ct.ProjectionError, match="binary on disk"):
        kv.retrofit_rows(run2)


def test_refuses_when_rate_does_not_rederive(sweep):
    run = sweep("c", OK_CELLS)
    p = run / "runs/A_f16_kv_d2k_rep1/result.json"
    res = json.loads(p.read_text())
    res["decode_tps"] *= 1.5
    p.write_text(json.dumps(res))
    with pytest.raises(ct.ProjectionError, match="decode_tps"):
        kv.project_retrofit(kv.retrofit_rows(run)[0])


def test_refuses_kv_type_mismatch(sweep):
    run = sweep("c", OK_CELLS)
    p = run / "runs/B_q8_0_kv_d2k_rep1/server_argv.json"
    argv = json.loads(p.read_text())
    argv[argv.index("--cache-type-v") + 1] = "f16"
    p.write_text(json.dumps(argv))
    with pytest.raises(ct.ProjectionError, match="KV types"):
        kv.retrofit_rows(run)


def test_ingest_source_units_and_loop_beliefs_knob_tier(sweep):
    sweep("a", [("A_f16_kv", "f16", "d2k", 0.0, "error")], ts="20260922T133646Z")
    sweep("c", OK_CELLS)
    src = ing.SOURCES["kv-quant-27b-v10-retrofit"]
    assert len(src.units(sweep.root)) == 2
    run = sweep.root / "run-20260922c" / "run-20260922T135201Z"
    frames = []
    for row in kv.retrofit_rows(run):
        frames.extend(ct.to_frames(kv.project_retrofit(row), as_of="2026-10-24T00:00:00Z", adapter_id=kv.ADAPTER_ID))
    target = lb.Target.from_mapping({"model_file": "Qwen3.8-27B-Q8_0.gguf", "quant": "Q8_0", "backend": "gpu",
                                     "role": "worker", "knob_families": ["kv_profile"]})
    ev = lb.evaluate_frames(frames, [target], as_of="2026-10-24T01:00:00Z")
    assert ev["tiers"]["knob"] == 6 and ev["tiers"].get("host", 0) == 0

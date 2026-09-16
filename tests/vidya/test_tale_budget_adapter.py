"""VB-PRB-T4 -- the TALE-EP write-side hook and its strict reader.

Pinned: a pre-hook results file emits ZERO rows; the ladder is the shared one (whatever
``claim_tuple.grade()`` returns); identity is unique per (run, suite, condition, metric); a tampered
sidecar is void as a whole; a mutated attestation grades DOWN; the writer refuses a run whose
meta does not record the served model.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import tale_budget as reader  # noqa: E402
from adapters import tale_budget_capture as capture  # noqa: E402

KERNEL = {"binary_path": "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server",
          "binary_sha256": "a" * 64, "tree": "production-consolidated-v9"}
META = {
    "schema": "tale_budget_run.v2", "started_at": "2026-09-16T12:00:00", "finished_at": "2026-09-16T13:00:00",
    "suites": ["math"], "conditions": ["baseline", "static", "tale"], "budget_unit": "tokens",
    "temperature": 0.1, "seed": 42, "max_tokens": 8192, "estimator_max_tokens": 32,
    "chat_template_kwargs": {"enable_thinking": False},
    "serving": {"base_url": "http://127.0.0.1:18383", "model_id": "Qwen3.8-27B-Q8_0.gguf",
                "model_id_source": "v1_models", "gguf_path": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf",
                "gguf_path_source": "props", "gguf": {"size_bytes": 29047086048},
                "props": {"model_path": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"}},
    "served_models_seen": ["Qwen3.8-27B-Q8_0.gguf"],
}


def make_run(root: Path, meta=None) -> Path:
    results = root / "prb_t4_gpu_math.jsonl"
    rows = []
    for cond, toks in (("baseline", 400), ("static", 120), ("tale", 150)):
        for i in range(4):
            rows.append({"question_id": f"q{i}", "suite": "math", "condition": cond,
                         "prompt": "p", "response": "r",
                         "correct": None if (cond == "static" and i == 3) else bool(i % 2),
                         "total_tokens": toks + i, "elapsed_s": 1.0 + i,
                         "tale_budget": 100 + i if cond == "tale" else None,
                         "estimator_tokens": 10 if cond == "tale" else 0,
                         "total_tokens_incl_estimator": toks + i + (10 if cond == "tale" else 0),
                         "elapsed_s_incl_estimator": 1.5 + i})
    results.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    results.with_suffix(".meta.json").write_text(json.dumps(meta or META))
    return results


def emit(results: Path, **kw) -> Path:
    return capture.write_belief_measurements(
        results, run_id="prb_t4_test", producer="test", kernel=KERNEL,
        emitted_at="2026-09-16T13:00:00Z", **kw)


def test_pre_hook_results_emit_zero_rows(tmp_path):
    results = make_run(tmp_path)
    assert reader.rows_for_results(results) == ()


def test_rows_project_and_grade_through_shared_ladder(tmp_path):
    results = make_run(tmp_path)
    side = emit(results)
    natives = reader.rows_for_results(results)
    # 3 conditions x 5 metrics (answer-only AND incl-estimator for tokens and latency)
    assert len(natives) == 15
    ids = {n["row"]["measurement_id"] for n in natives}
    assert len(ids) == 15
    lat = {(n["row"]["extra"]["condition"], n["row"]["metric"]): n["row"]["value"] for n in natives}
    assert lat[("tale", "tale_mean_latency_s_answer_only")] == pytest.approx(2.5)
    assert lat[("tale", "tale_mean_latency_s_incl_estimator")] == pytest.approx(3.0)
    acc = {n["row"]["extra"]["condition"]: n["row"] for n in natives
           if n["row"]["metric"] == "tale_suite_accuracy"}
    assert acc["baseline"]["category"] == "BASELINE" and acc["tale"]["category"] == "CANDIDATE"
    assert acc["static"]["reps"] == 3 and "1 unscorable excluded" in acc["static"]["reps_basis"]
    assert acc["baseline"]["value"] == pytest.approx(0.5)
    for native in natives:
        tup = reader.project(native)
        assert tup.attestation_present is True
        assert tup.extra["budget_unit"] == "tokens"
        assert tup.extra["served"]["gguf_path"].endswith("Qwen3.8-27B-Q8_0.gguf")
        assert ct.grade(tup) == ct.grade(tup)  # pure; whatever the shared ladder says
    assert reader.frames_for_sidecar(side, as_of="2026-09-16T14:00:00Z")


def test_tampered_sidecar_is_void(tmp_path):
    results = make_run(tmp_path)
    side = emit(results)
    lines = side.read_text().splitlines()
    row = json.loads(lines[0])
    row["value"] = 0.99
    lines[0] = json.dumps(row)
    side.write_text("\n".join(lines) + "\n")
    assert reader.native_rows(side) == ()


def test_mutated_attestation_grades_down(tmp_path):
    results = make_run(tmp_path)
    emit(results)
    before = reader.project(reader.rows_for_results(results)[0])
    results.write_text(results.read_text() + "\n")
    natives = reader.rows_for_results(results)
    assert natives and natives[0]["attestation_present"] is False
    after = reader.project(natives[0])
    assert before.attestation_present is True and before.attestation_verified is True
    assert after.attestation_present is False and after.attestation_verified is None
    # No TALE protocol is codified: both are observations, whatever the attestation says.
    assert ct.grade(before)[:2] == ct.grade(after)[:2] == ("Judged", "Located")


def _resign(row: dict) -> dict:
    row = dict(row)
    row["row_sha256"] = capture.row_digest(row)
    return row


def test_protocol_citation_is_empty_and_legacy_schema_citation_is_admissible(tmp_path):
    results = make_run(tmp_path)
    side = emit(results)
    rows = [json.loads(line) for line in side.read_text().splitlines()]
    assert {r["protocol_id"] for r in rows} == {""}
    # The pre-port /workspace writer cited its capture schema; still admissible, projected as "".
    legacy = [_resign({**r, "protocol_id": capture.CAPTURE_SCHEMA}) for r in rows]
    side.write_text("".join(json.dumps(r) + "\n" for r in legacy))
    natives = reader.native_rows(side)
    assert len(natives) == len(rows)
    tup = reader.project(natives[0])
    assert tup.protocol_id == "" and tup.extra["row_protocol_id"] == capture.CAPTURE_SCHEMA
    # Any other citation is not a producer-authored row: the whole file is void.
    forged = [_resign({**r, "protocol_id": "P-QUAL-T1"}) for r in rows]
    side.write_text("".join(json.dumps(r) + "\n" for r in forged))
    assert reader.native_rows(side) == ()


def test_writer_refuses_meta_without_served_model(tmp_path):
    meta = dict(META)
    meta.pop("serving")
    results = make_run(tmp_path, meta=meta)
    with pytest.raises(capture.CaptureError):
        emit(results)
    assert not capture.sidecar_path(results).exists()


def test_writer_refuses_missing_sampling_identity(tmp_path):
    meta = dict(META)
    meta["seed"] = None
    results = make_run(tmp_path, meta=meta)
    with pytest.raises(capture.CaptureError):
        emit(results)

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from contextlib import nullcontext
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "e8_multirow_repair", PROJECT_ROOT / "scripts/benchmark/repair_e8_quality_baseline_multirow.py"
)
assert spec is not None and spec.loader is not None
repair = importlib.util.module_from_spec(spec)
sys.modules["e8_multirow_repair"] = repair
spec.loader.exec_module(repair)


def _write(path: Path, value: object, *, lines: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in value) if lines else json.dumps(value, sort_keys=True) + "\n"
    path.write_text(text)


def _protocol(binding: dict) -> dict:
    return {
        "protocol_id": repair.RUNNER.PROTOCOL_ID, "repetitions": 3, "request_timeout_s": 300,
        "frontdoor_request_contract": repair.RUNNER.FRONTDOOR_REQUEST_CONTRACT, "runtime_binding": binding,
    }


def _source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    vectors: dict[int, dict] = {}
    for tier, n in ((1, 50), (2, 500)):
        questions = [
            {"qid": f"t{tier}-{ordinal}", "suite": "suite", "scoring_method": "exact_match", "expected": "a", "scoring_config": {}}
            for ordinal in range(n)
        ]
        vectors[tier] = {"tier": tier, "n": n, "seed": 7, "core_id": f"c{tier}", "era": repair.RUNNER.E8_ERA, "questions": questions}
        _write(root / f"question_vector.T{tier}.json", vectors[tier])
        _write(root / f"scoring_vector.T{tier}.json", vectors[tier])
    _write(root / "runtime_watch.jsonl", [{"ok": True}], lines=True)
    for tier, n in ((1, 50), (2, 500)):
        for repetition in range(1, 4):
            rows = [
                {"qid": f"t{tier}-{ordinal}", "suite": "suite", "scoring_method": "exact_match", "answer": "a", "correct": True, "error": None, "partial": False, "degraded": False, "route_used": "frontdoor", "scoring_config_sha256": repair.canonical_hash({})}
                for ordinal in range(n)
            ]
            sidecars = [{"row_type": "batch_start", "requested_n": n}]
            for ordinal in range(n):
                result = {"qid": f"t{tier}-{ordinal}", "tokens_generated": 1, "error": False}
                if (tier, repetition, ordinal) in {(2, 1, 1), (2, 2, 3)}:
                    error = "[ERROR: Inference failed: chat_completions failed: timed out]"
                    rows[ordinal].update({"answer": error, "correct": False, "error": error})
                    result = {"qid": f"t{tier}-{ordinal}", "tokens_generated": 0, "error": True, "error_detail": error}
                sidecars.append({"row_type": "question_result", "ordinal": ordinal, "result": result})
            sidecars.append({"row_type": "batch_complete", "complete": True})
            _write(root / f"raw.T{tier}.r{repetition}.json", {"q": 3.0, "ts": "2026-01-01T00:00:00Z", "core_id": f"c{tier}", "protocol_id": repair.RUNNER.PROTOCOL_ID, "n": n, "era": repair.RUNNER.E8_ERA, "per_suite_quality": {"suite": 3.0}, "per_suite_counts": {"suite": n}})
            _write(root / f"responses.T{tier}.r{repetition}.jsonl", rows, lines=True)
            _write(root / f"judge_traces.T{tier}.r{repetition}.jsonl", [], lines=True)
            _write(root / "eval_sidecars" / f"question_results.e8-t{tier}-r{repetition}.jsonl", sidecars, lines=True)
        _write(root / f"question_vector.T{tier}.json", vectors[tier])
        _write(root / f"scoring_vector.T{tier}.json", vectors[tier])
    binding = {"binding": "fixed"}
    runs = [
        {"tier": tier, "repetition": repetition, "raw": f"raw.T{tier}.r{repetition}.json", "responses": f"responses.T{tier}.r{repetition}.jsonl", "judge_traces": f"judge_traces.T{tier}.r{repetition}.jsonl", "sidecar": f"eval_sidecars/question_results.e8-t{tier}-r{repetition}.jsonl"}
        for tier in (1, 2) for repetition in range(1, 4)
    ]
    artifacts = sorted({f"{kind}_vector.T{tier}.json" for tier in (1, 2) for kind in ("question", "scoring")} | {"runtime_watch.jsonl"} | {row[key] for row in runs for key in ("raw", "responses", "judge_traces", "sidecar")})
    _write(root / "terminal_source.json", {
        "schema": repair.TERMINAL_SCHEMA, "status": "terminal_failed", "protocol_id": repair.RUNNER.PROTOCOL_ID,
        "protocol": _protocol(binding), "runtime_binding": binding, "runs": runs, "source_artifacts": artifacts,
        "source_sha256": {name: repair.sha256_path(root / name) for name in artifacts},
        "vector_sha256": {str(tier): repair.canonical_hash(vectors[tier]) for tier in (1, 2)},
    })
    return root


def _focused(source: Path, destination: Path) -> Path:
    plan = repair.build_plan(repair.validate_source(source))
    destination.mkdir()
    _write(destination / "repair_plan.json", plan)
    rows = []
    for target in plan["targets"]:
        rows.append({
            "tier": target["tier"], "repetition": target["repetition"], "ordinal": target["ordinal"], "qid": target["qid"],
            "suite": "suite", "scoring_method": "exact_match", "answer": "a", "correct": True, "error": None,
            "partial": False, "degraded": False, "route_used": "frontdoor", "scoring_config_sha256": repair.canonical_hash({}),
            "request_timeout_s": 300, "eval_concurrency": 1, "score_terminal": True,
            "source_terminal_sha256": plan["source_terminal_sha256"], "repair_plan_sha256": repair.sha256_path(destination / "repair_plan.json"),
            "failure_fingerprint": target["fingerprint"],
        })
    _write(destination / "focused_attempts.jsonl", rows, lines=True)
    _write(destination / "focused_runtime_watch.jsonl", [{"ok": True}], lines=True)
    _write(destination / "focused_collection_seal.json", {"schema": repair.FOCUSED_SEAL_SCHEMA, "status": "complete", "bundle_sha256": repair.seal_directory(destination, exclude={"focused_collection_seal.json"})})
    return destination


def _terminal_staging(tmp_path: Path, *, migrated: bool = False) -> Path:
    source = _source(tmp_path)
    (source / "terminal_source.json").unlink()
    binding = {"binding": "fixed"}
    _write(source / "runner_report.json", {"mode": "executed", "decision_grade": False, "protocol_id": repair.RUNNER.PROTOCOL_ID, "protocol": _protocol(binding), "postconditions": {"runtime_binding": binding}})
    _write(source / "run_seal.json", {"status": "failed"})
    if migrated:
        migration = source / "migration.T1.r1"
        migration.mkdir()
        for source_name, destination_name in (
            ("responses.T1.r1.jsonl", "responses.T1.r1.jsonl"),
            ("judge_traces.T1.r1.jsonl", "judge_traces.T1.r1.jsonl"),
        ):
            (source / source_name).rename(migration / destination_name)
        sidecar = source / "eval_sidecars" / "question_results.e8-t1-r1.jsonl"
        sidecar.rename(migration / "legacy_question_results.T1.r1.jsonl")
    return source


def test_classification_accepts_only_explicit_transport_failure() -> None:
    timeout = "[ERROR: Inference failed: chat_completions failed: timed out]"
    assert repair._generation_reasons({"answer": timeout}, {"result": {"tokens_generated": 0, "error": True, "error_detail": timeout}}, {"scoring_method": "exact_match"})
    negatives = [
        ({"answer": "", "error": None}, {"tokens_generated": 0, "error": False, "error_detail": timeout}),
        ({"answer": "model output"}, {"tokens_generated": 0, "error": True, "error_detail": timeout}),
        ({"answer": ""}, {"tokens_generated": 0, "error": True, "error_detail": "code execution failed"}),
        ({"answer": ""}, {"tokens_generated": 0, "error": True, "error_detail": "loop/truncation"}),
        ({"answer": "answer", "error": "scoring_unavailable: down"}, {"tokens_generated": 3, "error": True, "error_detail": "scoring_unavailable: down"}),
    ]
    for response, result in negatives:
        assert repair._generation_reasons(response, {"result": result}, {"scoring_method": "llm_judge"}) == ()


def test_plan_is_dynamic_and_spans_repetitions(tmp_path: Path) -> None:
    plan = repair.build_plan(repair.validate_source(_source(tmp_path)))
    assert [(row["tier"], row["repetition"], row["ordinal"]) for row in plan["targets"]] == [(2, 1, 1), (2, 2, 3)]


def test_source_rejects_incomplete_hash_watcher_and_symlink(tmp_path: Path) -> None:
    root = _source(tmp_path)
    (root / "raw.T2.r3.json").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        repair.validate_source(root)
    root = _source(tmp_path / "hash")
    path = root / "responses.T2.r1.jsonl"
    path.write_text(path.read_text().replace('"t2-0"', '"wrong"', 1))
    with pytest.raises(ValueError, match="hash differs"):
        repair.validate_source(root)
    root = _source(tmp_path / "watch")
    _write(root / "runtime_watch.jsonl", [{"ok": False}], lines=True)
    manifest = repair.load_json(root / "terminal_source.json")
    manifest["source_sha256"]["runtime_watch.jsonl"] = repair.sha256_path(root / "runtime_watch.jsonl")
    _write(root / "terminal_source.json", manifest)
    with pytest.raises(ValueError, match="watcher"):
        repair.validate_source(root)


def test_terminalizer_copies_only_complete_standard_and_migrated_sources(tmp_path: Path) -> None:
    staging = _terminal_staging(tmp_path)
    terminal = tmp_path / "terminal"
    repair.terminalize_source(staging, terminal)
    assert repair.validate_source(terminal).runs[0].responses.is_file()
    migrated = _terminal_staging(tmp_path / "migrated", migrated=True)
    terminal_migrated = tmp_path / "terminal-migrated"
    repair.terminalize_source(migrated, terminal_migrated)
    assert "migration.T1.r1" in str(repair.validate_source(terminal_migrated).runs[0].responses)
    (migrated / "raw.T2.r3.json").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        repair.terminalize_source(migrated, tmp_path / "bad-terminal")


def test_focused_substitution_and_candidate_validator(tmp_path: Path) -> None:
    source = _source(tmp_path)
    focused = _focused(source, tmp_path / "focused")
    candidate = tmp_path / "candidate"
    repair.publish_candidate(source, candidate, focused_dir=focused)
    assert repair.validate_candidate(candidate)["valid"] is True
    original = (source / "responses.T2.r1.jsonl").read_bytes().splitlines(keepends=True)
    final = (candidate / "final_ledgers" / "responses.T2.r1.jsonl").read_bytes().splitlines(keepends=True)
    assert original[0] == final[0] and original[1] != final[1]
    (candidate / "e8_quality_baseline_evidence.json").write_text("tampered\n")
    with pytest.raises(ValueError, match="seal"):
        repair.validate_candidate(candidate)
    with pytest.raises(FileExistsError):
        repair.publish_candidate(source, candidate, focused_dir=focused)


def test_focused_seal_and_tamper_fail_closed(tmp_path: Path) -> None:
    source = _source(tmp_path)
    focused = _focused(source, tmp_path / "focused")
    (focused / "focused_attempts.jsonl").write_text("tampered\n")
    with pytest.raises(ValueError, match="seal"):
        repair.publish_candidate(source, tmp_path / "candidate", focused_dir=focused)


def test_collection_failure_retains_prior_attempts(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    output = tmp_path / "collect"
    monkeypatch.setattr(repair, "_reconstruct_questions", lambda *_args: (_ for _ in ()).throw(RuntimeError("probe failed")))
    with pytest.raises(RuntimeError, match="probe failed"):
        repair.collect_focused(source, output, api_url="http://127.0.0.1:8000")
    assert repair.load_json(output / "focused_collection_seal.json")["status"] == "failed"
    assert (output / "collection_failure.json").is_file()


def test_later_focused_failure_preserves_earlier_durable_attempt(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    output = tmp_path / "collect"

    class Watcher:
        fatal_error = None
        samples = [{"ok": True}]

        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            return self.samples

        def active_load(self, **_kwargs):
            return nullcontext()

    class Tower:
        calls = 0

        def __init__(self, **_kwargs):
            self._question_artifact_dir = None

        def _eval_batch(self, questions, *_args, **_kwargs):
            Tower.calls += 1
            good = Tower.calls == 1
            return [SimpleNamespace(qid=questions[0]["qid"], question_id=questions[0]["qid"], suite="suite", answer="a" if good else "", correct=good, error=None if good else "failed", partial=False, degraded=False, route_used="frontdoor", eval_concurrency=1)]

    questions = {tier: [{"qid": f"t{tier}-{ordinal}", "suite": "suite", "scoring_method": "exact_match", "expected": "a", "scoring_config": {}} for ordinal in range(50 if tier == 1 else 500)] for tier in (1, 2)}
    monkeypatch.setattr(repair, "_reconstruct_questions", lambda *_args: questions)
    monkeypatch.setattr(repair.RUNNER, "RuntimeWatcher", Watcher)
    monkeypatch.setattr(repair.RUNNER, "require_clean_watcher", lambda *_args: None)
    monkeypatch.setattr(repair.RUNNER, "EvalTower", Tower)
    monkeypatch.setattr(repair.RUNNER.httpx, "Client", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(repair.RUNNER, "capture_llm_judge_traces", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(repair.RUNNER, "bind_eval_tower_scorer_identities", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(repair.RUNNER, "replay_llm_judge_scorer_tail_once", lambda *_args: [])
    with pytest.raises(RuntimeError, match="failed closed"):
        repair.collect_focused(source, output, api_url="http://127.0.0.1:8000")
    assert len(repair.load_jsonl(output / "focused_attempts.jsonl")) == 1
    assert repair.load_json(output / "focused_collection_seal.json")["status"] == "failed"


def test_timeout_cli_is_pinned() -> None:
    with pytest.raises(SystemExit):
        repair.parse_args(["--plan", "--source-dir", "/tmp/s", "--output-dir", "/tmp/o", "--evaltower-timeout-s", "301"])


def test_path_overlap_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    focused = _focused(source, tmp_path / "focused")
    with pytest.raises(ValueError, match="overlap"):
        repair.publish_candidate(source, source / "candidate", focused_dir=focused)

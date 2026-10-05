"""Regression coverage for the E8 v5 replay-first partial-resume contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from contextlib import contextmanager

import fcntl

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts/benchmark/resume_e8_quality_baseline_v5.py"
spec = importlib.util.spec_from_file_location("e8_v5_partial_resume_test", MODULE_PATH)
assert spec is not None and spec.loader is not None
resume = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = resume
spec.loader.exec_module(resume)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, sort_keys=True) + "\n")


@contextmanager
def _held_flocks(*paths: Path):
    handles = []
    try:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(path, "a+b")
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handles.append(handle)
        yield
    finally:
        for handle in reversed(handles):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


def _response(qid: str, *, error: str | None = None) -> dict:
    return {
        "qid": qid,
        "suite": "suite",
        "scoring_method": "llm_judge" if qid.endswith("98") else "exact_match",
        "answer": error or "answer",
        "correct": error is None,
        "error": error,
        "partial": False,
        "degraded": False,
        "route_used": "frontdoor",
        "scoring_config_sha256": "0" * 64,
    }


def _source(tmp_path: Path) -> Path:
    root = tmp_path / "failed-staging"
    for tier, n in ((1, 50), (2, 500)):
        questions = [
            {
                "qid": f"t{tier}-{ordinal}",
                "suite": "suite",
                "scoring_method": "exact_match",
                "expected": "a",
                "scoring_config": {},
            }
            for ordinal in range(n)
        ]
        if tier == 2:
            questions[98]["qid"] = "physreason_cal_problem_00351_sq2"
            questions[98]["scoring_method"] = "llm_judge"
            questions[99]["qid"] = "aime_2024-I-12"
        vector = {"tier": tier, "n": n, "questions": [{"qid": q["qid"]} for q in questions]}
        scoring = {"tier": tier, "n": n, "questions": questions}
        _write(root / f"question_vector.T{tier}.json", vector)
        _write(root / f"scoring_vector.T{tier}.json", scoring)
        for repetition in (1, 2, 3) if tier == 1 else (1,):
            rows = [_response(q["qid"]) for q in questions]
            sidecars = []
            for ordinal, q in enumerate(questions):
                error = None
                if tier == 2 and repetition == 1 and ordinal in (98, 99):
                    error = "[ERROR: Inference failed: chat_completions failed: timed out]"
                    rows[ordinal] = _response(q["qid"], error=error)
                sidecars.append(
                    {
                        "row_type": "question_result",
                        "ordinal": ordinal,
                        "answer": error or "answer",
                        "result": {
                            "qid": q["qid"],
                            "question_id": q["qid"],
                            "tokens_generated": 0 if error else 1,
                            "error": bool(error),
                            "error_detail": error,
                            "route": "frontdoor",
                            "correct": not bool(error),
                            **(
                                {"partial": False, "degraded": False}
                                if error
                                else {}
                            ),
                        },
                    }
                )
            _write(root / f"raw.T{tier}.r{repetition}.json", {"n": n})
            (root / f"responses.T{tier}.r{repetition}.jsonl").parent.mkdir(
                parents=True, exist_ok=True
            )
            (root / f"responses.T{tier}.r{repetition}.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows)
            )
            (
                root / "eval_sidecars" / f"question_results.e8-t{tier}-r{repetition}.jsonl"
            ).parent.mkdir(parents=True, exist_ok=True)
            (
                root / "eval_sidecars" / f"question_results.e8-t{tier}-r{repetition}.jsonl"
            ).write_text("".join(json.dumps(row) + "\n" for row in sidecars))
            (root / f"judge_traces.T{tier}.r{repetition}.jsonl").write_text("")
    (root / "runtime_watch.jsonl").write_text(json.dumps({"ok": True}) + "\n")
    return root


def test_plan_allows_exactly_two_generation_targets_and_no_banked_regeneration(
    tmp_path: Path,
) -> None:
    plan = resume.build_plan(_source(tmp_path))
    assert [(row["ordinal"], row["qid"]) for row in plan["generation_tail"]["targets"]] == [
        (98, "physreason_cal_problem_00351_sq2"),
        (99, "aime_2024-I-12"),
    ]
    assert plan["replay_only"] == {"tiers": [1], "banked_t2_r1_vector": True}
    assert plan["fresh_collection"] == [{"tier": 2, "repetition": 2}, {"tier": 2, "repetition": 3}]


def test_plan_rejects_any_extra_or_missing_target(tmp_path: Path) -> None:
    root = _source(tmp_path)
    rows = [json.loads(line) for line in (root / "responses.T2.r1.jsonl").read_text().splitlines()]
    rows[100] = _response(
        rows[100]["qid"], error="[ERROR: Inference failed: chat_completions failed: timed out]"
    )
    (root / "responses.T2.r1.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    sidecar = root / "eval_sidecars/question_results.e8-t2-r1.jsonl"
    sidecars = [json.loads(line) for line in sidecar.read_text().splitlines()]
    sidecars[100]["answer"] = rows[100]["answer"]
    sidecars[100]["result"].update(
        {
            "tokens_generated": 0,
            "error": True,
            "error_detail": rows[100]["error"],
            "partial": False,
            "degraded": False,
        }
    )
    sidecar.write_text("".join(json.dumps(row) + "\n" for row in sidecars))
    with pytest.raises(ValueError, match="target set differs"):
        resume.build_plan(root)


def test_plan_rejects_unbound_generation_target(tmp_path: Path) -> None:
    root = _source(tmp_path)
    sidecar = root / "eval_sidecars/question_results.e8-t2-r1.jsonl"
    rows = [json.loads(line) for line in sidecar.read_text().splitlines()]
    rows[98]["result"]["question_id"] = "unknown"
    sidecar.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="target set differs"):
        resume.build_plan(root)


def test_generation_inputs_are_reconstructed_not_taken_from_scorer_vector(monkeypatch) -> None:
    full_questions = {
        tier: [
            {
                "id": f"t{tier}-q0",
                "prompt": f"full prompt for tier {tier}",
                "suite": "suite",
                "scoring_method": "exact_match",
                "expected": "answer",
                "scoring_config": {},
            }
        ]
        for tier in (1, 2)
    }
    vectors = {
        tier: resume.V4.public_vector(
            full_questions[tier], tier=tier, core_id="sealed-t1", seed=17
        )
        for tier in (1, 2)
    }
    scoring = {
        tier: resume.V4.scoring_vector(
            full_questions[tier], tier=tier, core_id="sealed-t1", seed=17
        )
        for tier in (1, 2)
    }
    # Sealed scoring vectors intentionally omit both the prompt and EvalTower's
    # `id`/`question_id` identity.  They are valid for scoring but not generation.
    assert "prompt" not in scoring[2]["questions"][0]
    assert "id" not in scoring[2]["questions"][0]

    seen: list[tuple[int, str]] = []

    def fake_question_vector(_tower, *, tier, t1_core_id, n, seed):
        seen.append((tier, t1_core_id))
        assert n == 1
        assert seed == 17
        return [dict(question) for question in full_questions[tier]], "sealed-t1"

    monkeypatch.setattr(resume.V4, "question_vector", fake_question_vector)
    monkeypatch.setattr(
        resume.V4,
        "apply_context_replacement_map",
        lambda _args, questions, *, tier: questions,
    )
    rebuilt = resume._reconstruct_generation_questions(
        object(), SimpleNamespace(), vectors, scoring
    )
    assert seen == [(1, "sealed-t1"), (2, "sealed-t1")]
    assert rebuilt[2][0]["prompt"] == "full prompt for tier 2"
    assert rebuilt[2][0]["id"] == "t2-q0"


def test_generation_reconstruction_rejects_prompt_drift(monkeypatch) -> None:
    questions = {
        tier: [
            {
                "id": f"t{tier}-q0",
                "prompt": f"sealed prompt {tier}",
                "suite": "suite",
                "scoring_method": "exact_match",
                "expected": "answer",
                "scoring_config": {},
            }
        ]
        for tier in (1, 2)
    }
    vectors = {
        tier: resume.V4.public_vector(questions[tier], tier=tier, core_id="sealed-t1", seed=17)
        for tier in (1, 2)
    }
    scoring = {
        tier: resume.V4.scoring_vector(questions[tier], tier=tier, core_id="sealed-t1", seed=17)
        for tier in (1, 2)
    }

    def fake_question_vector(_tower, *, tier, **_kwargs):
        rows = [dict(question) for question in questions[tier]]
        if tier == 2:
            rows[0]["prompt"] = "drifted prompt"
        return rows, "sealed-t1"

    monkeypatch.setattr(resume.V4, "question_vector", fake_question_vector)
    monkeypatch.setattr(
        resume.V4,
        "apply_context_replacement_map",
        lambda _args, rows, *, tier: rows,
    )
    with pytest.raises(ValueError, match="question vector differs"):
        resume._reconstruct_generation_questions(object(), SimpleNamespace(), vectors, scoring)


def test_immutable_copy_hashes_every_source_file_and_never_edits_source(tmp_path: Path) -> None:
    source = _source(tmp_path)
    before = {
        path.relative_to(source): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*")
        if path.is_file()
    }
    plan = resume.build_plan(source)
    destination = tmp_path / "copy"
    resume.copy_source_immutable(source, destination, plan)
    assert {
        path.relative_to(source): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*")
        if path.is_file()
    } == before
    binding = json.loads((destination / "source_binding.json").read_text())
    assert binding["source_sha256"] == plan["source_sha256"]
    with pytest.raises(FileExistsError):
        resume.copy_source_immutable(source, destination, plan)


def test_partial_resume_context_binds_exact_source_plan_and_runner(tmp_path: Path) -> None:
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    spec = importlib.util.spec_from_file_location("e8_v5_partial_context_validator", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    source = _source(tmp_path)
    plan = resume.build_plan(source)
    evidence_root = tmp_path / "candidate"
    evidence_root.mkdir()
    snapshot = evidence_root / "source_snapshot"
    resume.copy_source_immutable(source, snapshot, plan)
    plan_path = evidence_root / "partial_resume_plan.json"
    _write(plan_path, plan)
    resume_sha = hashlib.sha256(resume.RUNNER_PATH.read_bytes()).hexdigest()
    report = {
        "partial_resume": {
            "schema": "epyc.e8_quality_v5_partial_resume.v2",
            "source_binding": str(snapshot / "source_binding.json"),
            "source_tree_sha256": plan["source_tree_sha256"],
            "plan_path": str(plan_path),
            "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "resume_runner": {"path": str(resume.RUNNER_PATH), "sha256": resume_sha},
            "t2_r1_generation_tail_ordinals": [98, 99],
            "t2_r1_scorer_recovery_ordinals": list(range(15)),
        }
    }
    context = validator.validate_partial_resume_context(
        report,
        evidence_root=evidence_root,
        expected_resume_runner_sha256=resume_sha,
    )
    assert context is not None
    assert context["plan"] == plan
    for tier in (1, 2):
        for kind in ("question", "scoring"):
            name = f"{kind}_vector.T{tier}.json"
            (evidence_root / name).write_bytes((snapshot / name).read_bytes())
    t1_details = []
    for repetition in (1, 2, 3):
        name = f"raw.T1.r{repetition}.json"
        (evidence_root / name).write_bytes((snapshot / name).read_bytes())
        t1_details.append({"repetition": repetition})
    validator.validate_partial_resume_source_links(
        context,
        evidence_root=evidence_root,
        vectors={
            tier: json.loads((evidence_root / f"question_vector.T{tier}.json").read_text())
            for tier in (1, 2)
        },
        scoring={
            tier: json.loads((evidence_root / f"scoring_vector.T{tier}.json").read_text())
            for tier in (1, 2)
        },
        details={"1": t1_details, "2": []},
    )
    (evidence_root / "raw.T1.r2.json").write_text("tampered\n")
    with pytest.raises(ValueError, match="banked T1 raw"):
        validator.validate_partial_resume_source_links(
            context,
            evidence_root=evidence_root,
            vectors={
                tier: json.loads((evidence_root / f"question_vector.T{tier}.json").read_text())
                for tier in (1, 2)
            },
            scoring={
                tier: json.loads((evidence_root / f"scoring_vector.T{tier}.json").read_text())
                for tier in (1, 2)
            },
            details={"1": t1_details, "2": []},
        )
    (snapshot / "responses.T1.r1.jsonl").write_text("tampered\n")
    with pytest.raises(ValueError, match="immutable source snapshot"):
        validator.validate_partial_resume_context(
            report,
            evidence_root=evidence_root,
            expected_resume_runner_sha256=resume_sha,
        )


def test_active_segment_rejects_gap_without_an_active_load_sample() -> None:
    class Watcher:
        samples: list[dict] = []

    with pytest.raises(ValueError, match="active-load segment"):
        resume._segment_check([{"ok": True, "active_load": None}], {"tier": 2, "repetition": 1})
    resume._segment_check(
        [{"ok": True, "active_load": {"tier": 2, "repetition": 1}}], {"tier": 2, "repetition": 1}
    )


def test_held_region_claim_uses_role_region_lock_shape(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    claims.mkdir()
    payload = {
        "request_tag": "e8-resume",
        "role": "bench-gpu",
        "region": "q3",
        "pid": os.getpid(),
    }
    path, global_path = (
        claims / "cpu_region.bench-gpu.q3.lock",
        claims / "cpu_region.GLOBAL.q3.lock",
    )
    _write(path, payload)
    global_path.parent.mkdir(parents=True, exist_ok=True)
    global_path.touch()
    with _held_flocks(path, global_path):
        claim = resume._capture_held_region_claim(
            SimpleNamespace(
                region_claim_tag="e8-resume",
                region_claim_regions="q3",
                region_claim_dir=claims,
            )
        )
    assert claim["claim_dir"] == str(claims.resolve())
    assert claim["claims"] == [{"path": str(path), "payload": payload}]
    assert claim["global_claims"] == [
        {"path": str(global_path), "region": "q3", "holder_pids": [os.getpid()]}
    ]


def test_held_region_claim_rejects_stale_live_ancestor_payload(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    payload = {"request_tag": "e8-resume", "role": "bench-cpu", "region": "q2", "pid": os.getpid()}
    _write(claims / "cpu_region.bench-cpu.q2.lock", payload)
    (claims / "cpu_region.GLOBAL.q2.lock").touch()
    with pytest.raises(ValueError, match="role lock is not flock-held"):
        resume._capture_held_region_claim(
            SimpleNamespace(region_claim_tag="e8-resume", region_claim_regions="q2", region_claim_dir=claims)
        )


def test_held_region_claim_rejects_missing_global_flock(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    payload = {"request_tag": "e8-resume", "role": "bench-cpu", "region": "q2", "pid": os.getpid()}
    role_path, global_path = claims / "cpu_region.bench-cpu.q2.lock", claims / "cpu_region.GLOBAL.q2.lock"
    _write(role_path, payload)
    global_path.touch()
    with _held_flocks(role_path), pytest.raises(ValueError, match="GLOBAL lock"):
        resume._capture_held_region_claim(
            SimpleNamespace(region_claim_tag="e8-resume", region_claim_regions="q2", region_claim_dir=claims)
        )


def test_held_region_claim_rejects_duplicate_requested_regions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repeats a requested region"):
        resume._capture_held_region_claim(
            SimpleNamespace(region_claim_tag="e8-resume", region_claim_regions="q2,q2", region_claim_dir=tmp_path)
        )


def test_held_region_claim_rejects_duplicate_role_claims_for_one_region(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    payloads = [
        {"request_tag": "e8-resume", "role": role, "region": "q2", "pid": os.getpid()}
        for role in ("bench-a", "bench-b")
    ]
    role_paths = [claims / f"cpu_region.{payload['role']}.q2.lock" for payload in payloads]
    global_path = claims / "cpu_region.GLOBAL.q2.lock"
    for path, payload in zip(role_paths, payloads):
        _write(path, payload)
    global_path.touch()
    with _held_flocks(*role_paths, global_path), pytest.raises(ValueError, match="claim differs"):
        resume._capture_held_region_claim(
            SimpleNamespace(region_claim_tag="e8-resume", region_claim_regions="q2", region_claim_dir=claims)
        )


def test_sealed_held_claim_rejects_duplicate_global_identities() -> None:
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    spec = importlib.util.spec_from_file_location("e8_v5_claim_shape_validator", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    claim = {
        "regions": ["q2", "q3"],
        "global_claims": [
            {"path": "/tmp/cpu_region.GLOBAL.q2.lock", "region": "q2"},
            {"path": "/tmp/cpu_region.GLOBAL.q3.lock", "region": "q3"},
        ],
    }
    validator.validate_held_region_claim_uniqueness(claim)
    with pytest.raises(ValueError, match="repeats a region"):
        validator.validate_held_region_claim_uniqueness({**claim, "regions": ["q2", "q2"]})
    with pytest.raises(ValueError, match="GLOBAL claim cardinality"):
        validator.validate_held_region_claim_uniqueness(
            {
                **claim,
                "global_claims": [
                    {"path": "/tmp/cpu_region.GLOBAL.q2.lock", "region": "q2"},
                    {"path": "/tmp/cpu_region.GLOBAL.q2.lock", "region": "q3"},
                ],
            }
        )


def test_scorer_history_is_limited_to_one_replay(tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    row = {
        "schema": "epyc.e8_quality_llm_judge_trace.v2",
        "fixed_vector_row": {"tier": 2, "repetition": 1, "ordinal": 6, "qid": "q6"},
        "attempts": [
            {"error": {"type": "ScoringUnavailableError"}},
            {"error": None},
        ],
    }
    trace.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="exactly 15"):
        resume._scorer_recovery_rows(trace, tier=2, repetition=1)
    row["attempts"].append({"error": None})
    trace.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="one deterministic retry"):
        resume._scorer_recovery_rows(trace, tier=2, repetition=1)


def test_normalized_t2_trace_is_reconstructed_and_scorer_binding_is_derived(tmp_path: Path) -> None:
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    spec = importlib.util.spec_from_file_location("e8_v5_normalized_trace_validator", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    source = _source(tmp_path)
    normalized = tmp_path / "normalized.jsonl"
    normalized.write_bytes((source / "judge_traces.T2.r1.jsonl").read_bytes())
    responses = resume.V4.load_jsonl(source / "responses.T2.r1.jsonl")
    responses[98]["answer"] = ""
    original_utc_now = resume.V4.utc_now
    try:
        resume.V4.utc_now = lambda: "2026-07-28T00:00:00Z"
        resume.V4.seal_judge_trace_outcomes(
            normalized,
            responses,
            resume._questions(source, 2),
            tier=2,
            repetition=1,
            default_api_url="http://127.0.0.1:8000",
        )
    finally:
        resume.V4.utc_now = original_utc_now
    validator_runner = validator.load_runner()
    reconstructed = validator.reconstruct_partial_t2r1_normalized_trace(
        pristine_trace_path=source / "judge_traces.T2.r1.jsonl",
        normalized_trace_path=normalized,
        pristine_response_path=source / "responses.T2.r1.jsonl",
        pristine_sidecar_path=source / "eval_sidecars/question_results.e8-t2-r1.jsonl",
        questions=resume._questions(source, 2),
        runner=validator_runner,
    )
    assert reconstructed == normalized.read_bytes()
    normalized_rows = [json.loads(line) for line in normalized.read_text().splitlines()]
    normalized_rows[0]["mode"] = "tampered"
    normalized.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in normalized_rows))
    with pytest.raises(ValueError, match="blank trace differs"):
        validator.reconstruct_partial_t2r1_normalized_trace(
            pristine_trace_path=source / "judge_traces.T2.r1.jsonl",
            normalized_trace_path=normalized,
            pristine_response_path=source / "responses.T2.r1.jsonl",
            pristine_sidecar_path=source / "eval_sidecars/question_results.e8-t2-r1.jsonl",
            questions=resume._questions(source, 2),
            runner=validator_runner,
        )
    with pytest.raises(ValueError, match="scorer-recovery ordinals"):
        validator.validate_partial_scorer_recovery_binding(
            {"t2_r1_scorer_recovery_ordinals": [2, 7]}, {2: "q2", 8: "q8"}
        )


def test_atomic_publication_never_replaces_existing_destination(tmp_path: Path) -> None:
    staging, destination = tmp_path / "staging", tmp_path / "published"
    staging.mkdir()
    (staging / "evidence").write_text("candidate\n")
    destination.mkdir()
    (destination / "existing").write_text("immutable\n")
    with pytest.raises(FileExistsError):
        resume.V4.atomic_publish_noreplace(staging, destination)
    assert (destination / "existing").read_text() == "immutable\n"


def test_resume_fault_after_staging_creation_is_terminally_sealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "candidate"
    monkeypatch.setattr(resume, "build_plan", lambda _source: {"sealed": True})
    monkeypatch.setattr(resume.V5, "parse_args", lambda _argv: SimpleNamespace())
    monkeypatch.setattr(resume.V5, "protocol_proposal", lambda _args: {})
    monkeypatch.setattr(
        resume.V4,
        "prepare_report",
        lambda _args, **_kwargs: {"blockers": []},
    )
    monkeypatch.setattr(
        resume,
        "write_json_create",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("injected staging fault")),
    )

    with pytest.raises(RuntimeError, match="injected staging fault"):
        resume.execute(
            SimpleNamespace(
                source_dir=source,
                output_dir=output,
                api_url="http://test",
            )
        )

    staging = next(tmp_path.glob(".candidate.staging-*"))
    assert resume.V4.load_json(staging / "run_seal.json")["status"] == (
        "terminal_aborted_no_admission"
    )
    assert resume.V4.load_json(staging / "writer_abort.json")["no_admission"] is True


def test_segmented_monitor_requires_gap_free_clean_claimed_segments() -> None:
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    spec = importlib.util.spec_from_file_location("e8_v5_segmented_validator", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    samples = [
        {"started_at": "2026-07-28T00:00:00Z", "ok": True},
        {"started_at": "2026-07-28T00:00:05Z", "ok": True},
        {"started_at": "2026-07-28T04:00:00Z", "ok": True},
        {"started_at": "2026-07-28T04:00:05Z", "ok": True},
    ]
    segments = [
        {"source": "historical", "binding_sha256": "a" * 64, "sample_indexes": [0, 1]},
        {"source": "resume", "binding_sha256": "b" * 64, "sample_indexes": [2, 3]},
    ]
    validator.validate_segmented_monitor(samples, segments)
    with pytest.raises(ValueError, match="contiguous"):
        validator.validate_segmented_monitor(
            samples,
            [
                {"source": "historical", "binding_sha256": "a" * 64, "sample_indexes": [0, 2]},
                {"source": "resume", "binding_sha256": "b" * 64, "sample_indexes": [1, 3]},
            ],
        )
    with pytest.raises(ValueError, match="unclaimed"):
        validator.validate_segmented_monitor(samples, segments[:1])
    reversed_samples = [samples[1], samples[0], samples[2], samples[3]]
    with pytest.raises(ValueError, match="sampling gap"):
        validator.validate_segmented_monitor(reversed_samples, segments)


def test_historical_jitter_amendment_is_exact_source_bound(tmp_path: Path, monkeypatch) -> None:
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    spec = importlib.util.spec_from_file_location("e8_v5_jitter_validator", validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    historical = [
        {
            "started_at": "2026-07-28T00:00:00Z",
            "ok": True,
            "active_load": {"tier": 1, "repetition": 1},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 1}},
        },
        {
            "started_at": "2026-07-28T00:00:07.200000Z",
            "ok": True,
            "active_load": {"tier": 1, "repetition": 2},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 1}},
        },
        {
            "started_at": "2026-07-28T00:00:12.200000Z",
            "ok": True,
            "active_load": {"tier": 1, "repetition": 3},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 1}},
        },
        {
            "started_at": "2026-07-28T00:00:17.200000Z",
            "ok": True,
            "active_load": {"tier": 2, "repetition": 1},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 1}},
        },
    ]
    resumed = [
        {
            "started_at": "2026-07-28T01:00:00Z",
            "ok": True,
            "active_load": {"tier": 2, "repetition": 1},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 2}},
        },
        {
            "started_at": "2026-07-28T01:00:05Z",
            "ok": True,
            "active_load": {"tier": 2, "repetition": 2},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 2}},
        },
        {
            "started_at": "2026-07-28T01:00:06Z",
            "ok": True,
            "active_load": {"tier": 2, "repetition": 3},
            "api_probe_urls": {"frontdoor": "http://localhost:8070"},
            "runtime_artifacts": {"server": {"st_ino": 2}},
        },
    ]
    historical_path, resume_path = tmp_path / "historical.jsonl", tmp_path / "resume.jsonl"
    historical_path.write_text("".join(json.dumps(row) + "\n" for row in historical))
    resume_path.write_text("".join(json.dumps(row) + "\n" for row in resumed))
    historical_sha = validator.sha256_path(historical_path)
    historical_binding = validator._monitor_binding_sha256(historical[0])
    monkeypatch.setattr(validator, "HISTORICAL_WATCHER_SHA256", historical_sha)
    monkeypatch.setattr(validator, "HISTORICAL_BINDING_SHA256", historical_binding)
    monkeypatch.setattr(validator, "HISTORICAL_EXPECTED_GAP_COUNT", 1)
    monkeypatch.setattr(validator, "HISTORICAL_EXPECTED_MAX_GAP_S", 7.2)
    monkeypatch.setattr(validator, "HISTORICAL_MAX_GAP_S", 7.25)
    segments = [
        {
            "source": "historical",
            "binding_sha256": historical_binding,
            "source_path": str(historical_path),
            "source_sha256": historical_sha,
            "sample_indexes": [0, 1, 2, 3],
            "max_gap_s": 7.25,
            "observed_gap_count_over_7s": 1,
            "observed_max_gap_s": 7.2,
        },
        {
            "source": "resume",
            "binding_sha256": validator._monitor_binding_sha256(resumed[0]),
            "source_path": str(resume_path),
            "source_sha256": validator.sha256_path(resume_path),
            "sample_indexes": [4, 5, 6],
            "max_gap_s": 7.0,
            "observed_gap_count_over_7s": 0,
            "observed_max_gap_s": 5.0,
        },
    ]
    validator.validate_segmented_monitor([*historical, *resumed], segments, evidence_root=tmp_path)
    segments[0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source hash"):
        validator.validate_segmented_monitor([*historical, *resumed], segments, evidence_root=tmp_path)

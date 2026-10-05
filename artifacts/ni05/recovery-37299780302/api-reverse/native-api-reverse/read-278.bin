"""Guards for copy-only final-C1 deterministic completion."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATH = (
    ROOT
    / "scripts/benchmark/complete_e8_quality_baseline_v5_final_c1.py"
)
SPEC = importlib.util.spec_from_file_location("e8_final_c1_completion_test", PATH)
assert SPEC and SPEC.loader
COMPLETION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPLETION)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _question(ordinal: int) -> dict:
    return {
        "qid": f"q{ordinal}",
        "suite": "unit",
        "scoring_method": "exact_match",
        "scoring_config": {},
        "expected": f"answer-{ordinal}",
    }


def _response(ordinal: int) -> dict:
    return {
        "qid": f"q{ordinal}",
        "suite": "unit",
        "scoring_method": "exact_match",
        "answer": f"answer-{ordinal}",
        "correct": True,
        "error": None,
        "partial": False,
        "degraded": False,
        "route_used": "frontdoor",
        "scoring_config_sha256": COMPLETION.canonical_hash({}),
    }


def _sidecar(ordinal: int, *, scorer_error: bool = False) -> dict:
    answer = f"answer-{ordinal}"
    result = {
        "qid": f"q{ordinal}",
        "question_id": f"q{ordinal}",
        "suite": "unit",
        "tokens_generated": 1,
        "correct": not scorer_error,
        "route": "frontdoor",
        "answer_hash": COMPLETION.V5._normalized_answer_hash(answer),
    }
    if scorer_error:
        result.update(
            {
                "error": True,
                "error_detail": "scoring unavailable",
            }
        )
    return {
        "row_type": "question_result",
        "ordinal": ordinal,
        "answer": answer,
        "result": result,
    }


def _typed_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict]:
    source = tmp_path / "aborted"
    race = source / "predecessor_snapshot"
    successor = race / "predecessor_snapshot"
    monkeypatch.setattr(COMPLETION.RECOVERY, "N", 7)
    monkeypatch.setattr(COMPLETION.FINAL_C1, "RETRY_ORDINALS", (0, 5))
    monkeypatch.setattr(
        COMPLETION.FINAL_C1, "RACE_RETRY_ORDINALS", (0, 3, 5)
    )
    _write_json(
        race / "partial_r2_plan.json",
        {
            "schema": COMPLETION.RACE.LEGACY_PLAN_SCHEMA,
            "race_retry_ordinals": [0, 3, 5],
            "predecessor_generation_import_ordinals": [6],
        },
    )
    _write_json(
        successor / "partial_r2_plan.json",
        {
            "schema": COMPLETION.RACE.SUCCESSOR.PLAN_SCHEMA,
            "reuse_ordinals": [1],
            "inherited_scorer_replay_ordinals": [],
            "imported_generation_ordinals": [2],
            "scorer_replay_ordinals": [4],
            "generation_ordinals": [0, 3, 5, 6],
        },
    )
    paths = {
        "current": source
        / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl",
        "race": race
        / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl",
        "successor": successor
        / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl",
        "imported": successor
        / "failed_source_snapshot/eval_sidecars/"
        "question_results.e8-t2-r2-recovery.jsonl",
        "saved": successor
        / "source_snapshot/eval_sidecars/question_results.e8-t2-r2.jsonl",
    }
    _write_jsonl(paths["current"], [_sidecar(0), _sidecar(5)])
    _write_jsonl(paths["race"], [_sidecar(0), _sidecar(3), _sidecar(5)])
    _write_jsonl(
        paths["successor"],
        [_sidecar(0), _sidecar(3), _sidecar(5), _sidecar(6)],
    )
    _write_jsonl(
        paths["imported"],
        [_sidecar(2), _sidecar(4, scorer_error=True)],
    )
    _write_jsonl(paths["saved"], [_sidecar(1)])
    scorer_sidecar = _sidecar(4, scorer_error=True)
    attempt = {
        "schema": COMPLETION.RECOVERY.SCORER_ATTEMPT_SCHEMA,
        "ordinal": 4,
        "qid": "q4",
        "saved_sidecar_sha256": COMPLETION.canonical_hash(scorer_sidecar),
        "scoring_question_sha256": COMPLETION.canonical_hash(_question(4)),
    }
    _write_jsonl(
        source / "scorer_attempts.T2.r2.jsonl",
        [{**attempt, "state": "started"}, {**attempt, "state": "succeeded"}],
    )
    answer = "answer-4"
    _write_jsonl(
        source / "scorer_replay_traces.T2.r2.jsonl",
        [
            {
                "schema": "epyc.e8_quality_llm_judge_trace.v1",
                "fixed_vector_qid": "q4",
                "correlation_sha256": COMPLETION.V4.judge_correlation_sha256(
                    answer, answer, {}
                ),
                "scorer_answer": COMPLETION.V4._normalized_scorer_answer(answer),
                "expected": answer,
                "scoring_config": {},
                "candidate": answer,
                "judge_prompt": None,
                "judge_role": None,
                "mode": "substring_fast_path",
                "request": None,
                "response": None,
                "http_error": None,
                "parsed_verdict": True,
                "error": None,
                "source_sha256": {
                    "debug_scorer": COMPLETION.sha256_path(
                        COMPLETION.V4.DEBUG_SCORER_SOURCE
                    ),
                    "seeding_scoring": COMPLETION.sha256_path(
                        COMPLETION.V4.SCORING_SOURCE
                    ),
                },
            }
        ],
    )
    sources = {
        0: "generation",
        1: "reuse",
        2: "imported_generation",
        3: "predecessor_race_retry",
        4: "scorer_replay",
        5: "generation",
        6: "predecessor_generation",
    }
    journal = {
        ordinal: {
            "ordinal": ordinal,
            "source": sources[ordinal],
            "response": _response(ordinal),
        }
        for ordinal in range(7)
    }
    _write_jsonl(
        source / "recovery_rows.T2.r2.jsonl",
        [journal[ordinal] for ordinal in range(7)],
    )
    hashes = COMPLETION.source_hashes(source)
    state = {
        "hashes": hashes,
        "tree_sha256": COMPLETION.canonical_hash(hashes),
        "journal": journal,
        "questions": [_question(ordinal) for ordinal in range(7)],
    }
    return source, state


def test_manifest_resolves_every_typed_lineage_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, state = _typed_lineage(tmp_path, monkeypatch)

    manifest, selected = COMPLETION.build_provenance_manifest(source, state)

    assert set(selected) == set(range(7))
    assert [row["surface"] for row in manifest["entries"]] == [
        "current_generation",
        "saved_r2",
        "imported_generation",
        "race_generation",
        "imported_generation",
        "current_generation",
        "successor_generation",
    ]
    assert manifest["entries"][4]["journal_source"] == "scorer_replay"
    assert manifest["entries"][4]["scorer_replay"] == {
        "class": "successor_scorer_replay",
        "attempts_path": "scorer_attempts.T2.r2.jsonl",
        "attempts_file_sha256": state["hashes"][
            "scorer_attempts.T2.r2.jsonl"
        ],
        "attempt_records_sha256": COMPLETION.canonical_hash(
            COMPLETION.V4.load_jsonl(
                source / "scorer_attempts.T2.r2.jsonl"
            )
        ),
        "saved_sidecar_sha256": COMPLETION.canonical_hash(
            _sidecar(4, scorer_error=True)
        ),
        "scoring_question_sha256": COMPLETION.canonical_hash(_question(4)),
        "trace_path": "scorer_replay_traces.T2.r2.jsonl",
        "trace_file_sha256": state["hashes"][
            "scorer_replay_traces.T2.r2.jsonl"
        ],
        "trace_row_sha256": COMPLETION.canonical_hash(
            COMPLETION.V4.load_jsonl(
                source / "scorer_replay_traces.T2.r2.jsonl"
            )[0]
        ),
        "trace_correlation_sha256": COMPLETION.V4.load_jsonl(
            source / "scorer_replay_traces.T2.r2.jsonl"
        )[0]["correlation_sha256"],
        "parsed_verdict": True,
    }
    assert manifest["entries_sha256"] == COMPLETION.canonical_hash(
        manifest["entries"]
    )


def test_manifest_rejects_category_mismatch_instead_of_recursive_first_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, state = _typed_lineage(tmp_path, monkeypatch)
    state["journal"][2]["source"] = "reuse"

    with pytest.raises(ValueError, match="source categories differ"):
        COMPLETION.build_provenance_manifest(source, state)


def test_manifest_rejects_typed_sidecar_identity_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, state = _typed_lineage(tmp_path, monkeypatch)
    path = (
        source
        / "predecessor_snapshot/predecessor_snapshot/"
        "failed_source_snapshot/eval_sidecars/"
        "question_results.e8-t2-r2-recovery.jsonl"
    )
    rows = COMPLETION.V4.load_jsonl(path)
    rows[0]["result"]["question_id"] = "unknown"
    _write_jsonl(path, rows)
    state["hashes"] = COMPLETION.source_hashes(source)

    with pytest.raises(ValueError, match="typed sidecar provenance differs"):
        COMPLETION.build_provenance_manifest(source, state)


def test_manifest_rejects_non_succeeded_scorer_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, state = _typed_lineage(tmp_path, monkeypatch)
    attempts = source / "scorer_attempts.T2.r2.jsonl"
    rows = COMPLETION.V4.load_jsonl(attempts)
    rows[1]["state"] = "failed"
    _write_jsonl(attempts, rows)
    state["hashes"] = COMPLETION.source_hashes(source)

    with pytest.raises(ValueError, match="exact succeeded attempt pair"):
        COMPLETION.build_provenance_manifest(source, state)


def test_manifest_rejects_scorer_trace_verdict_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, state = _typed_lineage(tmp_path, monkeypatch)
    traces = source / "scorer_replay_traces.T2.r2.jsonl"
    rows = COMPLETION.V4.load_jsonl(traces)
    rows[0]["parsed_verdict"] = False
    _write_jsonl(traces, rows)
    state["hashes"] = COMPLETION.source_hashes(source)

    with pytest.raises(ValueError, match="fast-path trace is inconsistent"):
        COMPLETION.build_provenance_manifest(source, state)


def test_typed_trace_selection_rejects_stale_scorer_replay_from_generation_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    generation = (
        source
        / "predecessor_snapshot/predecessor_snapshot/"
        "generation_judge_traces.T2.r2.jsonl"
    )
    _write_jsonl(
        generation,
        [
            {"fixed_vector_qid": "q0", "trace": "initial"},
            {"fixed_vector_qid": "q0", "trace": "retry"},
        ],
    )
    _write_jsonl(
        source / "scorer_replay_traces.T2.r2.jsonl",
        [{"fixed_vector_qid": "q0", "trace": "stale-third-replay"}],
    )
    question = {
        "qid": "q0", "scoring_method": "llm_judge",
        "scoring_config": {}, "expected": "expected",
    }
    state = {"questions": [question], "journal": {0: {"response": {
        "qid": "q0", "answer": "answer", "correct": False,
    }}}}
    manifest = {"entries": [{
        "ordinal": 0, "qid": "q0", "journal_source": "predecessor_generation",
        "surface": "successor_generation",
    }]}
    monkeypatch.setattr(
        COMPLETION.V4, "_validate_llm_judge_trace_history",
        lambda *_args, **_kwargs: False,
    )

    rows, selection = COMPLETION._typed_trace_rows(source, state, manifest)

    assert [row["trace"] for row in rows] == ["initial", "retry"]
    assert all(row["trace"] != "stale-third-replay" for row in rows)
    assert selection["rows"][0]["trace_paths"] == [
        "predecessor_snapshot/predecessor_snapshot/generation_judge_traces.T2.r2.jsonl",
        "predecessor_snapshot/predecessor_snapshot/generation_judge_traces.T2.r2.jsonl",
    ]


def test_caught_failure_publishes_abort_and_terminal_run_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    monkeypatch.setattr(
        COMPLETION,
        "_validate_aborted_source",
        lambda *_args: (_ for _ in ()).throw(ValueError("source rejected")),
    )
    monkeypatch.setattr(COMPLETION, "_fsync_tree", lambda _root: None)

    with pytest.raises(ValueError, match="source rejected"):
        COMPLETION.execute(
            SimpleNamespace(
                source_dir=source,
                output_dir=output,
                expected_source_tree_sha256="f" * 64,
            )
        )

    abort = COMPLETION.V4.load_json(
        output / COMPLETION.RECOVERY.ABORT_MARKER_NAME
    )
    seal = COMPLETION.V4.load_json(output / COMPLETION.RUN_SEAL_NAME)
    assert abort["writer"] == "final_c1_deterministic_completion"
    assert abort["no_admission"] is True
    assert seal["schema"] == COMPLETION.TERMINAL_SEAL.RUN_SEAL_SCHEMA
    assert seal["status"] == COMPLETION.TERMINAL_SEAL.TERMINAL_STATUS
    assert seal["no_admission"] is True


def _stub_successful_completion(
    monkeypatch: pytest.MonkeyPatch,
    manifest: dict,
) -> None:
    monkeypatch.setattr(
        COMPLETION,
        "_validate_aborted_source",
        lambda *_args: {},
    )
    monkeypatch.setattr(
        COMPLETION,
        "build_provenance_manifest",
        lambda *_args: (manifest, {}),
    )

    def complete(
        _source: Path,
        staging: Path,
        _state: dict,
        actual_manifest: dict,
        _selected: dict,
    ) -> None:
        COMPLETION._write_json(
            staging / COMPLETION.MANIFEST_NAME,
            actual_manifest,
        )
        (staging / "payload.txt").write_text("complete\n", encoding="utf-8")

    def validate(
        namespace: Path,
        _state: dict,
        actual_manifest: dict,
        *,
        require_run_seal: bool = False,
    ) -> None:
        if require_run_seal:
            COMPLETION._validate_standard_complete_seal(
                namespace, actual_manifest
            )

    monkeypatch.setattr(COMPLETION, "_complete", complete)
    monkeypatch.setattr(COMPLETION, "_validate_completed_staging", validate)
    monkeypatch.setattr(COMPLETION, "_fsync_tree", lambda _root: None)


def test_success_seals_only_the_published_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    manifest = {"schema": COMPLETION.SCHEMA, "entries_sha256": "e" * 64}
    _stub_successful_completion(monkeypatch, manifest)
    monkeypatch.setattr(COMPLETION.V4, "fsync_dir", lambda _path: None)

    result = COMPLETION.execute(
        SimpleNamespace(
            source_dir=source,
            output_dir=output,
            expected_source_tree_sha256="f" * 64,
        )
    )

    assert result == output
    assert {
        str(path.relative_to(output))
        for path in output.rglob("*")
        if path.is_file()
    } == {
        COMPLETION.MANIFEST_NAME,
        COMPLETION.RUN_SEAL_NAME,
        "payload.txt",
    }
    seal = COMPLETION.V4.load_json(output / COMPLETION.RUN_SEAL_NAME)
    assert seal["status"] == COMPLETION.TERMINAL_SEAL.COMPLETE_STATUS
    assert not list(tmp_path.glob(".output.staging-*"))


def test_execute_and_validate_complete_reduced_typed_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, state = _typed_lineage(tmp_path, monkeypatch)
    output = tmp_path / "completed"
    watcher = source / COMPLETION.FINAL_C1.WATCHER_NAME
    _write_json(watcher, {"status": "clean"})
    source_abort = {
        "schema": COMPLETION.RECOVERY.ABORT_SCHEMA,
        "status": "terminal_aborted_no_admission",
        "writer": "final_c1_retry",
        "recorded_at": "2026-07-29T12:00:00Z",
        "no_auto_retry": True,
        "no_admission": True,
    }
    _write_json(
        source / COMPLETION.RECOVERY.ABORT_MARKER_NAME,
        source_abort,
    )
    _write_jsonl(
        source / COMPLETION.FINAL_C1.ATTEMPTS_NAME,
        [{"ordinal": 0, "state": "succeeded"}],
    )
    state.update(
        {
            "hashes": COMPLETION.source_hashes(source),
            "plan": {
                "amendment_receipt": {"sha256": "a" * 64},
                "predecessor_watcher": {"sha256": "b" * 64},
                "predecessor_failed_attempts": [],
            },
            "proposal": {
                "frontdoor_capacity": {
                    "held_recovery_claim": {"claim_id": "unit-q2"}
                },
                "instrument": {
                    "measurement_source_sha256": {
                        "/sealed/scripts/benchmark/debug_scorer.py": "c" * 64,
                        "/sealed/scripts/benchmark/seeding_scoring.py": "d" * 64,
                    }
                },
            },
            "source_abort": source_abort,
        }
    )
    state["tree_sha256"] = COMPLETION.canonical_hash(state["hashes"])
    source_before = COMPLETION.source_hashes(source)
    manifest, _selected = COMPLETION.build_provenance_manifest(source, state)
    monkeypatch.setattr(
        COMPLETION,
        "_validate_aborted_source",
        lambda *_args: state,
    )
    monkeypatch.setattr(
        COMPLETION.RACE,
        "_require_clean_predecessor_watcher",
        lambda _path: None,
    )
    monkeypatch.setattr(COMPLETION.V4, "fsync_dir", lambda _path: None)

    complete_r2_kwargs: dict[str, object] = {}

    def complete_r2(
        destination: Path,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        complete_r2_kwargs.update(_kwargs)
        responses = [
            state["journal"][ordinal]["response"]
            for ordinal in range(COMPLETION.RECOVERY.N)
        ]
        sidecars = [
            _sidecar(ordinal)
            for ordinal in range(COMPLETION.RECOVERY.N)
        ]
        response_path = destination / "responses.T2.r2.jsonl"
        sidecar_path = (
            destination
            / "eval_sidecars/question_results.e8-t2-r2.jsonl"
        )
        trace_path = destination / "judge_traces.T2.r2.jsonl"
        raw_path = destination / "raw.T2.r2.json"
        _write_jsonl(response_path, responses)
        _write_jsonl(sidecar_path, sidecars)
        _write_jsonl(trace_path, [])
        _write_json(raw_path, {"ts": "placeholder"})
        _write_json(
            destination / "r2_complete.json",
            {
                "responses_sha256": COMPLETION.sha256_path(response_path),
                "sidecar_sha256": COMPLETION.sha256_path(sidecar_path),
                "trace_sha256": COMPLETION.sha256_path(trace_path),
                "raw_sha256": COMPLETION.sha256_path(raw_path),
                "journal_sha256": COMPLETION.sha256_path(
                    destination / "recovery_rows.T2.r2.jsonl"
                ),
                "attempts_sha256": COMPLETION.sha256_path(
                    destination / COMPLETION.FINAL_C1.ATTEMPTS_NAME
                ),
            },
        )

    monkeypatch.setattr(
        COMPLETION.RECOVERY,
        "_complete_r2",
        complete_r2,
    )
    args = SimpleNamespace(
        source_dir=source,
        output_dir=output,
        expected_source_tree_sha256=state["tree_sha256"],
    )

    assert COMPLETION.execute(args) == output
    assert complete_r2_kwargs["historical_source_sha256"] == {
        "debug_scorer": "c" * 64,
        "seeding_scoring": "d" * 64,
    }
    validation = COMPLETION.validate_published(args)

    assert validation["status"] == "published_complete_valid"
    assert COMPLETION.source_hashes(source) == source_before
    assert COMPLETION.sha256_path(
        output / COMPLETION.SOURCE_ABORT_COPY_NAME
    ) == source_before[COMPLETION.RECOVERY.ABORT_MARKER_NAME]
    assert COMPLETION.V4.load_json(output / COMPLETION.MANIFEST_NAME) == manifest
    assert COMPLETION.V4.load_json(
        output / COMPLETION.RUN_SEAL_NAME
    )["status"] == COMPLETION.TERMINAL_SEAL.COMPLETE_STATUS

    replay = COMPLETION.V4.load_jsonl(output / COMPLETION.SCORE_REPLAY_NAME)
    replay[0]["after_correct"] = not replay[0]["after_correct"]
    _write_jsonl(output / COMPLETION.SCORE_REPLAY_NAME, replay)
    with pytest.raises(ValueError, match="deterministic completion output differs"):
        COMPLETION.validate_published(args)


def test_deterministic_score_replay_corrects_live_bcb190_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A historical false cannot survive a pinned code-execution replay."""
    monkeypatch.setattr(COMPLETION.RECOVERY, "N", 419)
    questions = [_question(ordinal) for ordinal in range(419)]
    questions[418] = {
        "qid": "bcb_BigCodeBench/190",
        "suite": "bigcodebench",
        "scoring_method": "code_execution",
        "scoring_config": {"language": "python"},
        "expected": "assert True",
    }
    journal = {
        ordinal: {
            "ordinal": ordinal,
            "source": "reuse",
            "response": _response(ordinal),
        }
        for ordinal in range(419)
    }
    response = journal[418]["response"]
    response.update(
        {
            "qid": "bcb_BigCodeBench/190",
            "suite": "bigcodebench",
            "scoring_method": "code_execution",
            "answer": "assert True",
            "correct": False,
            "scoring_config_sha256": COMPLETION.canonical_hash(
                {"language": "python"}
            ),
        }
    )
    selected = {ordinal: _sidecar(ordinal) for ordinal in range(419)}
    selected[418] = {
        "row_type": "question_result",
        "ordinal": 418,
        "answer": "assert True",
        "result": {
            "qid": "bcb_BigCodeBench/190",
            "question_id": "bcb_BigCodeBench/190",
            "tokens_generated": 1,
            "correct": False,
            "route": "frontdoor",
            "answer_hash": COMPLETION.V5._normalized_answer_hash("assert True"),
        },
    }
    monkeypatch.setattr(
        COMPLETION.V4,
        "independently_score_response",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        COMPLETION,
        "_scorer_runtime_witness",
        lambda: {"test_runtime": "pinned"},
    )

    working, records, corrections = COMPLETION._replay_deterministic_scores(
        {"journal": journal, "questions": questions}, selected
    )

    record = next(row for row in records if row["ordinal"] == 418)
    assert record["qid"] == "bcb_BigCodeBench/190"
    assert record["changed"] is True
    assert record["before_correct"] is False
    assert record["after_correct"] is True
    assert record["scorer_sources_sha256"] == COMPLETION.canonical_hash(
        record["scorer_sources"]
    )
    assert record["scorer_runtime_witness_sha256"] == COMPLETION.canonical_hash(
        record["scorer_runtime_witness"]
    )
    assert working[418]["response"]["correct"] is True
    assert corrections[418]["result"]["correct"] is True


def test_parent_fsync_failure_terminalizes_published_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "sentinel").write_text("unchanged\n", encoding="utf-8")
    source_before = COMPLETION.source_hashes(source)
    output = tmp_path / "output"
    manifest = {"schema": COMPLETION.SCHEMA, "entries_sha256": "e" * 64}
    _stub_successful_completion(monkeypatch, manifest)
    monkeypatch.setattr(
        COMPLETION.V4,
        "fsync_dir",
        lambda _path: (_ for _ in ()).throw(OSError("fsync failed")),
    )

    with pytest.raises(OSError, match="fsync failed"):
        COMPLETION.execute(
            SimpleNamespace(
                source_dir=source,
                output_dir=output,
                expected_source_tree_sha256="f" * 64,
            )
        )

    seal = COMPLETION.V4.load_json(output / COMPLETION.RUN_SEAL_NAME)
    assert seal["status"] == COMPLETION.TERMINAL_SEAL.TERMINAL_STATUS
    assert seal["no_admission"] is True
    assert not list(tmp_path.glob(".output.staging-*"))
    assert COMPLETION.source_hashes(source) == source_before


def test_source_hashes_rejects_special_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    os.mkfifo(source / "unbound.fifo")

    with pytest.raises(ValueError, match="special file"):
        COMPLETION.source_hashes(source)


def test_historical_receipt_binds_source_producer_not_current_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt_path = tmp_path / "receipt.json"
    historical_runner = "1" * 64
    historical_helper = "2" * 64
    _write_json(
        receipt_path,
        {
            "schema": COMPLETION.FINAL_C1.RECEIPT_SCHEMA,
            "status": "ratified",
            "human_attestation": COMPLETION.FINAL_C1.ATTESTATION,
            "authorization": COMPLETION.FINAL_C1._receipt_contract(),
            "non_authorizations": {
                "no_inference_by_ratifier": True,
                "no_lineup_mutation": True,
                "no_state_write": True,
            },
            "instrument": {
                "commit": "historical-commit",
                "runner": {
                    "path": "scripts/benchmark/final_c1_retry.py",
                    "sha256": historical_runner,
                },
                "recovery_helper": {
                    "path": (
                        "scripts/benchmark/"
                        "recover_e8_quality_baseline_v5_partial_r2.py"
                    ),
                    "sha256": historical_helper,
                },
            },
        },
    )
    reference = {
        "path": str(receipt_path),
        "schema": COMPLETION.FINAL_C1.RECEIPT_SCHEMA,
        "sha256": COMPLETION.sha256_path(receipt_path),
    }
    plan = {
        "amendment_receipt": reference,
        "retry_runner_sha256": historical_runner,
    }
    proposal = {
        "instrument": {
            "commit": "historical-commit",
            "runner_sha256": historical_helper,
            "measurement_source_sha256": {
                (
                    "/historical/scripts/benchmark/"
                    "recover_e8_quality_baseline_v5_partial_r2.py"
                ): historical_helper,
            },
        }
    }
    monkeypatch.setattr(
        COMPLETION.FINAL_C1,
        "CANONICAL_RECEIPT",
        receipt_path,
    )

    assert COMPLETION._source_receipt_is_bound(plan, proposal) == reference
    assert historical_helper != COMPLETION.sha256_path(
        COMPLETION.FINAL_C1.RECOVERY_PATH
    )


def test_aborted_source_rejects_unbound_writer_abort(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_json(
        source / COMPLETION.RECOVERY.ABORT_MARKER_NAME,
        {
            "schema": COMPLETION.RECOVERY.ABORT_SCHEMA,
            "status": "terminal_aborted_no_admission",
            "writer": "different_writer",
            "no_auto_retry": True,
            "no_admission": True,
        },
    )
    hashes = COMPLETION.source_hashes(source)

    with pytest.raises(ValueError, match="source abort differs"):
        COMPLETION._validate_aborted_source(
            source, COMPLETION.canonical_hash(hashes)
        )


def test_historical_scorer_sources_requires_exact_sealed_pair() -> None:
    state = {
        "proposal": {
            "instrument": {
                "measurement_source_sha256": {
                    "/historical/scripts/benchmark/debug_scorer.py": "a" * 64,
                    "/historical/scripts/benchmark/seeding_scoring.py": "b" * 64,
                }
            }
        }
    }

    assert COMPLETION._historical_scorer_sources(state) == {
        "debug_scorer": "a" * 64,
        "seeding_scoring": "b" * 64,
    }

    state["proposal"]["instrument"]["measurement_source_sha256"].pop(
        "/historical/scripts/benchmark/seeding_scoring.py"
    )
    with pytest.raises(ValueError, match="ambiguous scorer source binding"):
        COMPLETION._historical_scorer_sources(state)


def test_audit_never_accepts_an_output_namespace(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit):
        COMPLETION.parse_args(
            [
                "--source-dir",
                str(tmp_path),
                "--expected-source-tree-sha256",
                "f" * 64,
                "--audit",
                "--output-dir",
                str(tmp_path / "output"),
            ]
        )

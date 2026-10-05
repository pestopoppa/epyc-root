from __future__ import annotations

from contextlib import nullcontext
import fcntl
import importlib.util
import json
import hashlib
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.autopilot_core.instrument_era_guard import E7_EVAL_INSTRUMENT_ERA_ID


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATED_E8_ROOT = PROJECT_ROOT


def _integrated_e8_head() -> str:
    """Sample the live source HEAD at pin-construction time.

    Both wrappers re-read ``git rev-parse HEAD`` in the subprocess and refuse when
    it differs from ``E8_V5_ORCHESTRATOR_HEAD``.  This is a SHARED clone, so a
    module-import-time snapshot leaves a whole test-session-long window in which
    another session's commit invalidates every pin this module hands out.  Sampling
    per call shrinks that window to the subprocess spawn and weakens nothing: the
    wrappers still fail closed when the live HEAD differs from the supplied pin.
    """
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
    ).strip()


# The canonical AutoPilot state is LIVE runtime state, not repo content: it is
# gitignored, so it exists only in the main checkout.  Deliberately absolute — a
# __file__ anchor would point a worktree at a file that cannot exist there.
CANONICAL_STATE_PATH = Path(
    "/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_state.json"
)
MODULE_PATH = PROJECT_ROOT / "scripts/benchmark/run_e8_quality_baseline_v5.py"
spec = importlib.util.spec_from_file_location("e8_v5", MODULE_PATH)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_applier_module(name: str):
    """Load the reviewed v5 adapter and hand back the canonical applier module."""
    adapter = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
    )
    adapter_spec = importlib.util.spec_from_file_location(name, adapter)
    assert adapter_spec is not None and adapter_spec.loader is not None
    adapter_module = importlib.util.module_from_spec(adapter_spec)
    sys.modules[adapter_spec.name] = adapter_module
    adapter_spec.loader.exec_module(adapter_module)
    return adapter_module.module


# apply_e8_quality_baseline_state.validate_state_precondition() requires the E8
# quality-rebaseline hold to still be OPEN at the E8 boundary.  There is no shared
# constant for the status string (the applier's SHA-256 is pinned by ratified
# operator receipts and by scripts/benchmark/final_c1_retry.py, so it cannot be
# refactored to export one).  _e7_pre_state() therefore re-checks every value it
# writes against the applier's OWN predicate, so a contract change fails loudly
# here instead of silently seeding an invalid fixture.
_E8_HOLD_OPEN_STATUS = "hold_open"


def _e7_pre_state(canonical) -> dict:
    """Derive the E7 baseline pre-state that the canonical applier accepts.

    The live AutoPilot state is the only realistic pre-state shape (four populated
    quality tiers with real provenance), but it is MUTABLE runtime state, not a
    fixture: on 2026-08-04T09:48:42Z the operator ran
    ``scripts/autopilot/operator_seed_e8_operational_baseline.py --apply``, which
    stamped ``baseline_state.eval_quality_era`` to the active era and moved
    ``e8_quality_rebaseline.status`` ``hold_open -> closed_operational``.  The
    ratification-grade applier is a one-shot E7 -> E8 transaction and correctly
    refuses that post-seed state, so these tests must reconstruct the pre-state
    rather than copy the live file. The live active era is also mutable: E9 moved
    it on 2026-08-05, so this historical one-shot fixture must explicitly restore
    the applier's E8 era instead of borrowing today's value.
    """
    state = json.loads(CANONICAL_STATE_PATH.read_bytes())
    state["baseline_state"] = {
        **state["baseline_state"],
        "eval_quality_era": E7_EVAL_INSTRUMENT_ERA_ID,
    }
    state["active_instrument_eras"] = {
        **(state.get("active_instrument_eras") or {}),
        "eval_quality": "E8",
    }
    hold = {
        key: value
        for key, value in (state.get("e8_quality_rebaseline") or {}).items()
        if key not in ("closed_at", "closed_by")
    }
    hold["boundary"] = canonical.E8_BOUNDARY
    hold["status"] = _E8_HOLD_OPEN_STATUS
    state["e8_quality_rebaseline"] = hold
    # Fail loudly if the applier's pre-state contract ever moves away from what
    # this helper reconstructs, instead of handing tests a silently stale fixture.
    canonical.validate_state_precondition(state)
    return state


def _e7_pre_state_bytes(canonical) -> bytes:
    return (json.dumps(_e7_pre_state(canonical), indent=2, sort_keys=True) + "\n").encode()


def test_durable_candidate_writer_marks_new_staging_and_published_namespaces(
    tmp_path: Path,
) -> None:
    output = tmp_path / "candidate"
    staging = tmp_path / ".candidate.staging-fault"

    @runner.durable_candidate_writer("fault_injection")
    def fail(args: SimpleNamespace) -> None:
        staging.mkdir()
        output.mkdir()
        raise RuntimeError("injected failure")

    with pytest.raises(RuntimeError, match="injected failure"):
        fail(SimpleNamespace(output_dir=output))
    for namespace in (staging, output):
        marker = json.loads((namespace / runner.ABORT_MARKER_NAME).read_text())
        assert marker["schema"] == runner.ABORT_SCHEMA
        assert marker["status"] == "aborted"
        assert marker["writer"] == "fault_injection"
        assert marker["error_class"] == "RuntimeError"
        seal = json.loads((namespace / "run_seal.json").read_text())
        assert seal["status"] == "terminal_aborted_no_admission"
        assert seal["abort_marker_sha256"] == _sha(
            namespace / runner.ABORT_MARKER_NAME
        )


def test_durable_candidate_writer_marks_false_terminal_result(tmp_path: Path) -> None:
    output = tmp_path / "candidate"
    staging = tmp_path / ".candidate.staging-false"

    @runner.durable_candidate_writer("false_injection")
    def fail(_args: SimpleNamespace) -> bool:
        staging.mkdir()
        return False

    assert fail(SimpleNamespace(output_dir=output)) is False
    marker = json.loads((staging / runner.ABORT_MARKER_NAME).read_text())
    assert marker["status"] == "aborted"
    assert marker["error"] == "false_injection returned non-success status False"
    assert json.loads((staging / "run_seal.json").read_text())["status"] == (
        "terminal_aborted_no_admission"
    )


def test_execute_marks_real_ineligible_staging_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "candidate"
    state_path = tmp_path / "state.json"
    state_path.write_text("{}\n")
    watcher_rows = [
        {
            "started_at": "2026-07-28T00:00:00Z",
            "finished_at": "2026-07-28T00:00:00Z",
            "ok": True,
        },
        {
            "started_at": "2026-07-28T00:00:05Z",
            "finished_at": "2026-07-28T00:00:05Z",
            "ok": True,
        },
    ]

    class FakeThread:
        alive = True

        def is_alive(self) -> bool:
            return self.alive

    class FakeWatcher:
        def __init__(self, _args, _binding, path: Path, **_kwargs) -> None:
            self.path = path
            self._thread = FakeThread()
            self.samples: list[dict] = []
            self.fatal_error = None

        def start(self) -> None:
            return None

        def active_load(self, **_kwargs):
            return nullcontext()

        def stop(self) -> list[dict]:
            _jsonl(self.path, watcher_rows)
            self.samples = watcher_rows
            self._thread.alive = False
            return self.samples

    class FakeTower:
        def __init__(self, **_kwargs) -> None:
            self._question_artifact_dir = None

    report = {
        "blockers": [],
        "preconditions": {
            "file_sha256": {},
            "health": {"ok": True, "payload_sha256": "health"},
            "numeric_rerun": {},
        },
    }
    monkeypatch.setattr(runner, "protocol_proposal", lambda _args: {})
    monkeypatch.setattr(runner.V4, "prepare_report", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(runner.V4, "runtime_binding", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(runner.V4, "EvalTower", FakeTower)
    monkeypatch.setattr(runner.V4, "probe_url_mapping", lambda _health: {})
    monkeypatch.setattr(runner.V4, "RuntimeWatcher", FakeWatcher)
    monkeypatch.setattr(runner.V4, "require_clean_watcher", lambda _watcher: None)
    monkeypatch.setattr(
        runner.V4,
        "question_vector",
        lambda _tower, *, tier, **_kwargs: (
            [{"qid": f"q{tier}", "suite": "suite"}],
            f"core-{tier}",
        ),
    )
    monkeypatch.setattr(
        runner.V4, "validate_source_vector_scorer_config", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        runner.V4, "apply_context_replacement_map", lambda _args, questions, **_kwargs: questions
    )
    monkeypatch.setattr(
        runner.V4,
        "public_vector",
        lambda questions, *, tier, core_id, seed: {
            "n": len(questions),
            "tier": tier,
            "core_id": core_id,
            "seed": seed,
        },
    )
    monkeypatch.setattr(
        runner.V4,
        "scoring_vector",
        lambda questions, *, tier, core_id, seed: {
            "questions": questions,
            "tier": tier,
            "core_id": core_id,
            "seed": seed,
        },
    )
    monkeypatch.setattr(runner.V4, "frontdoor_context_coverage", lambda *_args: {})
    monkeypatch.setattr(runner.V4, "candidate_contract_from_proposal", lambda *_args: {})
    monkeypatch.setattr(runner, "protocol_contract", lambda *_args: None)
    monkeypatch.setattr(
        runner,
        "run_repetition_v5",
        lambda *_args, tier, **_kwargs: (
            {
                "ts": "2026-07-28T00:00:00Z",
                "q": 0.0,
                "core_id": f"core-{tier}",
            },
            {
                "error_classification": {"infrastructure": 1},
                "n_results": 1,
                "actual_eval_concurrency": [runner.V4.CONCURRENCY],
                "response_vector_matches_input": True,
                "per_suite_counts_match_input": True,
                "runtime_binding_matches_pre": True,
                "all_routes_frontdoor": True,
                "sidecar_sha256": "0" * 64,
                "judge_trace_sha256": "0" * 64,
                "scoring_audit": {"matches": True},
            },
        ),
    )
    monkeypatch.setattr(
        runner.V4, "api_health", lambda *_args: {"ok": True, "payload_sha256": "health"}
    )
    monkeypatch.setattr(runner.V4, "file_fingerprints", lambda *_args: {})
    monkeypatch.setattr(runner.V4, "immutable_paths", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runner.V4, "numeric_rerun_status", lambda *_args: {})
    monkeypatch.setattr(runner.V4, "load_json", lambda _path: {})
    monkeypatch.setattr(runner, "validate_repetition_artifacts", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner.V4, "build_evidence", lambda **_kwargs: ({}, {}))

    result, status = runner.execute(
        SimpleNamespace(
            output_dir=output,
            api_url="http://test",
            http_timeout_s=1,
            t1_n=1,
            t2_n=1,
            t1_core_id="core-1",
            seed=42,
            state_path=state_path,
        )
    )

    assert status == 2
    assert result["decision_grade"] is False
    assert not output.exists()
    staging = next(tmp_path.glob(".candidate.staging-*"))
    marker = json.loads((staging / runner.ABORT_MARKER_NAME).read_text())
    assert marker["status"] == "aborted"
    assert marker["writer"] == "run_e8_quality_baseline_v5"
    assert marker["error"] == "run_e8_quality_baseline_v5 returned non-success status 2"
    seal = json.loads((staging / "run_seal.json").read_text())
    assert seal["status"] == "terminal_aborted_no_admission"
    assert seal["superseded_run_seal_status"] == "failed"


def _integrated_e8_pins(*, wrapper: Path | None = None, validator_wrapper: Path | None = None) -> dict[str, str]:
    """Pins used by the final wrapper's exact integration-source contract."""
    benchmark = INTEGRATED_E8_ROOT / "scripts/benchmark"
    pins = {
        "E8_V5_SOURCE_ROOT": str(INTEGRATED_E8_ROOT),
        "E8_V5_ORCHESTRATOR_HEAD": _integrated_e8_head(),
        "E8_V5_PRODUCER_SHA256": _sha(benchmark / "terminalize_e8_quality_baseline_source.py"),
        "E8_V5_RUNNER_SHA256": _sha(benchmark / "run_e8_quality_baseline_v5.py"),
        "E8_V5_BASE_RUNNER_SHA256": _sha(benchmark / "run_e8_quality_baseline_reseed.py"),
        "E8_V5_RESUME_RUNNER_SHA256": _sha(benchmark / "resume_e8_quality_baseline_v5.py"),
        "E8_V5_RECOVERY_RUNNER_SHA256": _sha(
            benchmark / "recover_e8_quality_baseline_v5_partial_r2.py"
        ),
        "E8_V5_FINALIZER_RUNNER_SHA256": _sha(
            benchmark / "finalize_e8_quality_baseline_v5_recovery_r2.py"
        ),
        "E8_V5_SUCCESSOR_RUNNER_SHA256": _sha(
            benchmark / "prepare_e8_quality_baseline_v5_partial_r2_successor.py"
        ),
        "E8_V5_RACE_RETRY_RUNNER_SHA256": _sha(
            benchmark / "prepare_e8_quality_baseline_v5_partial_r2_race_retry.py"
        ),
        "E8_V5_MIXED_TAIL_REPAIR_RUNNER_SHA256": _sha(
            benchmark / "prepare_e8_quality_baseline_v5_partial_r2_mixed_tail_repair.py"
        ),
        "E8_V5_TERMINALIZER_RUNNER_SHA256": _sha(
            benchmark / "terminalize_e8_quality_baseline_v5_partial_r2_successor.py"
        ),
        "E8_V5_FINAL_C1_RETRY_RUNNER_SHA256": _sha(benchmark / "final_c1_retry.py"),
        "E8_V5_FINAL_C1_VALIDATOR_SHA256": _sha(benchmark / "final_c1_validator.py"),
        "E8_V5_VALIDATOR_PY_SHA256": _sha(benchmark / "validate_e8_quality_baseline_v5.py"),
    }
    if wrapper is not None:
        pins["E8_V5_WRAPPER_SHA256"] = _sha(wrapper)
    if validator_wrapper is not None:
        pins["E8_V5_VALIDATOR_SHA256"] = _sha(validator_wrapper)
    return pins


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _response(qid: str, answer: str, *, error: str | None = None, partial: bool = False) -> dict:
    return {
        "qid": qid,
        "suite": "suite",
        "scoring_method": "exact_match",
        "answer": answer,
        "correct": error is None,
        "error": error,
        "partial": partial,
        "degraded": False,
        "route_used": "frontdoor",
        "scoring_config_sha256": runner.canonical_hash({}),
    }


def _sidecar(qids: list[str], *, failure_ordinal: int = 0) -> list[dict]:
    rows = [{"row_type": "batch_start", "requested_n": len(qids)}]
    for ordinal, qid in enumerate(qids):
        result = {"qid": qid, "question_id": qid, "tokens_generated": 1, "error": False}
        answer = "a"
        if ordinal == failure_ordinal:
            answer = "timed out"
            result.update(
                {
                    "tokens_generated": 0,
                    "error": True,
                    "error_detail": "timed out",
                    "partial": False,
                    "degraded": False,
                }
            )
        rows.append(
            {
                "row_type": "question_result",
                "ordinal": ordinal,
                "answer": answer,
                "result": result,
                "eval_batch_id": "full-batch",
                "label": "e8-t2-r1",
                "requested_n": len(qids),
                "complete": False,
                "started_at_s": 1.0,
                "ended_at_s": 2.0,
                "elapsed_s": 1.0,
                "scored_at_s": 2.1,
            }
        )
    rows.append({"row_type": "batch_complete", "complete": True})
    return rows


@pytest.mark.parametrize("error", sorted(runner.ACCEPTED_INFRA_ERRORS))
def test_generation_classifier_accepts_only_evidence_bound_reviewed_errors(error: str) -> None:
    response = _response("q", error, error=error)
    sidecar = {
        "result": {
            "qid": "q",
            "question_id": "q",
            "tokens_generated": 0,
            "error": True,
            "error_detail": error,
            "partial": False,
            "degraded": False,
        }
    }
    assert runner.classify_generation_failure(response, sidecar) == error


@pytest.mark.parametrize("question_id", ["unknown", "other"])
def test_generation_classifier_rejects_unbound_eval_tower_question_id(
    question_id: str,
) -> None:
    response = _response("stable-qid", "timed out", error="timed out")
    sidecar = {
        "result": {
            "qid": "stable-qid",
            "question_id": question_id,
            "tokens_generated": 0,
            "error": True,
            "error_detail": "timed out",
            "partial": False,
            "degraded": False,
        }
    }
    assert runner.classify_generation_failure(response, sidecar) is None


def test_generation_classifier_rejects_missing_eval_tower_question_id() -> None:
    response = _response("stable-qid", "timed out", error="timed out")
    sidecar = {
        "result": {
            "qid": "stable-qid",
            "tokens_generated": 0,
            "error": True,
            "error_detail": "timed out",
            "partial": False,
            "degraded": False,
        }
    }
    assert runner.classify_generation_failure(response, sidecar) is None


@pytest.mark.parametrize(
    "result_change",
    [
        {},
        {"partial": True, "degraded": False},
        {"partial": False, "degraded": True},
        {"partial": "false", "degraded": False},
        {"partial": False, "degraded": "false"},
    ],
)
def test_generation_classifier_requires_explicit_clean_sidecar_state(
    result_change: dict,
) -> None:
    response = _response("q", "timed out", error="timed out")
    sidecar = {
        "result": {
            "qid": "q",
            "question_id": "q",
            "tokens_generated": 0,
            "error": True,
            "error_detail": "timed out",
            **result_change,
        }
    }
    assert runner.classify_generation_failure(response, sidecar) is None


def test_generation_failure_targets_rejects_unbound_sidecar() -> None:
    response = _response("q", "timed out", error="timed out")
    sidecar = {
        "result": {
            "qid": "q",
            "question_id": "unknown",
            "tokens_generated": 0,
            "error": True,
            "error_detail": "timed out",
            "partial": False,
            "degraded": False,
        }
    }
    assert runner.generation_failure_targets([response], {0: (0, sidecar)}) == []


@pytest.mark.parametrize(
    ("answer", "tokens", "result_error", "detail"),
    [
        ("", 0, False, "timed out"),
        ("model output", 0, True, "timed out"),
        ("", 1, True, "timed out"),
        ("", 0, True, ""),
        ("", 0, True, "empty model output"),
        ("", 0, True, "truncated"),
        ("", 0, True, "loop detected"),
        ("", 0, True, "code execution failed"),
        ("answer", 4, True, "scoring_unavailable: judge down"),
        ("", False, True, "timed out"),
    ],
)
def test_generation_classifier_rejects_model_and_scorer_failures(
    answer: str, tokens: int, result_error: bool, detail: str
) -> None:
    assert (
        runner.classify_generation_failure(
            _response("q", answer, error=detail or None),
            {
                "result": {
                    "qid": "q",
                    "question_id": "q",
                    "tokens_generated": tokens,
                    "error": result_error,
                    "error_detail": detail,
                    "partial": False,
                    "degraded": False,
                }
            },
        )
        is None
    )


def test_generation_classifier_rejects_cross_ledger_mismatch() -> None:
    sidecar = {
        "result": {
            "qid": "other",
            "question_id": "other",
            "tokens_generated": 0,
            "error": True,
            "error_detail": "timed out",
            "partial": False,
            "degraded": False,
        }
    }
    assert (
        runner.classify_generation_failure(
            _response("q", "timed out", error="request timed out"), sidecar
        )
        is None
    )


@pytest.mark.parametrize(
    "result_change",
    [
        {"question_id": "unknown"},
        {"question_id": "other"},
        {"partial": True},
        {"degraded": True},
    ],
)
def test_clean_sidecar_rejects_unbound_or_incomplete_result(
    result_change: dict,
) -> None:
    response = _response("q", "answer")
    result = {
        "qid": "q",
        "question_id": "q",
        "correct": True,
        "tokens_generated": 1,
        "route": "frontdoor",
        "answer_hash": runner._normalized_answer_hash("answer"),
        **result_change,
    }
    assert not runner.validate_clean_sidecar_result(
        response,
        {"answer": "answer", "result": result},
        qid="q",
    )


@pytest.mark.parametrize(
    "response_change",
    [
        {"partial": True},
        {"degraded": True},
        {"route_used": "worker_general"},
    ],
)
def test_generation_classifier_rejects_nonclean_response_state(
    response_change: dict,
) -> None:
    response = {
        **_response("q", "timed out", error="timed out"),
        **response_change,
    }
    sidecar = {
        "result": {
            "qid": "q",
            "question_id": "q",
            "tokens_generated": 0,
            "error": True,
            "error_detail": "timed out",
            "partial": False,
            "degraded": False,
        }
    }
    assert runner.classify_generation_failure(response, sidecar) is None


class FakeTower:
    def __init__(
        self,
        sidecar_dir: Path,
        *,
        fail: bool = False,
        partial: bool = False,
        malformed_success: str | None = None,
        question_id: str | None = None,
    ) -> None:
        self.sidecar_dir = sidecar_dir
        self.fail = fail
        self.partial = partial
        self.malformed_success = malformed_success
        self.question_id = question_id
        self.calls = 0

    def _eval_batch(self, questions, _client, *, log_every, label):
        del log_every
        self.calls += 1
        qid = questions[0]["qid"]
        question_id = self.question_id or qid
        error = "timed out" if self.fail else None
        answer = error or "a"
        result_row = {
            "qid": qid,
            "question_id": question_id,
            "tokens_generated": 0 if error else 1,
            "error": bool(error),
            "error_detail": error,
        }
        if error:
            result_row.update({"partial": False, "degraded": False})
        sidecar_answer = answer
        if not error and self.malformed_success == "zero_tokens":
            result_row["tokens_generated"] = 0
        elif not error and self.malformed_success == "result_error":
            result_row.update({"error": True, "error_detail": "model failed"})
        elif not error and self.malformed_success == "qid":
            result_row.update({"qid": "other", "question_id": "other"})
        elif not error and self.malformed_success == "answer":
            sidecar_answer = "different"
        _jsonl(
            self.sidecar_dir / f"question_results.{label}.jsonl",
            [
                {"row_type": "batch_start", "requested_n": 1},
                {
                    "row_type": "question_result",
                    "ordinal": 0,
                    "answer": sidecar_answer,
                    "result": result_row,
                    "complete": False,
                    "started_at_s": 3.0,
                    "ended_at_s": 3.25,
                    "elapsed_s": 0.25,
                },
                {"row_type": "batch_complete", "complete": True},
            ],
        )
        return [
            SimpleNamespace(
                qid=qid,
                question_id=question_id,
                answer=answer,
                correct=error is None,
                error=error,
                partial=self.partial,
                degraded=False,
                route_used="frontdoor",
                eval_concurrency=1,
                suite="suite",
                prompt="",
                eval_partition="core",
                elapsed_s=0.25,
                tokens_generated=0 if error else 1,
                tools_used=0,
                host_covariates={},
                # Mirrors the real QuestionResult default
                # (`eval_tower.py`: `retrieval_compaction: dict[str, Any] =
                # field(default_factory=dict)`). `_compact_question_result`
                # reads it unguarded, so a stand-in that omits it raises
                # AttributeError rather than exercising the no-compaction path.
                retrieval_compaction={},
                scoring_method="exact_match",
                tools_called=[],
                confidence_source="binary_correctness_proxy",
                confidence=1.0,
                exogenous_recovered=False,
                exogenous_unrecovered=False,
                external_restart=False,
                retry_count=0,
                rubric_scores={},
                rubric_source=None,
                # Mirrors the real QuestionResult default
                # (`rubric_threshold_source: str = ""`, added by RC-12 5a9442d3);
                # `_compact_question_result` serializes it for every row.
                rubric_threshold_source="",
            )
        ]


def _tail_fixture(
    tmp_path: Path, *, target_question_id: str = "q0"
) -> tuple[list[dict], Path, Path, Path, Path]:
    questions = [
        {
            "qid": "q0",
            "suite": "suite",
            "scoring_method": "exact_match",
            "expected": "a",
            "scoring_config": {},
        },
        {
            "qid": "q1",
            "suite": "suite",
            "scoring_method": "exact_match",
            "expected": "a",
            "scoring_config": {},
        },
    ]
    responses = tmp_path / "responses.T2.r1.jsonl"
    sidecar_dir = tmp_path / "eval_sidecars"
    sidecar = sidecar_dir / "question_results.e8-t2-r1.jsonl"
    trace = tmp_path / "judge_traces.T2.r1.jsonl"
    _jsonl(responses, [_response("q0", "timed out", error="timed out"), _response("q1", "a")])
    sidecar_rows = _sidecar(["q0", "q1"])
    sidecar_rows[1]["result"]["question_id"] = target_question_id
    _jsonl(sidecar, sidecar_rows)
    _jsonl(trace, [])
    return questions, responses, sidecar, trace, sidecar_dir


def _patch_tail_runtime(monkeypatch) -> None:
    monkeypatch.setattr(runner.V4, "require_clean_watcher", lambda _watcher: None)
    monkeypatch.setattr(runner.V4.httpx, "Client", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(
        runner.V4, "capture_llm_judge_traces", lambda *_args, **_kwargs: nullcontext()
    )
    monkeypatch.setattr(
        runner.V4, "bind_eval_tower_scorer_identities", lambda *_args, **_kwargs: nullcontext()
    )
    monkeypatch.setattr(runner.V4, "replay_llm_judge_scorer_tail_once", lambda *_args: [])


def test_generation_tail_replaces_only_target_response_and_sidecar_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_tail_runtime(monkeypatch)
    questions, responses, sidecar, trace, sidecar_dir = _tail_fixture(tmp_path)
    original_responses = responses.read_bytes().splitlines(keepends=True)
    original_sidecar = sidecar.read_bytes().splitlines(keepends=True)
    tail = runner.run_generation_tail(
        FakeTower(sidecar_dir),
        tier=2,
        repetition=1,
        questions=questions,
        responses_path=responses,
        sidecar_path=sidecar,
        judge_trace_path=trace,
        sidecar_dir=sidecar_dir,
        output_dir=tmp_path,
        published_dir=tmp_path,
        args=SimpleNamespace(api_url="http://127.0.0.1:8000"),
        watcher=object(),
    )
    final_responses = responses.read_bytes().splitlines(keepends=True)
    final_sidecar = sidecar.read_bytes().splitlines(keepends=True)
    assert tail["retry_count"] == 1
    assert final_responses[0] != original_responses[0]
    assert final_responses[1] == original_responses[1]
    assert final_sidecar[1] != original_sidecar[1]
    assert final_sidecar[2:] == original_sidecar[2:]
    _parsed, final_rows = runner.sidecar_question_rows(sidecar, expected_n=2)
    repaired = final_rows[0][1]
    assert repaired["eval_batch_id"] == "full-batch"
    assert repaired["label"] == "e8-t2-r1"
    assert repaired["requested_n"] == 2
    assert repaired["started_at_s"] == 3.0
    assert repaired["ended_at_s"] == 3.25
    assert repaired["answer"] == "a"
    assert "scored_at_s" not in repaired
    assert repaired["result"]["qid"] == "q0"
    assert repaired["result"]["question_id"] == "q0"
    assert repaired["result"].get("error") is None
    attempts = runner.V4.load_jsonl(tmp_path / "generation_tail_attempts.T2.r1.jsonl")
    assert attempts[0]["outcome"] == "recovered"
    assert attempts[0]["concurrency"] == 1
    assert attempts[0]["request_timeout_s"] == 300


@pytest.mark.parametrize(("fail", "partial"), [(True, False), (False, True)])
def test_generation_tail_retry_failure_fails_whole_candidate_and_keeps_attempt(
    tmp_path: Path, monkeypatch, fail: bool, partial: bool
) -> None:
    _patch_tail_runtime(monkeypatch)
    questions, responses, sidecar, trace, sidecar_dir = _tail_fixture(tmp_path)
    before = responses.read_bytes()
    tower = FakeTower(sidecar_dir, fail=fail, partial=partial)
    with pytest.raises(RuntimeError, match="failed closed"):
        runner.run_generation_tail(
            tower,
            tier=2,
            repetition=1,
            questions=questions,
            responses_path=responses,
            sidecar_path=sidecar,
            judge_trace_path=trace,
            sidecar_dir=sidecar_dir,
            output_dir=tmp_path,
            published_dir=tmp_path,
            args=SimpleNamespace(api_url="http://127.0.0.1:8000"),
            watcher=object(),
        )
    assert tower.calls == 1
    assert responses.read_bytes() == before
    attempts = runner.V4.load_jsonl(tmp_path / "generation_tail_attempts.T2.r1.jsonl")
    assert attempts == [{**attempts[0], "outcome": "failed_closed"}]


@pytest.mark.parametrize(
    "malformed_success",
    ["zero_tokens", "result_error", "qid", "answer"],
)
def test_generation_tail_rejects_incoherent_success_sidecar(
    tmp_path: Path,
    monkeypatch,
    malformed_success: str,
) -> None:
    _patch_tail_runtime(monkeypatch)
    questions, responses, sidecar, trace, sidecar_dir = _tail_fixture(tmp_path)
    with pytest.raises(RuntimeError, match="failed closed"):
        runner.run_generation_tail(
            FakeTower(sidecar_dir, malformed_success=malformed_success),
            tier=2,
            repetition=1,
            questions=questions,
            responses_path=responses,
            sidecar_path=sidecar,
            judge_trace_path=trace,
            sidecar_dir=sidecar_dir,
            output_dir=tmp_path,
            published_dir=tmp_path,
            args=SimpleNamespace(api_url="http://127.0.0.1:8000"),
            watcher=object(),
        )


def test_merge_judge_trace_appends_missing_target_and_preserves_non_target_bytes(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "trace.jsonl"
    focused = tmp_path / "focused.jsonl"
    non_target = '{"fixed_vector_row":{"ordinal":2,"qid":"q2"},"outcome":"kept"}\n'.encode()
    trace.write_bytes(non_target)
    _jsonl(
        focused,
        [{"fixed_vector_row": {"ordinal": 0, "qid": "focused"}, "outcome": "retry"}],
    )
    runner._merge_judge_trace(
        trace,
        focused,
        tier=2,
        repetition=1,
        ordinal=5,
        qid="q5",
    )
    lines = trace.read_bytes().splitlines(keepends=True)
    assert lines[0] == non_target
    assert json.loads(lines[1])["fixed_vector_row"] == {
        "tier": 2,
        "repetition": 1,
        "ordinal": 5,
        "qid": "q5",
    }
    validator = _load_validator("e8_v5_validator_absent_trace_test")
    validator.validate_tail_trace_replacement(
        original_trace_lines=[non_target],
        final_trace_lines=lines,
        retry_traces={5: runner.V4.load_jsonl(focused)},
        target_ordinals={5},
        scoring_questions=[{"scoring_method": "exact_match"} for _ordinal in range(5)]
        + [{"scoring_method": "llm_judge"}],
        expected_qids=[f"q{ordinal}" for ordinal in range(6)],
        tier=2,
        repetition=1,
    )


def test_merge_judge_trace_replaces_existing_target_only(tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    focused = tmp_path / "focused.jsonl"
    old_target = '{"fixed_vector_row":{"ordinal":5,"qid":"q5"},"outcome":"old"}\n'.encode()
    non_target = '{"fixed_vector_row":{"ordinal":2,"qid":"q2"},"outcome":"kept"}\n'.encode()
    trace.write_bytes(old_target + non_target)
    _jsonl(
        focused,
        [{"fixed_vector_row": {"ordinal": 0, "qid": "focused"}, "outcome": "retry"}],
    )
    runner._merge_judge_trace(
        trace,
        focused,
        tier=2,
        repetition=1,
        ordinal=5,
        qid="q5",
    )
    lines = trace.read_bytes().splitlines(keepends=True)
    assert json.loads(lines[0])["outcome"] == "retry"
    assert lines[1] == non_target
    validator = _load_validator("e8_v5_validator_existing_trace_test")
    validator.validate_tail_trace_replacement(
        original_trace_lines=[old_target, non_target],
        final_trace_lines=lines,
        retry_traces={5: runner.V4.load_jsonl(focused)},
        target_ordinals={5},
        scoring_questions=[{"scoring_method": "exact_match"} for _ordinal in range(5)]
        + [{"scoring_method": "llm_judge"}],
        expected_qids=[f"q{ordinal}" for ordinal in range(6)],
        tier=2,
        repetition=1,
    )


def test_duplicate_target_judge_trace_is_rejected_by_runner_and_validator(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "trace.jsonl"
    focused = tmp_path / "focused.jsonl"
    duplicate = [
        {"fixed_vector_row": {"ordinal": 5, "qid": "q5"}, "outcome": "old-1"},
        {"fixed_vector_row": {"ordinal": 5, "qid": "q5"}, "outcome": "old-2"},
    ]
    _jsonl(trace, duplicate)
    _jsonl(
        focused,
        [{"fixed_vector_row": {"ordinal": 0, "qid": "focused"}, "outcome": "retry"}],
    )
    with pytest.raises(ValueError, match="not unique"):
        runner._merge_judge_trace(
            trace,
            focused,
            tier=2,
            repetition=1,
            ordinal=5,
            qid="q5",
        )
    validator = _load_validator("e8_v5_validator_duplicate_trace_test")
    with pytest.raises(ValueError, match="duplicate original"):
        validator.validate_tail_trace_replacement(
            original_trace_lines=trace.read_bytes().splitlines(keepends=True),
            final_trace_lines=trace.read_bytes().splitlines(keepends=True),
            retry_traces={5: runner.V4.load_jsonl(focused)},
            target_ordinals={5},
            scoring_questions=[{"scoring_method": "exact_match"} for _ordinal in range(5)]
            + [{"scoring_method": "llm_judge"}],
            expected_qids=[f"q{ordinal}" for ordinal in range(6)],
            tier=2,
            repetition=1,
        )


def test_validator_derives_scorer_tail_only_from_recovered_judge_history() -> None:
    validator = _load_validator("e8_v5_validator_scorer_derivation_test")
    recovered = {
        "schema": "epyc.e8_quality_llm_judge_trace.v2",
        "attempts": [
            {"error": {"type": "ScoringUnavailableError"}},
            {"error": None},
        ],
        "fixed_vector_row": {
            "tier": 1,
            "repetition": 2,
            "ordinal": 0,
            "qid": "q0",
        },
    }
    assert validator.derived_scorer_targets(
        pristine_trace_lines=[(json.dumps(recovered) + "\n").encode()],
        scoring_questions=[{"scoring_method": "llm_judge"}],
        expected_qids=["q0"],
        tier=1,
        repetition=2,
    ) == {0: "q0"}
    with pytest.raises(ValueError, match="recovered judge retry"):
        validator.derived_scorer_targets(
            pristine_trace_lines=[(json.dumps(recovered) + "\n").encode()],
            scoring_questions=[{"scoring_method": "exact_match"}],
            expected_qids=["q0"],
            tier=1,
            repetition=2,
        )


def test_scorer_tail_replaces_only_target_sidecar_line_and_preserves_batch_identity(
    tmp_path: Path,
) -> None:
    sidecar = tmp_path / "question_results.e8-t1-r1.jsonl"
    rows = _sidecar(["q0", "q1"], failure_ordinal=-1)
    rows[1]["result"].update(
        {
            "question_id": "q0",
            "error": True,
            "error_detail": "scoring_unavailable: judge timeout",
        }
    )
    _jsonl(sidecar, rows)
    responses = [_response("q0", "a"), _response("q1", "a")]
    before = sidecar.read_bytes().splitlines(keepends=True)
    replaced = runner.reconcile_scorer_tail_sidecar(
        sidecar,
        responses,
        [{"ordinal": 0, "qid": "q0", "outcome": "recovered"}],
    )
    after = sidecar.read_bytes().splitlines(keepends=True)
    assert replaced == [0]
    assert before[0] == after[0]
    assert before[2:] == after[2:]
    _parsed, indexed = runner.sidecar_question_rows(sidecar, expected_n=2)
    target = indexed[0][1]
    assert target["eval_batch_id"] == "full-batch"
    assert target["label"] == "e8-t2-r1"
    assert target["requested_n"] == 2
    assert target["result"]["question_id"] == "q0"
    assert runner.validate_clean_sidecar_result(responses[0], target, qid="q0")


def test_no_tail_repetition_does_not_rewrite_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    responses = tmp_path / "responses.T1.r1.jsonl"
    sidecar_dir = tmp_path / "eval_sidecars"
    sidecar = sidecar_dir / "question_results.e8-t1-r1.jsonl"
    trace = tmp_path / "judge_traces.T1.r1.jsonl"
    response_rows = [_response("q0", "a")]
    sidecar_rows = _sidecar(["q0"], failure_ordinal=-1)
    _jsonl(responses, response_rows)
    _jsonl(sidecar, sidecar_rows)
    _jsonl(trace, [])
    original_sidecar = sidecar.read_bytes()

    def fake_repetition(*_args, **_kwargs):
        return (
            {"q": 3.0},
            {
                "sidecar_sha256": runner.V4.sha256_path(sidecar),
                "scorer_tail_replay": [],
            },
        )

    monkeypatch.setattr(runner.V4, "run_repetition", fake_repetition)
    monkeypatch.setattr(
        runner,
        "run_generation_tail",
        lambda *_args, **_kwargs: {
            "schema": runner.TAIL_SCHEMA,
            "targets": [],
            "retry_count": 0,
        },
    )
    _observation, detail = runner.run_repetition_v5(
        object(),
        tier=1,
        repetition=1,
        questions=[{"qid": "q0"}],
        core_id="core",
        output_dir=tmp_path,
        expected_binding={},
        args=SimpleNamespace(),
        sidecar_dir=sidecar_dir,
        published_dir=tmp_path,
        watcher=object(),
    )
    assert sidecar.read_bytes() == original_sidecar
    pristine = detail["pristine_full_run"]
    pristine_sidecar = Path(pristine["artifacts"][sidecar.name]["path"])
    assert pristine_sidecar.read_bytes() == original_sidecar
    assert detail["scorer_sidecar_replacement_ordinals"] == []


def test_v5_cli_pins_tail_timeout_and_disallows_execute_mode() -> None:
    args = runner.parse_args(
        ["--collect-candidate", "--output-dir", "/tmp/v5", "--evaltower-timeout-s", "300"]
    )
    assert args.evaltower_timeout_s == 300
    with pytest.raises(SystemExit):
        runner.parse_args(
            ["--collect-candidate", "--output-dir", "/tmp/v5", "--evaltower-timeout-s", "301"]
        )
    with pytest.raises(SystemExit):
        runner.parse_args(["--execute", "--output-dir", "/tmp/v5"])


def test_v5_cli_separates_reviewed_source_from_live_runtime_paths() -> None:
    args = runner.parse_args(["--prepare"])
    runtime_root = PROJECT_ROOT
    assert args.state_path == runtime_root / "orchestration/autopilot_state.json"
    assert args.registry_path == runtime_root / "orchestration/model_registry.yaml"
    # 2026-08-01: model_registry_lean.yaml deleted; the lean registry IS the
    # compiled orchestration/model_registry.yaml.
    assert args.lean_registry_path == runtime_root / "orchestration/model_registry.yaml"
    assert args.lean_registry_path.exists()
    assert args.stack_priors_path == runtime_root / "orchestration/derived/stack_priors.yaml"
    assert args.orchestrator_state_path == runtime_root / "logs/orchestrator_state.json"
    assert args.journal_path == runtime_root / "orchestration/autopilot_journal.jsonl"
    assert args.runtime_facts_path == Path("/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json")
    assert runner.V4_PATH.is_relative_to(runner.PROJECT_ROOT)


def _synthetic_candidate(tmp_path: Path) -> Path:
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    validator_spec = importlib.util.spec_from_file_location(
        "e8_v5_validator_fixture", validator_path
    )
    assert validator_spec is not None and validator_spec.loader is not None
    validator = importlib.util.module_from_spec(validator_spec)
    sys.modules[validator_spec.name] = validator
    validator_spec.loader.exec_module(validator)
    root = tmp_path / "candidate"
    root.mkdir()
    details: dict[str, list[dict]] = {"1": [], "2": []}
    records = []
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
        vector = {
            "schema": "epyc.e8_quality_question_vector.v1",
            "era": "E8",
            "tier": tier,
            "core_id": f"core-{tier}",
            "seed": 42,
            "n": n,
            "dataset_sha256": "0" * 64,
            "per_suite_counts": {"suite": n},
            "questions": [{"qid": row["qid"]} for row in questions],
        }
        scoring = {
            "schema": "epyc.e8_quality_scoring_vector.v1",
            "era": "E8",
            "tier": tier,
            "core_id": f"core-{tier}",
            "seed": 42,
            "n": n,
            "dataset_sha256": "0" * 64,
            "questions": questions,
        }
        (root / f"question_vector.T{tier}.json").write_text(json.dumps(vector) + "\n")
        (root / f"scoring_vector.T{tier}.json").write_text(json.dumps(scoring) + "\n")
        observations = []
        for repetition in range(1, 4):
            responses = root / f"responses.T{tier}.r{repetition}.jsonl"
            sidecar = root / "eval_sidecars" / f"question_results.e8-t{tier}-r{repetition}.jsonl"
            trace = root / f"judge_traces.T{tier}.r{repetition}.jsonl"
            response_rows = [_response(row["qid"], "a") for row in questions]
            _jsonl(responses, response_rows)
            sidecar_rows = [{"row_type": "batch_start", "requested_n": n}]
            sidecar_rows.extend(
                {
                    "row_type": "question_result",
                    "ordinal": ordinal,
                    "answer": "a",
                    "complete": False,
                    "ended_at_s": 3.25,
                    "elapsed_s": 0.25,
                    "started_at_s": 3.0,
                    "result": {
                        "qid": row["qid"],
                        "question_id": row["qid"],
                        "correct": True,
                        "tokens_generated": 1,
                        "route": "frontdoor",
                        "answer_hash": runner._normalized_answer_hash("a"),
                    },
                }
                for ordinal, row in enumerate(questions)
            )
            sidecar_rows.append({"row_type": "batch_complete", "complete": True})
            _jsonl(sidecar, sidecar_rows)
            _jsonl(trace, [])
            pristine_sources = (responses, sidecar, trace)
            tail = {"schema": runner.TAIL_SCHEMA, "targets": [], "retry_count": 0}
            if tier == 1 and repetition == 1:
                original_dir = root / "generation_tail_original.T1.r1"
                original_response = original_dir / responses.name
                original_sidecar = original_dir / sidecar.name
                original_trace = original_dir / trace.name
                original_rows = list(response_rows)
                original_rows[0] = _response(
                    questions[0]["qid"],
                    "timed out",
                    error="timed out",
                )
                original_sidecars = json.loads(json.dumps(sidecar_rows))
                original_sidecars[1].update(
                    {
                        "answer": "timed out",
                        "result": {
                            "qid": questions[0]["qid"],
                            "question_id": questions[0]["qid"],
                            "tokens_generated": 0,
                            "error": True,
                            "error_detail": "timed out",
                        },
                    }
                )
                _jsonl(original_response, original_rows)
                _jsonl(original_sidecar, original_sidecars)
                _jsonl(original_trace, [])
                pristine_sources = (
                    original_response,
                    original_sidecar,
                    original_trace,
                )
                focused_sidecar = (
                    root / "eval_sidecars" / "question_results.e8-v5-tail-t1-r1-o0.jsonl"
                )
                focused_rows = [
                    {"row_type": "batch_start", "requested_n": 1},
                    {
                        "row_type": "question_result",
                        "ordinal": 0,
                        "answer": "a",
                        "complete": False,
                        "ended_at_s": 3.25,
                        "elapsed_s": 0.25,
                        "started_at_s": 3.0,
                        "result": {
                            "qid": questions[0]["qid"],
                            "question_id": questions[0]["qid"],
                            "correct": True,
                            "tokens_generated": 1,
                            "route": "frontdoor",
                            "answer_hash": runner._normalized_answer_hash("a"),
                        },
                    },
                    {"row_type": "batch_complete", "complete": True},
                ]
                _jsonl(focused_sidecar, focused_rows)
                focused_trace = root / "generation_tail_judge_traces" / "T1.r1.o0.jsonl"
                _jsonl(focused_trace, [])
                source = {
                    "ordinal": 0,
                    "qid": questions[0]["qid"],
                    "error": "timed out",
                    "response_sha256": runner.canonical_hash(original_rows[0]),
                    "sidecar_sha256": runner.canonical_hash(original_sidecars[1]),
                }
                target = {
                    **source,
                    "failure_fingerprint": runner.canonical_hash(source),
                }
                attempt_path = root / "generation_tail_attempts.T1.r1.jsonl"
                _jsonl(
                    attempt_path,
                    [
                        {
                            "schema": runner.TAIL_SCHEMA,
                            "tier": 1,
                            "repetition": 1,
                            "ordinal": 0,
                            "qid": questions[0]["qid"],
                            "failure_fingerprint": target["failure_fingerprint"],
                            "original_response_sha256": target["response_sha256"],
                            "original_sidecar_sha256": target["sidecar_sha256"],
                            "retry_response_sha256": runner.canonical_hash(response_rows[0]),
                            "retry_sidecar_sha256": runner.canonical_hash(focused_rows[1]),
                            "merged_sidecar_sha256": runner.canonical_hash(sidecar_rows[1]),
                            "retry_sidecar_path": str(focused_sidecar),
                            "retry_judge_trace_sha256": validator.sha256_path(focused_trace),
                            "retry_judge_trace_path": str(focused_trace),
                            "request_timeout_s": 300,
                            "concurrency": 1,
                            "scorer_tail_replay": [],
                            "outcome": "recovered",
                        }
                    ],
                )
                tail = {
                    "schema": runner.TAIL_SCHEMA,
                    "targets": [target],
                    "retry_count": 1,
                    "attempt_path": str(attempt_path),
                    "attempt_sha256": validator.sha256_path(attempt_path),
                    "original_artifact_dir": str(original_dir),
                    "scoring_audit": {"matches": True},
                }
            pristine_dir = root / f"pristine_full_run.T{tier}.r{repetition}"
            pristine_artifacts = {}
            for source, final_name in zip(
                pristine_sources,
                (responses.name, sidecar.name, trace.name),
            ):
                destination = pristine_dir / final_name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
                pristine_artifacts[final_name] = {
                    "path": str(destination),
                    "sha256": validator.sha256_path(destination),
                }
            pristine = {
                "schema": "epyc.e8_quality_pristine_full_run.v1",
                "path": str(pristine_dir),
                "artifacts": pristine_artifacts,
            }
            raw = root / f"raw.T{tier}.r{repetition}.json"
            raw_payload = {
                "q": 3.0,
                "ts": f"2026-07-27T00:00:0{repetition}Z",
                "core_id": f"core-{tier}",
                "protocol_id": runner.PROTOCOL_ID,
                "n": n,
                "era": "E8",
                "per_suite_quality": {"suite": 3.0},
                "per_suite_counts": {"suite": n},
            }
            raw.write_text(json.dumps(raw_payload) + "\n")
            observations.append(
                {
                    "path": str(raw),
                    "sha256": validator.sha256_path(raw),
                    "q": raw_payload["q"],
                    "ts": raw_payload["ts"],
                    "core_id": raw_payload["core_id"],
                    "protocol_id": runner.PROTOCOL_ID,
                    "n": n,
                    "era": "E8",
                }
            )
            details[str(tier)].append(
                {
                    "tier": tier,
                    "repetition": repetition,
                    "n_results": n,
                    "response_vector_matches_input": True,
                    "per_suite_counts_match_input": True,
                    "runtime_binding_matches_pre": True,
                    "all_routes_frontdoor": True,
                    "error_classification": {},
                    "scoring_audit": {"matches": True},
                    "scorer_tail_replay": [],
                    "scorer_sidecar_replacement_ordinals": [],
                    "response_path": str(responses),
                    "response_sha256": validator.sha256_path(responses),
                    "sidecar_path": str(sidecar),
                    "sidecar_sha256": validator.sha256_path(sidecar),
                    "judge_trace_path": str(trace),
                    "judge_trace_sha256": validator.sha256_path(trace),
                    "generation_tail": tail,
                    "pristine_full_run": pristine,
                }
            )
        summary = root / f"summary.T{tier}.json"
        summary.write_text(
            json.dumps(
                {
                    "tier": tier,
                    "core_id": f"core-{tier}",
                    "n": n,
                    "quality": 3.0,
                    "per_suite_quality": {"suite": 3.0},
                    "per_suite_counts": {"suite": n},
                    "era": "E8",
                    "decision_grade": True,
                    "observations": observations,
                    "question_vector_path": str(root / f"question_vector.T{tier}.json"),
                    "question_vector_sha256": validator.sha256_path(
                        root / f"question_vector.T{tier}.json"
                    ),
                    "scoring_vector_path": str(root / f"scoring_vector.T{tier}.json"),
                    "scoring_vector_sha256": validator.sha256_path(
                        root / f"scoring_vector.T{tier}.json"
                    ),
                    "response_artifacts": [],
                }
            )
            + "\n"
        )
        records.append(
            {
                "tier": tier,
                "path": str(summary),
                "sha256": validator.sha256_path(summary),
                "protocol_id": runner.PROTOCOL_ID,
                "core_id": f"core-{tier}",
                "n": n,
                "timestamp": observations[-1]["ts"],
                "era": "E8",
                "instrument": "dedicated_full_pool_tier_baseline",
                "quality": 3.0,
                "question_vector_sha256": runner.V4.vector_sha256(vector),
                "scoring_vector_sha256": runner.canonical_hash(scoring),
            }
        )
    proposal = root / "protocol_candidate.json"
    proposal.write_text(
        json.dumps(
            {
                "schema": runner.PROPOSAL_SCHEMA,
                "protocol": {
                    "protocol_id": runner.PROTOCOL_ID,
                    "generation_tail_contract": runner.GENERATION_TAIL_CONTRACT,
                },
            }
        )
        + "\n"
    )
    evidence = root / "e8_quality_baseline_evidence.json"
    runner_sha = validator.sha256_path(runner.RUNNER_PATH)
    evidence.write_text(
        json.dumps(
            {
                "schema": "epyc.e8_quality_baseline_evidence.v2",
                "eval_quality_era": "E8",
                "generation_tail_contract": runner.GENERATION_TAIL_CONTRACT,
                "runner": {"path": str(runner.RUNNER_PATH), "sha256": runner_sha},
                "protocol_candidate": {
                    "path": str(proposal),
                    "sha256": validator.sha256_path(proposal),
                },
                "source_records": records,
                "replacement": {
                    "baseline_state": {
                        "eval_quality_era": "E8",
                        "baselines_by_tier": {"1": 3.0, "2": 3.0},
                        "per_suite_quality_by_tier": {
                            "1": {"suite": 3.0},
                            "2": {"suite": 3.0},
                        },
                        "per_suite_counts_by_tier": {
                            "1": {"suite": 50},
                            "2": {"suite": 500},
                        },
                    },
                    "quality_history_by_tier": {
                        "1": [3.0, 3.0, 3.0],
                        "2": [3.0, 3.0, 3.0],
                    },
                    "quality_history_provenance_by_tier": {
                        str(tier): [
                            {
                                "q": 3.0,
                                "ts": f"2026-07-27T00:00:0{repetition}Z",
                                "era": "E8",
                                "core_id": f"core-{tier}",
                            }
                            for repetition in range(1, 4)
                        ]
                        for tier in (1, 2)
                    },
                },
                "run_seal_path": str(root / "run_seal.json"),
            }
        )
        + "\n"
    )
    watcher = root / "runtime_watch.jsonl"
    watcher_rows = [
        {
            "started_at": "2026-07-27T00:00:00Z",
            "finished_at": "2026-07-27T00:00:01Z",
            "ok": True,
        },
        {
            "started_at": "2026-07-27T00:00:05Z",
            "finished_at": "2026-07-27T00:00:06Z",
            "ok": True,
        },
    ]
    _jsonl(watcher, watcher_rows)
    report = root / "runner_report.json"
    report.write_text(
        json.dumps(
            {
                "mode": "executed",
                "protocol_id": runner.PROTOCOL_ID,
                "decision_grade": True,
                "observations": details,
                "postconditions": {
                    "checks": {name: True for name in validator.EXPECTED_CHECKS},
                    "watcher_samples": watcher_rows,
                    "watcher_path": str(watcher),
                    "watcher_sha256": validator.sha256_path(watcher),
                },
            }
        )
        + "\n"
    )
    bundle = {
        str(path): validator.sha256_path(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "run_seal.json"
    }
    seal = root / "run_seal.json"
    seal.write_text(
        json.dumps(
            {
                "schema": "epyc.e8_quality_baseline_run_seal.v1",
                "status": "complete",
                "manifest_sha256": validator.sha256_path(evidence),
                "runner_report_sha256": validator.sha256_path(report),
                "protocol_candidate_sha256": validator.sha256_path(proposal),
                "runner_sha256": runner_sha,
                "bundle_sha256": bundle,
            }
        )
        + "\n"
    )
    return evidence


def _load_validator(name: str):
    validator_path = PROJECT_ROOT / "scripts/benchmark/validate_e8_quality_baseline_v5.py"
    spec = importlib.util.spec_from_file_location(name, validator_path)
    assert spec is not None and spec.loader is not None
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    return validator


def _bind_synthetic_candidate_to_integrated_source(evidence: Path) -> Path:
    """Keep the sealed fixture synthetic while exercising the composite source root."""
    integrated_runner = INTEGRATED_E8_ROOT / "scripts/benchmark/run_e8_quality_baseline_v5.py"
    manifest = json.loads(evidence.read_text())
    manifest["runner"] = {"path": str(integrated_runner), "sha256": _sha(integrated_runner)}
    evidence.write_text(json.dumps(manifest) + "\n")
    seal_path = evidence.parent / "run_seal.json"
    seal = json.loads(seal_path.read_text())
    seal["manifest_sha256"] = _sha(evidence)
    seal["runner_sha256"] = _sha(integrated_runner)
    seal["bundle_sha256"] = {
        str(path): _sha(path)
        for path in sorted(evidence.parent.rglob("*"))
        if path.is_file() and path.name != "run_seal.json"
    }
    seal_path.write_text(json.dumps(seal) + "\n")
    return evidence


def _reseal_candidate(evidence: Path, validator) -> None:
    root = evidence.parent
    seal_path = root / "run_seal.json"
    seal = json.loads(seal_path.read_text())
    seal["manifest_sha256"] = validator.sha256_path(evidence)
    seal["runner_report_sha256"] = validator.sha256_path(root / "runner_report.json")
    seal["protocol_candidate_sha256"] = validator.sha256_path(root / "protocol_candidate.json")
    seal["bundle_sha256"] = {
        str(path): validator.sha256_path(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "run_seal.json"
    }
    seal_path.write_text(json.dumps(seal) + "\n")


def test_proposed_v5_validator_and_shell_replay_synthetic_bundle(tmp_path: Path) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_test")
    runner_sha = hashlib.sha256(runner.RUNNER_PATH.read_bytes()).hexdigest()
    base_runner_sha = hashlib.sha256(runner.V4_PATH.read_bytes()).hexdigest()
    assert (
        validator.validate(
            evidence,
            expected_runner_sha256=runner_sha,
            expected_base_runner_sha256=base_runner_sha,
        )["valid"]
        is True
    )
    wrapper = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/prepare_e8_quality_baseline_v5_candidate.sh"
    )
    _bind_synthetic_candidate_to_integrated_source(evidence)
    completed = subprocess.run(
        ["bash", str(wrapper), "--validate-evidence", str(evidence)],
        env={
            **__import__("os").environ,
            **_integrated_e8_pins(validator_wrapper=wrapper),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    unsealed_root = tmp_path / "unsealed"
    unsealed_root.mkdir()
    evidence = _synthetic_candidate(unsealed_root)
    (evidence.parent / "unsealed_tamper.txt").write_text("tampered\n")
    with pytest.raises(ValueError, match="exact artifact set"):
        validator.validate(
            evidence,
            expected_runner_sha256=runner_sha,
            expected_base_runner_sha256=base_runner_sha,
        )


def test_validator_rejects_failed_watcher_even_when_bundle_is_resealed(
    tmp_path: Path,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_watcher_test")
    report_path = evidence.parent / "runner_report.json"
    report = json.loads(report_path.read_text())
    report["postconditions"]["watcher_samples"][0]["ok"] = False
    watcher_path = evidence.parent / "runtime_watch.jsonl"
    _jsonl(watcher_path, report["postconditions"]["watcher_samples"])
    report["postconditions"]["watcher_sha256"] = validator.sha256_path(watcher_path)
    report_path.write_text(json.dumps(report) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="clean decision-grade"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_unreviewed_base_runner_pin(tmp_path: Path) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_base_pin_test")
    with pytest.raises(ValueError, match="base runner differs"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256="0" * 64,
        )


def test_validator_rejects_resealed_incoherent_sidecar(tmp_path: Path) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_sidecar_test")
    sidecar_path = evidence.parent / "eval_sidecars/question_results.e8-t1-r2.jsonl"
    sidecar_rows = runner.V4.load_jsonl(sidecar_path)
    sidecar_rows[1]["result"]["tokens_generated"] = 0
    _jsonl(sidecar_path, sidecar_rows)
    report_path = evidence.parent / "runner_report.json"
    report = json.loads(report_path.read_text())
    report["observations"]["1"][1]["sidecar_sha256"] = validator.sha256_path(sidecar_path)
    report_path.write_text(json.dumps(report) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="not coherent"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


@pytest.mark.parametrize("field", ["q", "per_suite_quality", "per_suite_counts"])
def test_validator_recomputes_raw_aggregates_from_response_ledgers(
    tmp_path: Path,
    field: str,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator(f"e8_v5_validator_raw_{field}_test")
    summary_path = evidence.parent / "summary.T1.json"
    summary = json.loads(summary_path.read_text())
    repetitions = range(1, 4) if field == "per_suite_counts" else (1,)
    for repetition in repetitions:
        raw_path = evidence.parent / f"raw.T1.r{repetition}.json"
        raw = json.loads(raw_path.read_text())
        if field == "q":
            raw["q"] = 0.0
            summary["observations"][repetition - 1]["q"] = 0.0
        elif field == "per_suite_quality":
            raw["per_suite_quality"] = {"suite": 0.0}
        else:
            raw["per_suite_counts"] = {"suite": 51}
        raw_path.write_text(json.dumps(raw) + "\n")
        summary["observations"][repetition - 1]["sha256"] = validator.sha256_path(
            raw_path
        )
    if field == "per_suite_counts":
        summary["per_suite_counts"] = {"suite": 51}
    summary_path.write_text(json.dumps(summary) + "\n")
    manifest = json.loads(evidence.read_text())
    manifest["source_records"][0]["sha256"] = validator.sha256_path(summary_path)
    if field == "per_suite_counts":
        manifest["replacement"]["baseline_state"]["per_suite_counts_by_tier"]["1"] = {
            "suite": 51
        }
    evidence.write_text(json.dumps(manifest) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="raw observation differs"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_response_suite_not_bound_to_fixed_vector(
    tmp_path: Path,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_fixed_suite_test")
    root = evidence.parent
    response_path = root / "responses.T1.r1.jsonl"
    pristine_path = root / "pristine_full_run.T1.r1" / response_path.name
    responses = runner.V4.load_jsonl(response_path)
    responses[0]["suite"] = ""
    _jsonl(response_path, responses)
    pristine_path.write_bytes(response_path.read_bytes())
    report_path = root / "runner_report.json"
    report = json.loads(report_path.read_text())
    detail = report["observations"]["1"][0]
    detail["response_sha256"] = validator.sha256_path(response_path)
    detail["pristine_full_run"]["artifacts"][response_path.name]["sha256"] = (
        validator.sha256_path(pristine_path)
    )
    report_path.write_text(json.dumps(report) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="fixed scoring vector"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


@pytest.mark.parametrize("timestamp", ["not-a-timestamp", "2026-07-01T00:00:00Z"])
def test_validator_rejects_malformed_or_pre_e8_raw_timestamp(
    tmp_path: Path,
    timestamp: str,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator(
        f"e8_v5_validator_raw_timestamp_{timestamp[:3]}_test"
    )
    root = evidence.parent
    raw_path = root / "raw.T1.r1.json"
    raw = json.loads(raw_path.read_text())
    raw["ts"] = timestamp
    raw_path.write_text(json.dumps(raw) + "\n")
    summary_path = root / "summary.T1.json"
    summary = json.loads(summary_path.read_text())
    summary["observations"][0]["ts"] = timestamp
    summary["observations"][0]["sha256"] = validator.sha256_path(raw_path)
    summary_path.write_text(json.dumps(summary) + "\n")
    manifest = json.loads(evidence.read_text())
    manifest["source_records"][0]["sha256"] = validator.sha256_path(summary_path)
    evidence.write_text(json.dumps(manifest) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="timestamp"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_external_symlink_in_sealed_tree(tmp_path: Path) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_external_symlink_test")
    external = tmp_path / "external.json"
    external.write_text("{}\n")
    (evidence.parent / "external-alias.json").symlink_to(external)
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="symlink"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_durable_abort_marker(tmp_path: Path) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_abort_marker_test")
    runner.V4.write_json(
        evidence.parent / runner.ABORT_MARKER_NAME,
        {
            "schema": runner.ABORT_SCHEMA,
            "status": "aborted",
            "writer": "fault_injection",
        },
    )
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="abort marker"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_same_basename_raw_outside_evidence_root_level(
    tmp_path: Path,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_nested_raw_test")
    source = evidence.parent / "raw.T1.r1.json"
    nested = evidence.parent / "nested/raw.T1.r1.json"
    nested.parent.mkdir()
    nested.write_bytes(source.read_bytes())
    summary_path = evidence.parent / "summary.T1.json"
    summary = json.loads(summary_path.read_text())
    summary["observations"][0]["path"] = str(nested)
    summary["observations"][0]["sha256"] = validator.sha256_path(nested)
    summary_path.write_text(json.dumps(summary) + "\n")
    manifest = json.loads(evidence.read_text())
    manifest["source_records"][0]["sha256"] = validator.sha256_path(summary_path)
    evidence.write_text(json.dumps(manifest) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="raw observation differs"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_forged_scorer_allowlist_and_question_identity(
    tmp_path: Path,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_forged_scorer_test")
    sidecar_path = evidence.parent / "eval_sidecars/question_results.e8-t1-r2.jsonl"
    sidecar_rows = runner.V4.load_jsonl(sidecar_path)
    sidecar_rows[1]["result"]["question_id"] = "forged-source-id"
    _jsonl(sidecar_path, sidecar_rows)
    report_path = evidence.parent / "runner_report.json"
    report = json.loads(report_path.read_text())
    detail = report["observations"]["1"][1]
    detail["scorer_tail_replay"] = [
        {"ordinal": 0, "qid": "t1-0", "outcome": "recovered"}
    ]
    detail["scorer_sidecar_replacement_ordinals"] = [0]
    detail["sidecar_sha256"] = validator.sha256_path(sidecar_path)
    report_path.write_text(json.dumps(report) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="not derived from pristine traces"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_validator_rejects_extra_generation_target_row_mutation(
    tmp_path: Path,
) -> None:
    evidence = _synthetic_candidate(tmp_path)
    validator = _load_validator("e8_v5_validator_generation_row_test")
    sidecar_path = evidence.parent / "eval_sidecars/question_results.e8-t1-r1.jsonl"
    sidecar_rows = runner.V4.load_jsonl(sidecar_path)
    sidecar_rows[1]["unexpected_mutation"] = "accepted-before-exact-reconstruction"
    _jsonl(sidecar_path, sidecar_rows)
    attempt_path = evidence.parent / "generation_tail_attempts.T1.r1.jsonl"
    attempts = runner.V4.load_jsonl(attempt_path)
    attempts[0]["merged_sidecar_sha256"] = runner.canonical_hash(sidecar_rows[1])
    _jsonl(attempt_path, attempts)
    report_path = evidence.parent / "runner_report.json"
    report = json.loads(report_path.read_text())
    detail = report["observations"]["1"][0]
    detail["sidecar_sha256"] = validator.sha256_path(sidecar_path)
    detail["generation_tail"]["attempt_sha256"] = validator.sha256_path(attempt_path)
    report_path.write_text(json.dumps(report) + "\n")
    _reseal_candidate(evidence, validator)
    with pytest.raises(ValueError, match="not the exact reconstruction"):
        validator.validate(
            evidence,
            expected_runner_sha256=validator.sha256_path(runner.RUNNER_PATH),
            expected_base_runner_sha256=validator.sha256_path(runner.V4_PATH),
        )


def test_collect_wrapper_refuses_bad_runner_pin_without_creating_output(
    tmp_path: Path,
) -> None:
    wrapper = (
        PROJECT_ROOT / "scripts/benchmark/operator_candidates/collect_e8_quality_baseline_v5.sh"
    )
    output = tmp_path / "must-not-exist"
    completed = subprocess.run(
        ["bash", str(wrapper), "--output-dir", str(output)],
        env={
            **__import__("os").environ,
            "E8_V5_SOURCE_ROOT": str(PROJECT_ROOT),
            "E8_V5_COLLECT_WRAPPER_SHA256": hashlib.sha256(wrapper.read_bytes()).hexdigest(),
            "E8_V5_RUNNER_SHA256": "0" * 64,
            "E8_V5_BASE_RUNNER_SHA256": hashlib.sha256(runner.V4_PATH.read_bytes()).hexdigest(),
            "E8_V5_ORCHESTRATOR_HEAD": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
            ).strip(),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "externally reviewed hash" in completed.stderr
    assert not output.exists()


def test_v5_applier_adapter_plan_is_read_only(tmp_path: Path) -> None:
    adapter = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
    )
    paths = [tmp_path / name for name in ("state", "evidence", "validator", "tx", "attest")]
    completed = subprocess.run(
        [
            "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python",
            str(adapter),
            "--state",
            str(paths[0]),
            "--evidence",
            str(paths[1]),
            "--canonical-evidence",
            str(paths[1]),
            "--validator",
            str(paths[2]),
            "--transaction-dir",
            str(paths[3]),
            "--attestation",
            str(paths[4]),
            "--plan",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "E8 baseline-state apply plan" in completed.stdout
    assert all(not path.exists() for path in paths)


def test_final_wrapper_prevalidates_exact_transaction_without_writes(
    tmp_path: Path,
) -> None:
    # The reviewed transaction is computed against a DERIVED E7 pre-state in a
    # sandbox: the live production state is no longer a valid one-shot E7 -> E8
    # pre-state (see _e7_pre_state).  The canonical production state, the canonical
    # operator root, and the canonical apply lock must all still come out untouched.
    wrapper, env, state, sandbox_root, evidence, pre_sha, candidate_sha = (
        _v5_wrapper_integration_fixture(tmp_path)
    )
    state_bytes = state.read_bytes()
    canonical_state_bytes = CANONICAL_STATE_PATH.read_bytes()
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    operator_root = Path("/mnt/raid0/llm/epyc-root/artifacts/operator")
    before_outputs = set(operator_root.glob(f"*{evidence_sha}*"))
    lock_path = Path("/mnt/raid0/llm/tmp/e8-quality-baseline-v5-apply.lock")
    lock_before = (
        (
            lock_path.stat().st_ino,
            lock_path.stat().st_size,
            lock_path.stat().st_mtime_ns,
            lock_path.read_bytes(),
        )
        if lock_path.exists()
        else None
    )
    completed = subprocess.run(
        _v5_wrapper_command(wrapper, "--prevalidate", evidence, pre_sha, candidate_sha),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "prevalidation passed" in completed.stdout
    # The printed review IS the exact transaction the human binds: the reviewed
    # hashes and precisely the applier's own six state-review rows.
    canonical = _canonical_applier_module("e8_v5_applier_prevalidation_test")
    # stdout is the sealed validator's own report, then the retained review, then
    # the human-readable trailer; the review is the last JSON document printed.
    printed = completed.stdout.split("E8 v5 prevalidation passed")[0]
    decoder = json.JSONDecoder()
    review = None
    offset = 0
    while (offset := printed.find("{", offset)) != -1:
        review, end = decoder.raw_decode(printed, offset)
        offset = end
    assert review is not None
    assert review["pre_state_sha256"] == pre_sha
    assert review["candidate_state_sha256"] == candidate_sha
    assert [row["path"] for row in review["exact_state_diff"]] == [
        "/" + "/".join(path) for path in canonical.STATE_REVIEW_PATHS
    ]
    assert state.read_bytes() == state_bytes
    assert set((sandbox_root / "artifacts/operator").iterdir()) == set()
    assert CANONICAL_STATE_PATH.read_bytes() == canonical_state_bytes
    assert set(operator_root.glob(f"*{evidence_sha}*")) == before_outputs
    lock_after = (
        (
            lock_path.stat().st_ino,
            lock_path.stat().st_size,
            lock_path.stat().st_mtime_ns,
            lock_path.read_bytes(),
        )
        if lock_path.exists()
        else None
    )
    assert lock_after == lock_before

    bad_env = {**env, "E8_V5_FINAL_C1_VALIDATOR_SHA256": "0" * 64}
    rejected = subprocess.run(
        _v5_wrapper_command(wrapper, "--prevalidate", evidence, pre_sha, candidate_sha),
        env=bad_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode != 0
    assert "E8_V5_FINAL_C1_VALIDATOR_SHA256" in rejected.stderr
    assert state.read_bytes() == state_bytes
    assert set((sandbox_root / "artifacts/operator").iterdir()) == set()
    assert CANONICAL_STATE_PATH.read_bytes() == canonical_state_bytes
    assert set(operator_root.glob(f"*{evidence_sha}*")) == before_outputs


def test_final_wrapper_uses_dynamic_confirmation_and_post_commit_receipt_only() -> None:
    """The human boundary cannot be satisfied by a reusable static token."""
    wrapper = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
    )
    source = wrapper.read_text()
    assert "--apply" in source
    assert '[[ -t 0 && -t 1 ]]' in source
    assert 'CONFIRMATION="APPLY-E8-V5:${EVIDENCE_SHA256}:${EXPECTED_CANDIDATE}"' in source
    assert "PROTOCOL_RECEIPT" not in source
    assert "canonical.write_json_create_only(receipt_path, payload)" in source
    assert source.index('"${COMMON[@]}" --attest "$CONFIRMATION"') < source.index(
        "canonical.write_json_create_only(receipt_path, payload)"
    )
    assert source.index('"${COMMON[@]}" --attest "$CONFIRMATION"') < source.index(
        "E8 v5 state CAS committed and consolidated receipt created"
    )


def test_final_wrapper_prevalidation_rejects_stale_reviewed_hashes_without_writes(
    tmp_path: Path,
) -> None:
    # The state under review must be a VALID E7 pre-state, otherwise the wrapper
    # refuses at the precondition and never reaches the reviewed-hash comparison
    # this test exists to cover.
    wrapper, env, state, sandbox_root, evidence, _pre_sha, _candidate_sha = (
        _v5_wrapper_integration_fixture(tmp_path)
    )
    state_before = state.read_bytes()
    canonical_state_before = CANONICAL_STATE_PATH.read_bytes()
    completed = subprocess.run(
        [
            "bash", str(wrapper), "--prevalidate", "--evidence", str(evidence),
            "--expected-pre-state-sha256", "0" * 64,
            "--expected-candidate-state-sha256", "1" * 64,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "reviewed pre-state" in completed.stderr
    assert state.read_bytes() == state_before
    assert set((sandbox_root / "artifacts/operator").iterdir()) == set()
    assert CANONICAL_STATE_PATH.read_bytes() == canonical_state_before


def _v5_wrapper_integration_fixture(tmp_path: Path) -> tuple[Path, dict[str, str], Path, Path, Path, str, str]:
    """Build a full sealed transaction against a temporary state/artifact root."""
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    evidence = _bind_synthetic_candidate_to_integrated_source(_synthetic_candidate(evidence_root))
    wrapper = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
    )
    validator_shell = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/prepare_e8_quality_baseline_v5_candidate.sh"
    )
    adapter = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
    )
    canonical_applier = Path(
        "/mnt/raid0/llm/epyc-root/artifacts/operator/apply_e8_quality_baseline_state.py"
    )
    adapter_spec = importlib.util.spec_from_file_location(
        f"e8_v5_integration_adapter_{tmp_path.name}", adapter
    )
    assert adapter_spec is not None and adapter_spec.loader is not None
    adapter_module = importlib.util.module_from_spec(adapter_spec)
    sys.modules[adapter_spec.name] = adapter_module
    adapter_spec.loader.exec_module(adapter_module)
    canonical = adapter_module.module

    state = tmp_path / "state.json"
    state.write_bytes(_e7_pre_state_bytes(canonical))
    manifest = json.loads(evidence.read_text())
    candidate = canonical.candidate_state(json.loads(state.read_text()), manifest["replacement"])
    candidate_bytes = (json.dumps(candidate, indent=2, sort_keys=True) + "\n").encode()
    pre_sha = hashlib.sha256(state.read_bytes()).hexdigest()
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    operator_root = tmp_path / "operator-root"
    (operator_root / "artifacts/operator").mkdir(parents=True)
    env = {
        **__import__("os").environ,
        **_integrated_e8_pins(wrapper=wrapper, validator_wrapper=validator_shell),
        "E8_V5_OPERATOR_ROOT": str(operator_root),
        "E8_V5_STATE": str(state),
        "E8_V5_LOCK_PATH": str(tmp_path / "apply.lock"),
        "E8_V5_TRUST_LOCK": str(tmp_path / "measurement-trust.lock"),
        "E8_V5_TEST_MODE": "1",
        "E8_V5_TEST_AUTO_CONFIRM": "1",
        "E8_V5_APPLIER_SHA256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        "E8_V5_CANONICAL_APPLIER_SHA256": hashlib.sha256(canonical_applier.read_bytes()).hexdigest(),
    }
    return wrapper, env, state, operator_root, evidence, pre_sha, candidate_sha


def _v5_wrapper_command(
    wrapper: Path, mode: str, evidence: Path, pre_sha: str, candidate_sha: str
) -> list[str]:
    return [
        "bash", str(wrapper), mode, "--evidence", str(evidence),
        "--expected-pre-state-sha256", pre_sha,
        "--expected-candidate-state-sha256", candidate_sha,
    ]


def test_final_wrapper_integration_commits_temp_state_then_creates_bound_receipt(
    tmp_path: Path,
) -> None:
    wrapper, env, state, root, evidence, pre_sha, candidate_sha = _v5_wrapper_integration_fixture(tmp_path)
    completed = subprocess.run(
        _v5_wrapper_command(wrapper, "--apply", evidence, pre_sha, candidate_sha),
        env=env, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    receipt = root / f"artifacts/operator/e8_quality_baseline_state_v5_{evidence_sha}.consolidated_receipt.json"
    value = json.loads(receipt.read_text())
    assert hashlib.sha256(state.read_bytes()).hexdigest() == candidate_sha
    assert value["state_review"]["pre_state_sha256"] == pre_sha
    assert value["state_review"]["candidate_state_sha256"] == candidate_sha
    assert len(value["state_review"]["exact_state_diff"]) == 6
    benchmark = PROJECT_ROOT / "scripts/benchmark"
    for key, filename in {
        "successor_runner": "prepare_e8_quality_baseline_v5_partial_r2_successor.py",
        "race_retry_runner": "prepare_e8_quality_baseline_v5_partial_r2_race_retry.py",
        "mixed_tail_repair_runner": "prepare_e8_quality_baseline_v5_partial_r2_mixed_tail_repair.py",
        "terminalizer_runner": "terminalize_e8_quality_baseline_v5_partial_r2_successor.py",
        "final_c1_retry_runner": "final_c1_retry.py",
        "final_c1_validator": "final_c1_validator.py",
    }.items():
        assert value["code_sha256"][key] == _sha(benchmark / filename)
    assert value["transaction"]["canonical_attestation_path"].endswith(
        "canonical_apply_attestation.json"
    )


def test_final_wrapper_shared_trust_lock_blocks_before_transaction(
    tmp_path: Path,
) -> None:
    wrapper, env, state, root, evidence, pre_sha, candidate_sha = _v5_wrapper_integration_fixture(
        tmp_path
    )
    trust_lock = Path(env["E8_V5_TRUST_LOCK"])
    trust_lock.touch()
    before_state = state.read_bytes()
    before_outputs = set((root / "artifacts/operator").iterdir())
    with trust_lock.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = subprocess.run(
            _v5_wrapper_command(
                wrapper, "--prevalidate", evidence, pre_sha, candidate_sha
            ),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    assert blocked.returncode != 0
    assert "measurement trust-boundary lock is already held" in blocked.stderr
    assert state.read_bytes() == before_state
    assert set((root / "artifacts/operator").iterdir()) == before_outputs


def test_v5_direct_applier_honors_shared_and_inherited_trust_lock(
    tmp_path: Path,
) -> None:
    adapter = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
    )
    trust_lock = tmp_path / "measurement-trust.lock"
    trust_lock.touch()
    env = {
        **__import__("os").environ,
        "E8_V5_TRUST_LOCK": str(trust_lock),
        "E8_V5_TEST_MODE": "1",
    }
    with trust_lock.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = subprocess.run(
            [sys.executable, str(adapter), "--plan"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        inherited_env = {**env, "EPYC_MEASUREMENT_TRUST_LOCK_FD": str(handle.fileno())}
        inherited = subprocess.run(
            [
                sys.executable,
                str(adapter),
                "--state",
                str(tmp_path / "state"),
                "--evidence",
                str(tmp_path / "evidence"),
                "--canonical-evidence",
                str(tmp_path / "evidence"),
                "--validator",
                str(tmp_path / "validator"),
                "--transaction-dir",
                str(tmp_path / "transaction"),
                "--attestation",
                str(tmp_path / "attestation"),
                "--plan",
            ],
            env=inherited_env,
            pass_fds=(handle.fileno(),),
            capture_output=True,
            text=True,
            check=False,
        )
    assert blocked.returncode != 0
    assert "measurement trust-boundary lock is already held" in blocked.stderr
    assert inherited.returncode == 0, inherited.stderr
    assert "E8 baseline-state apply plan" in inherited.stdout


def test_final_wrapper_integration_apply_failure_rolls_back_without_receipt(
    tmp_path: Path,
) -> None:
    wrapper, env, state, root, evidence, pre_sha, candidate_sha = _v5_wrapper_integration_fixture(tmp_path)
    before = state.read_bytes()
    lifecycle_lock = state.parent / ".autopilot.lock"
    with lifecycle_lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed = subprocess.run(
            _v5_wrapper_command(wrapper, "--apply", evidence, pre_sha, candidate_sha),
            env=env, capture_output=True, text=True, check=False,
        )
    assert completed.returncode != 0
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert state.read_bytes() == before
    review = root / f"artifacts/operator/e8_quality_baseline_state_v5_{evidence_sha}.six_row_review.json"
    assert not review.exists()
    assert not (
        root / f"artifacts/operator/e8_quality_baseline_state_v5_{evidence_sha}.consolidated_receipt.json"
    ).exists()
    retry = subprocess.run(
        _v5_wrapper_command(wrapper, "--apply", evidence, pre_sha, candidate_sha),
        env=env, capture_output=True, text=True, check=False,
    )
    assert retry.returncode == 0, retry.stderr
    assert hashlib.sha256(state.read_bytes()).hexdigest() == candidate_sha


def test_final_wrapper_integration_recovers_only_missing_post_commit_receipt(
    tmp_path: Path,
) -> None:
    wrapper, env, state, root, evidence, pre_sha, candidate_sha = _v5_wrapper_integration_fixture(tmp_path)
    committed = subprocess.run(
        _v5_wrapper_command(wrapper, "--apply", evidence, pre_sha, candidate_sha),
        env=env, capture_output=True, text=True, check=False,
    )
    assert committed.returncode == 0, committed.stderr
    assert hashlib.sha256(state.read_bytes()).hexdigest() == candidate_sha
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    receipt = root / f"artifacts/operator/e8_quality_baseline_state_v5_{evidence_sha}.consolidated_receipt.json"
    assert receipt.exists()
    receipt.unlink()  # Simulate only the post-commit external receipt loss.
    lifecycle_lock = state.parent / ".autopilot.lock"
    with lifecycle_lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = subprocess.run(
            _v5_wrapper_command(wrapper, "--finalize-receipt", evidence, pre_sha, candidate_sha),
            env=env, capture_output=True, text=True, check=False,
        )
    assert locked.returncode != 0
    assert "lifecycle/state lock is held" in locked.stderr
    assert not receipt.exists()
    stale = subprocess.run(
        _v5_wrapper_command(wrapper, "--finalize-receipt", evidence, pre_sha, "0" * 64),
        env=env, capture_output=True, text=True, check=False,
    )
    assert stale.returncode != 0
    assert "retained review candidate differs" in stale.stderr
    assert not receipt.exists()
    repaired = subprocess.run(
        _v5_wrapper_command(wrapper, "--finalize-receipt", evidence, pre_sha, candidate_sha),
        env=env, capture_output=True, text=True, check=False,
    )
    assert repaired.returncode == 0, repaired.stderr
    first = receipt.read_bytes()
    duplicate = subprocess.run(
        _v5_wrapper_command(wrapper, "--finalize-receipt", evidence, pre_sha, candidate_sha),
        env=env, capture_output=True, text=True, check=False,
    )
    assert duplicate.returncode != 0
    assert "consolidated receipt already exists" in duplicate.stderr
    assert receipt.read_bytes() == first
    receipt.write_text('{"conflicting": true}\n')
    conflicting = subprocess.run(
        _v5_wrapper_command(wrapper, "--finalize-receipt", evidence, pre_sha, candidate_sha),
        env=env, capture_output=True, text=True, check=False,
    )
    assert conflicting.returncode != 0
    assert "consolidated receipt already exists" in conflicting.stderr
    assert receipt.read_text() == '{"conflicting": true}\n'


def test_final_wrapper_fake_pytest_flags_cannot_bypass_tty_on_canonical_paths(
    tmp_path: Path,
) -> None:
    """Forged pytest markers must never let --apply write on canonical paths.

    ``E8_V5_TEST_AUTO_CONFIRM`` is only honoured when TEST_SANDBOX==1, i.e. when all
    four sandbox overrides are set and resolve below /tmp.  With canonical paths the
    wrapper must therefore refuse and leave the production state, the canonical
    operator root, and the canonical apply lock untouched — the first half below.
    The wrapper runs the (state-dependent) six-row review BEFORE the TTY gate, so on
    canonical paths the refusal now lands at the E7 pre-state precondition rather
    than at the TTY prompt; the second half drives the TTY gate directly on sandbox
    paths so the gate itself stays covered.
    """
    wrapper = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
    )
    validator_shell = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/prepare_e8_quality_baseline_v5_candidate.sh"
    )
    adapter = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
    )
    canonical_applier = Path(
        "/mnt/raid0/llm/epyc-root/artifacts/operator/apply_e8_quality_baseline_state.py"
    )
    canonical = _canonical_applier_module("e8_v5_canonical_tty_adapter")
    evidence_root = tmp_path / "canonical-evidence"
    evidence_root.mkdir()
    evidence = _bind_synthetic_candidate_to_integrated_source(
        _synthetic_candidate(evidence_root)
    )
    state_before = CANONICAL_STATE_PATH.read_bytes()
    # A genuinely well-formed transaction binding: the true live pre-state hash and
    # a real candidate hash for this sealed evidence, so nothing but the canonical
    # paths distinguishes this attempt from an authorised one.
    candidate = canonical.candidate_state(
        _e7_pre_state(canonical), json.loads(evidence.read_text())["replacement"]
    )
    candidate_sha = hashlib.sha256(
        (json.dumps(candidate, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    operator_root = Path("/mnt/raid0/llm/epyc-root/artifacts/operator")
    before_outputs = set(operator_root.glob(f"*{evidence_sha}*"))
    lock_path = Path("/mnt/raid0/llm/tmp/e8-quality-baseline-v5-apply.lock")
    lock_before = (
        (lock_path.stat().st_ino, lock_path.stat().st_mtime_ns, lock_path.read_bytes())
        if lock_path.exists()
        else None
    )
    completed = subprocess.run(
        _v5_wrapper_command(
            wrapper,
            "--apply",
            evidence,
            hashlib.sha256(state_before).hexdigest(),
            candidate_sha,
        ),
        env={
            **__import__("os").environ,
            **_integrated_e8_pins(wrapper=wrapper, validator_wrapper=validator_shell),
            "E8_V5_TEST_MODE": "1",
            "E8_V5_TEST_AUTO_CONFIRM": "1",
            "PYTEST_CURRENT_TEST": "forged",
            "E8_V5_APPLIER_SHA256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            "E8_V5_CANONICAL_APPLIER_SHA256": hashlib.sha256(canonical_applier.read_bytes()).hexdigest(),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert CANONICAL_STATE_PATH.read_bytes() == state_before
    assert set(operator_root.glob(f"*{evidence_sha}*")) == before_outputs
    lock_after = (
        (lock_path.stat().st_ino, lock_path.stat().st_mtime_ns, lock_path.read_bytes())
        if lock_path.exists()
        else None
    )
    assert lock_after == lock_before

    # The TTY gate itself, reached on sandbox paths through the receipt-recovery
    # branch.  Without E8_V5_TEST_AUTO_CONFIRM the wrapper must demand an
    # interactive terminal; with it, the gate is passed and the run fails later, on
    # the retained-review checks.
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    sandbox_root = sandbox / "operator-root"
    sandbox_operator = sandbox_root / "artifacts/operator"
    sandbox_operator.mkdir(parents=True)
    sandbox_state = sandbox / "state.json"
    sandbox_state.write_bytes(_e7_pre_state_bytes(canonical))
    transaction = sandbox_operator / f"e8_quality_baseline_state_v5_{evidence_sha}.transaction"
    transaction.mkdir()
    (transaction / "canonical_apply_attestation.json").write_text("{}\n")
    (
        sandbox_operator / f"e8_quality_baseline_state_v5_{evidence_sha}.six_row_review.json"
    ).write_text("{}\n")
    receipt = (
        sandbox_operator
        / f"e8_quality_baseline_state_v5_{evidence_sha}.consolidated_receipt.json"
    )
    sandbox_env = {
        **__import__("os").environ,
        **_integrated_e8_pins(wrapper=wrapper, validator_wrapper=validator_shell),
        "E8_V5_OPERATOR_ROOT": str(sandbox_root),
        "E8_V5_STATE": str(sandbox_state),
        "E8_V5_LOCK_PATH": str(sandbox / "apply.lock"),
        "E8_V5_TRUST_LOCK": str(sandbox / "measurement-trust.lock"),
        "E8_V5_TEST_MODE": "1",
        "E8_V5_APPLIER_SHA256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        "E8_V5_CANONICAL_APPLIER_SHA256": hashlib.sha256(canonical_applier.read_bytes()).hexdigest(),
    }
    sandbox_env.pop("E8_V5_TEST_AUTO_CONFIRM", None)
    without_tty = subprocess.run(
        _v5_wrapper_command(
            wrapper, "--finalize-receipt", evidence, "0" * 64, candidate_sha
        ),
        env=sandbox_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert without_tty.returncode != 0
    assert "apply requires an interactive terminal confirmation" in without_tty.stderr
    assert not receipt.exists()
    passed_gate = subprocess.run(
        _v5_wrapper_command(
            wrapper, "--finalize-receipt", evidence, "0" * 64, candidate_sha
        ),
        env={**sandbox_env, "E8_V5_TEST_AUTO_CONFIRM": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert passed_gate.returncode != 0
    assert "interactive terminal confirmation" not in passed_gate.stderr
    assert not receipt.exists()
    assert CANONICAL_STATE_PATH.read_bytes() == state_before


def test_final_wrapper_rejects_symlinked_test_sandbox_state_escape(tmp_path: Path) -> None:
    wrapper = (
        PROJECT_ROOT
        / "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
    )
    root = tmp_path / "operator-root"
    root.mkdir()
    # The live AutoPilot state is gitignored and exists only in the main
    # checkout; anchoring it on PROJECT_ROOT made this test fail in any worktree.
    canonical_state = CANONICAL_STATE_PATH
    state_link = tmp_path / "state.json"
    state_link.symlink_to(canonical_state)
    lock = tmp_path / "apply.lock"
    before = canonical_state.read_bytes()
    completed = subprocess.run(
        ["bash", str(wrapper), "--prevalidate"],
        env={
            **__import__("os").environ,
            "E8_V5_OPERATOR_ROOT": str(root),
            "E8_V5_STATE": str(state_link),
            "E8_V5_LOCK_PATH": str(lock),
            "E8_V5_TRUST_LOCK": str(tmp_path / "measurement-trust.lock"),
            "E8_V5_TEST_MODE": "1",
            "PYTEST_CURRENT_TEST": "forged",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "paths must not be symlinks" in completed.stderr
    assert canonical_state.read_bytes() == before

"""Contract tests for the bounded E8 T2/r2 recovery preflight."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts/benchmark/recover_e8_quality_baseline_v5_partial_r2.py"
spec = importlib.util.spec_from_file_location("e8_partial_r2_recovery", MODULE_PATH)
assert spec is not None and spec.loader is not None
recovery = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = recovery
spec.loader.exec_module(recovery)
_normalized_answer_hash = getattr(
    sys.modules[recovery.V4.EvalTower.__module__], "normalized_answer_hash"
)


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "aborted"
    questions = []
    public = []
    for ordinal in range(500):
        method = "llm_judge" if ordinal in (6, 24, 44) else "exact_match"
        qid = f"q-{ordinal}"
        public.append({"qid": qid})
        questions.append(
            {
                "qid": qid,
                "suite": "suite",
                "scoring_method": method,
                "expected": "expected",
                "scoring_config": {},
            }
        )
    for name, rows in (("question_vector.T2.json", public), ("scoring_vector.T2.json", questions)):
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_text(json.dumps({"tier": 2, "n": 500, "questions": rows}) + "\n")
    (source / "question_vector.T1.json").write_text(
        json.dumps(
            {
                "tier": 1,
                "n": 1,
                "core_id": "sealed-t1-core",
                "questions": [{"qid": "t1-q"}],
            }
        )
        + "\n"
    )
    sidecar = [
        {
            "row_type": "batch_start",
            "requested_n": 500,
            "concurrency": recovery.V4.CONCURRENCY,
            "complete": False,
        }
    ]
    for ordinal, question in enumerate(questions[:79]):
        error = None
        answer = "answer"
        if ordinal in {2, 3, 5, 7, 20, 26, 29, 38, 41, 45, 48, 51, 53, 54, 65, 72, 75}:
            error = "[ERROR: placement timeout role=frontdoor reason=race_lost holders=[0, 1, 2] after 90.0s]"
            answer = ""
        elif ordinal in {6, 24, 44}:
            error = "scoring_unavailable: judge unavailable"
        result = {
            "qid": question["qid"],
            "question_id": question["qid"],
            "suite": "suite",
            "scoring_method": question["scoring_method"],
            "route": "frontdoor",
            "tokens_generated": 0 if error and not answer else 1,
            "correct": not bool(error),
        }
        if error:
            result.update({"error": True, "error_detail": error})
        else:
            result.update({"answer_hash": recovery.V5._normalized_answer_hash(answer)})
        sidecar.append(
            {"row_type": "question_result", "ordinal": ordinal, "answer": answer, "result": result}
        )
    _write(source / "eval_sidecars/question_results.e8-t2-r2.jsonl", sidecar)
    _write(source / "judge_traces.T2.r2.jsonl", [])
    return source


def test_plan_reuses_only_clean_rows_and_bounds_generation(tmp_path: Path) -> None:
    plan = recovery.build_plan(_source(tmp_path))
    assert len(plan["reuse_ordinals"]) == 59
    assert plan["scorer_replay_ordinals"] == [6, 24, 44]
    assert len(plan["generation_ordinals"]) == 438
    assert plan["t1_core_id"] == "sealed-t1-core"
    assert set(plan["scorer_replay_ordinals"]).isdisjoint(plan["generation_ordinals"])
    assert plan["generation_concurrency"] == recovery.V4.CONCURRENCY


def test_reconstruction_uses_sealed_t1_core_not_synthetic_t2_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    questions = [
        {
            "qid": "q-0",
            "suite": "suite",
            "prompt": "prompt",
            "expected": "answer",
            "scoring_method": "exact_match",
            "scoring_config": {},
        }
    ]
    public = recovery.V4.public_vector(
        questions,
        tier=2,
        core_id="legacy_pool_t2_seed_42_n500",
        seed=42,
    )
    scoring = recovery.V4.scoring_vector(
        questions,
        tier=2,
        core_id="legacy_pool_t2_seed_42_n500",
        seed=42,
    )
    seen: list[str] = []

    monkeypatch.setattr(recovery.V4, "EvalTower", lambda **_kwargs: object())

    def question_vector(_tower, *, tier, t1_core_id, n, seed):
        assert (tier, n, seed) == (2, recovery.N, 42)
        seen.append(t1_core_id)
        return questions, "legacy_pool_t2_seed_42_n500"

    monkeypatch.setattr(recovery.V4, "question_vector", question_vector)
    monkeypatch.setattr(
        recovery.V4,
        "apply_context_replacement_map",
        lambda _args, rows, *, tier: rows,
    )

    assert (
        recovery._reconstruct_questions(
            SimpleNamespace(api_url="http://test"),
            public,
            scoring,
            t1_core_id="core_v2",
        )
        == questions
    )
    assert seen == ["core_v2"]


def test_preflight_binds_reconstructed_vector_to_sealed_t1_core(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path)
    public = recovery.V4.load_json(source / "question_vector.T2.json")
    public["seed"] = 42
    (source / "question_vector.T2.json").write_text(json.dumps(public) + "\n")
    scoring = recovery.V4.load_json(source / "scoring_vector.T2.json")
    seen: list[str] = []
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", str(recovery.V4.CONCURRENCY))
    monkeypatch.setattr(
        recovery.V5,
        "parse_args",
        lambda _argv: SimpleNamespace(api_url="http://test", http_timeout_s=1),
    )
    monkeypatch.setattr(recovery, "_capture_recovery_claim", lambda _args: {"claim": "held"})
    monkeypatch.setattr(recovery.V4, "runtime_binding", lambda _args: {"runtime_topology": []})
    monkeypatch.setattr(
        recovery,
        "preflight_frontdoor_capacity",
        lambda _binding, **_kwargs: {"capacity": recovery.V4.CONCURRENCY},
    )

    def reconstruct(_args, _public, _scoring, *, t1_core_id):
        seen.append(t1_core_id)
        return scoring["questions"]

    monkeypatch.setattr(recovery, "_reconstruct_questions", reconstruct)
    monkeypatch.setattr(
        recovery.V4,
        "public_vector",
        lambda _questions, **_kwargs: public,
    )
    result = recovery.preflight(
        SimpleNamespace(
            source_dir=source,
            output_dir=tmp_path / "never-created",
            api_url="http://test",
        )
    )
    assert seen == ["sealed-t1-core"]
    assert result["reconstructed_question_vector_sha256"] == recovery.canonical_hash(public)
    assert not (tmp_path / "never-created").exists()


def test_plan_rejects_missing_t1_core_binding(tmp_path: Path) -> None:
    source = _source(tmp_path)
    (source / "question_vector.T1.json").unlink()
    with pytest.raises(ValueError, match="question_vector.T1.json"):
        recovery.build_plan(source)


def test_plan_rejects_unapproved_saved_error(tmp_path: Path) -> None:
    source = _source(tmp_path)
    path = source / "eval_sidecars/question_results.e8-t2-r2.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    next(row for row in rows if row.get("ordinal") == 2)["result"]["error_detail"] = (
        "request timed out"
    )
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="unapproved terminal"):
        recovery.build_plan(source)


def test_collect_fails_closed_without_creating_an_output_bundle(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "would-be-evidence"
    with pytest.raises(ValueError, match="held GLOBAL recovery claim"):
        recovery.execute(type("Args", (), {"source_dir": source, "output_dir": output})())
    assert not output.exists()


def test_collect_reconstruction_failure_writes_nothing_and_sends_no_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path)
    output = tmp_path / "would-be-recovery"
    requests: list[object] = []
    monkeypatch.setattr(recovery, "_capture_recovery_claim", lambda _args: {"claim": "held"})
    monkeypatch.setattr(
        recovery.V5,
        "parse_args",
        lambda _argv: SimpleNamespace(api_url="http://test", http_timeout_s=1),
    )
    monkeypatch.setattr(recovery.V4, "runtime_binding", lambda _args: {"runtime_topology": []})
    monkeypatch.setattr(
        recovery,
        "preflight_frontdoor_capacity",
        lambda _binding, **_kwargs: {"capacity": recovery.V4.CONCURRENCY},
    )

    def fail_reconstruction(*_args, **_kwargs):
        raise ValueError("reconstructed public vector differs")

    monkeypatch.setattr(recovery, "_reconstruct_questions", fail_reconstruction)
    monkeypatch.setattr(
        recovery, "_generate_with_watcher", lambda *_args: requests.append(object())
    )
    with pytest.raises(ValueError, match="reconstructed public vector differs"):
        recovery.execute(
            SimpleNamespace(
                source_dir=source,
                output_dir=output,
                api_url="http://test",
            )
        )
    assert not output.exists()
    assert requests == []


def test_compact_exact_match_omission_is_allowed_but_llm_judge_omission_is_not(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    path = source / "eval_sidecars/question_results.e8-t2-r2.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    next(row for row in rows if row.get("ordinal") == 0)["result"].pop("scoring_method")
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    recovery.build_plan(source)
    next(row for row in rows if row.get("ordinal") == 6)["result"].pop("scoring_method")
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="scoring method"):
        recovery.build_plan(source)


def test_plan_rejects_a_symlink_source(tmp_path: Path) -> None:
    source = _source(tmp_path)
    link = tmp_path / "source-link"
    link.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symlink"):
        recovery.build_plan(link)


def test_proposal_binds_instrument_claim_and_output_namespace(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    plan = recovery.build_plan(source)
    claim = {"claims": [{"payload": {"request_tag": "tag", "region": "q2"}}], "global_claims": [{}]}
    monkeypatch.setattr(
        recovery,
        "_instrument_identity",
        lambda _args: {"commit": "c", "runner_sha256": "r", "measurement_source_sha256": {}},
    )
    output = tmp_path / "observation"
    output.mkdir()
    proposal = recovery._recovery_proposal(
        plan,
        output,
        claim=claim,
        frontdoor_capacity={"capacity": 3},
        instrument=recovery._instrument_identity(SimpleNamespace()),
    )
    recovery._bind_recovery_proposal(output, proposal)
    assert recovery.V4.load_json(output / "recovery_proposal.json") == proposal
    assert proposal["status"] == "observation_only"
    assert proposal["application"] == "requires_separate_human_finalizer"


def test_instrument_identity_binds_v5_resume_and_recovery_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recovery.V5, "measurement_source_paths", lambda _args: [recovery.V5_PATH])
    identity = recovery._instrument_identity(SimpleNamespace())
    fingerprints = identity["measurement_source_sha256"]
    assert fingerprints[str(recovery.V5_PATH.resolve())] == recovery.sha256_path(recovery.V5_PATH)
    assert fingerprints[str(recovery.RESUME_PATH.resolve())] == recovery.sha256_path(
        recovery.RESUME_PATH
    )
    assert fingerprints[str(MODULE_PATH.resolve())] == recovery.sha256_path(MODULE_PATH)


def test_snapshot_rejects_source_mutation_before_copy(tmp_path: Path) -> None:
    source = _source(tmp_path)
    plan = recovery.build_plan(source)
    (source / "question_vector.T2.json").write_text("{}\n")
    with pytest.raises(ValueError, match="changed before snapshot"):
        recovery._snapshot_source(source, tmp_path / "output", plan)


def test_capacity_rejects_q2_q3_contention_before_generation() -> None:
    regions = {
        ("frontdoor", 1): frozenset({"q0"}),
        ("frontdoor", 2): frozenset({"q1"}),
        ("frontdoor", 3): frozenset({"q2"}),
        ("frontdoor", 4): frozenset({"q3"}),
    }
    capacity, selected = recovery.compatible_frontdoor_capacity(regions, {1, 2, 3, 4}, {"q2", "q3"})
    assert capacity == 2
    assert selected == [
        {"topology_idx": 1, "regions": ["q0"]},
        {"topology_idx": 2, "regions": ["q1"]},
    ]


def test_capacity_selects_only_mutually_disjoint_free_instances() -> None:
    regions = {
        ("frontdoor", 0): frozenset({"q0", "q1", "q2", "q3"}),
        ("frontdoor", 1): frozenset({"q0"}),
        ("frontdoor", 2): frozenset({"q1"}),
        ("frontdoor", 3): frozenset({"q2"}),
    }
    capacity, selected = recovery.compatible_frontdoor_capacity(regions, {0, 1, 2, 3}, set())
    assert capacity == 3
    assert [row["topology_idx"] for row in selected] == [1, 2, 3]


def test_frontdoor_capacity_requires_an_explicit_c1_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C1 is an amended exception; legacy callers remain bound to C3."""
    from src.runtime import instance_topology

    monkeypatch.setattr(
        instance_topology,
        "get_instance_regions",
        lambda: {
            ("frontdoor", 1): frozenset({"q0"}),
            ("frontdoor", 2): frozenset({"q1"}),
            ("frontdoor", 3): frozenset({"q2"}),
        },
    )
    monkeypatch.setattr(
        instance_topology,
        "topology_idx_for_port",
        lambda role, port: {
            ("frontdoor", 8070): 1,
            ("frontdoor", 8080): 2,
            ("frontdoor", 8180): 3,
        }.get((role, port)),
    )
    monkeypatch.setattr(recovery, "_locked_global_regions", lambda _regions: set())
    binding = {
        "runtime_topology": [
            {"port": port, "roles": ["frontdoor"]} for port in (8070, 8080, 8180)
        ]
    }
    claim = {"claims": [{"payload": {"region": "q3"}}]}

    with pytest.raises(ValueError, match="explicit concurrency contract"):
        recovery.preflight_frontdoor_capacity(binding, required=1, claim=claim)

    proof = recovery.preflight_frontdoor_capacity(
        binding,
        required=1,
        claim=claim,
        expected_concurrency=1,
    )
    assert proof["required_concurrency"] == 1
    assert proof["capacity"] == recovery.V4.CONCURRENCY

    with pytest.raises(ValueError, match="only the ratified c3 or amended c1"):
        recovery.preflight_frontdoor_capacity(
            binding,
            required=2,
            claim=claim,
            expected_concurrency=2,
        )
    with pytest.raises(ValueError, match="only the ratified c3 or amended c1"):
        recovery.preflight_frontdoor_capacity(
            binding,
            required=1,
            claim=claim,
            expected_concurrency=True,
        )

    proof = recovery.preflight_frontdoor_capacity(
        binding,
        required=recovery.V4.CONCURRENCY,
        claim=claim,
    )
    assert proof["required_concurrency"] == recovery.V4.CONCURRENCY


def _small_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink only this module's frozen contract for execute-path tests."""
    monkeypatch.setattr(recovery, "N", 5)
    monkeypatch.setattr(recovery, "SAVED_PREFIX_N", 3)
    monkeypatch.setattr(
        recovery,
        "EXPECTED_SAVED_DISPOSITIONS",
        recovery.Counter({"reuse": 1, "regenerate": 1, "rescore": 1}),
    )
    monkeypatch.setattr(recovery, "EXPECTED_GENERATION_N", 3)


def _small_source(tmp_path: Path) -> Path:
    source = tmp_path / "aborted-small"
    questions = [
        {
            "qid": f"q-{ordinal}",
            "suite": "suite",
            "scoring_method": "llm_judge" if ordinal == 2 else "exact_match",
            "expected": "expected",
            "scoring_config": {},
        }
        for ordinal in range(5)
    ]
    for name, rows in (
        ("question_vector.T2.json", [{"qid": row["qid"]} for row in questions]),
        ("scoring_vector.T2.json", questions),
    ):
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_text(
            json.dumps({"tier": 2, "n": 5, "core_id": "small-core", "seed": 7, "questions": rows})
            + "\n"
        )
    (source / "question_vector.T1.json").write_text(
        json.dumps(
            {
                "tier": 1,
                "n": 1,
                "core_id": "small-t1-core",
                "questions": [{"qid": "t1-q"}],
            }
        )
        + "\n"
    )
    race_lost = "[ERROR: placement timeout role=frontdoor reason=race_lost holders=[0] after 90.0s]"
    scorer_error = "scoring_unavailable: judge unavailable"
    sidecar = [
        {
            "row_type": "batch_start",
            "requested_n": 5,
            "concurrency": recovery.V4.CONCURRENCY,
            "complete": False,
        },
        {
            "row_type": "question_result",
            "ordinal": 0,
            "answer": "saved-clean",
            "result": {
                "qid": "q-0",
                "question_id": "q-0",
                "suite": "suite",
                "route": "frontdoor",
                "tokens_generated": 1,
                "correct": True,
                "answer_hash": _normalized_answer_hash("saved-clean"),
            },
        },
        {
            "row_type": "question_result",
            "ordinal": 1,
            "answer": "",
            "result": {
                "qid": "q-1",
                "question_id": "q-1",
                "suite": "suite",
                "scoring_method": "exact_match",
                "route": "frontdoor",
                "tokens_generated": 0,
                "correct": False,
                "error": True,
                "error_detail": race_lost,
            },
        },
        {
            "row_type": "question_result",
            "ordinal": 2,
            "answer": "saved-scorer-output",
            "result": {
                "qid": "q-2",
                "question_id": "q-2",
                "suite": "suite",
                "scoring_method": "llm_judge",
                "route": "frontdoor",
                "tokens_generated": 1,
                "correct": False,
                "error": True,
                "error_detail": scorer_error,
            },
        },
    ]
    _write(source / "eval_sidecars/question_results.e8-t2-r2.jsonl", sidecar)
    _write(source / "judge_traces.T2.r2.jsonl", [])
    return source


class _FakeResult:
    def __init__(self, qid: str, *, answer: str, error: str | None = None) -> None:
        self.qid = qid
        self.question_id = qid
        self.answer = answer
        self.correct = error is None
        self.error = error
        self.partial = False
        self.degraded = False
        self.route_used = "frontdoor"
        self.eval_concurrency = recovery.V4.CONCURRENCY


class _FakeWatcher:
    last_instance: "_FakeWatcher | None" = None

    def __init__(self, _runner_args, _binding, path: Path, **_kwargs) -> None:
        type(self).last_instance = self
        self.started = False
        self.path = path
        self.samples: list[dict] = recovery.V4.load_jsonl(path) if path.exists() else []
        self._active_load: dict[str, int] | None = None

    def sample(self) -> None:
        offset = len(self.samples)
        sample = {
            "ok": True,
            "active_load": self._active_load,
            "api_probe_urls": {},
            "runtime_artifacts": {},
            "started_at": f"2026-07-28T00:00:{offset:02d}Z",
            "finished_at": f"2026-07-28T00:00:{offset:02d}Z",
        }
        self.samples.append(sample)
        _write(self.path, self.samples)

    def start(self) -> None:
        self.started = True
        self.sample()

    def stop(self) -> list[dict]:
        self.sample()
        return list(self.samples)

    @contextmanager
    def active_load(self, **_kwargs):
        self._active_load = {"tier": _kwargs["tier"], "repetition": _kwargs["repetition"]}
        try:
            yield
        finally:
            self._active_load = None


def _patch_execute_environment(monkeypatch: pytest.MonkeyPatch, requests: list[list[int]]) -> None:
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", str(recovery.V4.CONCURRENCY))
    claim = {
        "claims": [{"payload": {"request_tag": "claim", "region": "q0"}}],
        "global_claims": [{"region": "q0"}],
    }
    monkeypatch.setattr(recovery, "_capture_recovery_claim", lambda _args: claim)
    monkeypatch.setattr(
        recovery,
        "_instrument_identity",
        lambda _args: {
            "commit": "test",
            "runner_sha256": "runner",
            "measurement_source_sha256": {},
        },
    )
    monkeypatch.setattr(
        recovery.V5,
        "parse_args",
        lambda _argv: SimpleNamespace(api_url="http://test", http_timeout_s=1),
    )
    monkeypatch.setattr(recovery.V4, "runtime_binding", lambda _args: {"runtime_topology": []})
    monkeypatch.setattr(
        recovery,
        "preflight_frontdoor_capacity",
        lambda _binding, **_kwargs: {"capacity": recovery.V4.CONCURRENCY, "proof": "test"},
    )
    monkeypatch.setattr(
        recovery,
        "_reconstruct_questions",
        lambda _args, _public, scoring, *, t1_core_id: [
            {**question, "_reconstructed_only": True} for question in scoring["questions"]
        ],
    )
    monkeypatch.setattr(
        recovery.V4, "capture_llm_judge_traces", lambda *_args, **_kwargs: nullcontext()
    )
    monkeypatch.setattr(
        recovery.V4, "judge_trace_fixed_vector_identity", lambda *_args: nullcontext()
    )
    monkeypatch.setattr(
        recovery.V4, "score_answer_or_error", lambda *_args, **_kwargs: (True, None)
    )
    monkeypatch.setattr(
        recovery.V4, "fixed_baseline_environment", lambda *_args, **_kwargs: nullcontext()
    )
    monkeypatch.setattr(
        recovery.V4, "bind_eval_tower_scorer_identities", lambda *_args, **_kwargs: nullcontext()
    )
    monkeypatch.setattr(recovery.V4, "api_health", lambda *_args: {"ok": True})
    monkeypatch.setattr(recovery.V4, "probe_url_mapping", lambda _health: {})
    monkeypatch.setattr(recovery.V4, "RuntimeWatcher", _FakeWatcher)
    monkeypatch.setattr(recovery.V4, "require_clean_watcher", lambda _watcher: None)

    class FakeTower:
        def __init__(self, *_args, **_kwargs) -> None:
            self.timeout = 1
            self._question_artifact_dir: Path | None = None

        def _eval_batch(self, execution, _client, **_kwargs):
            requests.append([int(row["_ordinal"]) for row in execution])
            assert self._question_artifact_dir is not None
            path = self._question_artifact_dir / "question_results.e8-t2-r2-recovery.jsonl"
            batch_id = f"batch-{len(requests)}"
            rows = recovery.V4.load_jsonl(path) if path.exists() else []
            rows.append(
                {
                    "row_type": "batch_start",
                    "eval_batch_id": batch_id,
                    "label": "e8-t2-r2-recovery",
                    "requested_n": len(execution),
                    "concurrency": recovery.V4.CONCURRENCY,
                    "complete": False,
                }
            )
            for row in execution:
                qid = row["qid"]
                scorer_error = qid == "q-4"
                answer = f"answer-{qid}"
                result = {
                    "qid": qid,
                    "question_id": qid,
                    "suite": "suite",
                    "route": "frontdoor",
                    "tokens_generated": 1,
                    "correct": not scorer_error,
                    "answer_hash": _normalized_answer_hash(answer),
                }
                if scorer_error:
                    result.update({"error": True, "error_detail": "scoring_unavailable: transient"})
                rows.append(
                    {
                        "row_type": "question_result",
                        "eval_batch_id": batch_id,
                        "label": "e8-t2-r2-recovery",
                        "requested_n": len(execution),
                        "ordinal": row["_ordinal"],
                        "started_at_s": 1785196802.25,
                        "ended_at_s": 1785196802.75,
                        "answer": answer,
                        "result": result,
                    }
                )
            rows.append(
                {
                    "row_type": "batch_complete",
                    "eval_batch_id": batch_id,
                    "label": "e8-t2-r2-recovery",
                    "requested_n": len(execution),
                    "completed_n": len(execution),
                    "complete": True,
                }
            )
            _write(path, rows)
            return [
                _FakeResult(
                    row["qid"],
                    answer=f"answer-{row['qid']}",
                    error=("scoring_unavailable: transient" if row["qid"] == "q-4" else None),
                )
                for row in execution
            ]

    setattr(sys.modules[FakeTower.__module__], "normalized_answer_hash", _normalized_answer_hash)

    def replay(results, execution):
        for position, (result, question) in enumerate(zip(results, execution)):
            if question["qid"] == "q-4":
                result.error = None
                result.correct = True
                return [{"ordinal": position, "qid": result.qid, "outcome": "recovered"}]
        return []

    monkeypatch.setattr(recovery.V4, "EvalTower", FakeTower)
    monkeypatch.setattr(recovery.V4, "replay_llm_judge_scorer_tail_once", replay)

    def complete(
        output,
        _snapshot,
        _plan,
        rows,
        _questions,
        _api_url,
        *,
        completion_context=None,
    ):
        recovery.V4.write_text(
            output / "responses.T2.r2.jsonl",
            "".join(
                json.dumps(rows[ordinal]["response"], sort_keys=True) + "\n"
                for ordinal in sorted(rows)
            ),
        )
        recovery._write_json(output / "raw.T2.r2.json", {"q": 1.0, "n": len(rows)})
        marker = {
                "status": "complete",
                "raw_sha256": recovery.sha256_path(output / "raw.T2.r2.json"),
                "journal_sha256": recovery.sha256_path(output / "recovery_rows.T2.r2.jsonl"),
            }
        if completion_context is not None:
            marker.update(completion_context)
        recovery._write_json(output / "r2_complete.json", marker)

    monkeypatch.setattr(recovery, "_complete_r2", complete)


def _args(source: Path, output: Path) -> SimpleNamespace:
    return SimpleNamespace(source_dir=source, output_dir=output, api_url="http://test")


@pytest.mark.parametrize(
    "defect",
    [
        "concurrency",
        "batch_id",
        "watcher_bracket",
        "stale_sidecar",
        "cadence_gap",
        "missing_complete",
        "partial_complete",
        "complete_requested_n",
    ],
)
def test_generation_harvest_requires_c3_batch_and_clean_watcher_bracket(
    tmp_path: Path,
    defect: str,
) -> None:
    batch_id = "batch-reviewed"
    sidecar = tmp_path / "question_results.jsonl"
    watcher = tmp_path / "watcher.jsonl"
    rows = [
        {
            "row_type": "batch_start",
            "eval_batch_id": batch_id,
            "label": "e8-t2-r2-recovery",
            "requested_n": 1,
            "concurrency": 1 if defect == "concurrency" else recovery.V4.CONCURRENCY,
        },
        {
            "row_type": "question_result",
            "eval_batch_id": "stale" if defect == "batch_id" else batch_id,
            "label": "e8-t2-r2-recovery",
            "requested_n": 1,
            "ordinal": 7,
            "started_at_s": (
                1785196799.0 if defect == "stale_sidecar" else 1785196801.0
            ),
            "ended_at_s": 1785196806.0 if defect == "watcher_bracket" else 1785196804.0,
            "answer": "answer",
            "result": {"qid": "q7", "question_id": "q7"},
        },
    ]
    if defect != "missing_complete":
        rows.append(
            {
                "row_type": "batch_complete",
                "eval_batch_id": batch_id,
                "label": "e8-t2-r2-recovery",
                "requested_n": 2 if defect == "complete_requested_n" else 1,
                "completed_n": 0 if defect == "partial_complete" else 1,
                "complete": True,
            }
        )
    _write(sidecar, rows)
    watcher_rows = [
        {
            "ok": True,
            "active_load": {"tier": 2, "repetition": 2},
            "started_at": "2026-07-28T00:00:00Z",
            "finished_at": "2026-07-28T00:00:00Z",
        },
        {
            "ok": True,
            "active_load": {"tier": 2, "repetition": 2},
            "started_at": (
                "2026-07-28T00:00:08Z"
                if defect == "cadence_gap"
                else "2026-07-28T00:00:05Z"
            ),
            "finished_at": (
                "2026-07-28T00:00:08Z"
                if defect == "cadence_gap"
                else "2026-07-28T00:00:05Z"
            ),
        },
    ]
    _write(watcher, watcher_rows)
    with pytest.raises(ValueError, match="batch|watcher"):
        recovery._validate_generation_sidecar_envelope(sidecar, watcher, {7})


def test_execute_uses_original_ordinals_reconciles_scorer_and_stops_at_r2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    source = _small_source(tmp_path)
    output = recovery.execute(_args(source, tmp_path / "output"))

    assert requests == [[1, 3, 4]]
    journal = recovery.V4.load_jsonl(output / "recovery_rows.T2.r2.jsonl")
    assert {row["ordinal"] for row in journal} == set(range(5))
    assert next(row for row in journal if row["ordinal"] == 2)["source"] == "scorer_replay"
    assert next(row for row in journal if row["ordinal"] == 4)["source"] == "generation"
    generated_sidecar = recovery.V4.load_jsonl(
        output / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl"
    )
    scorer_row = next(row for row in generated_sidecar if row.get("ordinal") == 4)
    assert scorer_row["result"].get("error") is None
    assert scorer_row["result"]["correct"] is True
    marker = recovery.V4.load_json(output / "r2_complete.json")
    assert marker["status"] == "intermediate_r2_complete"
    assert marker["raw_sha256"] == recovery.sha256_path(output / "raw.T2.r2.json")
    assert marker["journal_sha256"] == recovery.sha256_path(output / "recovery_rows.T2.r2.jsonl")
    assert marker["watcher"]["proposal_sha256"] == recovery.sha256_path(
        output / "recovery_proposal.json"
    )
    assert marker["scorer_attempts"] == {
        "path": "scorer_attempts.T2.r2.jsonl",
        "sha256": recovery.sha256_path(output / "scorer_attempts.T2.r2.jsonl"),
        "records": 2,
        "expected_terminal_count": 1,
        "terminal_states": {"succeeded": 1},
    }
    assert marker["scorer_attempts_sha256"] == marker["scorer_attempts"]["sha256"]
    scorer_attempts = recovery.V4.load_jsonl(output / "scorer_attempts.T2.r2.jsonl")
    sealed_scoring_question = recovery.V4.load_json(source / "scoring_vector.T2.json")["questions"][
        2
    ]
    assert scorer_attempts[0]["scoring_question_sha256"] == recovery.canonical_hash(
        sealed_scoring_question
    )
    assert scorer_attempts[0]["scoring_question_sha256"] != recovery.canonical_hash(
        {**sealed_scoring_question, "_reconstructed_only": True}
    )
    (output / "raw.T2.r2.json").write_text('{"q": 0}\n')
    assert marker["raw_sha256"] != recovery.sha256_path(output / "raw.T2.r2.json")
    assert (output / "r3_complete.json").exists() is False
    assert (output / "run_seal.json").exists() is False
    assert (output / "responses.T2.r2.jsonl").is_file()
    assert (output / "raw.T2.r2.json").is_file()


def test_scorer_replay_runs_inside_the_shared_active_load_watcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    observed_active_load: list[dict[str, int] | None] = []

    def score(*_args, **_kwargs):
        assert _FakeWatcher.last_instance is not None
        observed_active_load.append(_FakeWatcher.last_instance._active_load)
        return True, None

    monkeypatch.setattr(recovery.V4, "score_answer_or_error", score)
    output = recovery.execute(_args(_small_source(tmp_path), tmp_path / "output"))

    assert observed_active_load == [{"tier": 2, "repetition": 2}]
    watcher = recovery.V4.load_jsonl(output / "runtime_watch.r2.jsonl")
    assert any(row["active_load"] == {"tier": 2, "repetition": 2} for row in watcher)
    assert requests == [[1, 3, 4]]


def test_failed_scorer_attempt_is_durable_and_cannot_be_replayed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    source = _small_source(tmp_path)
    output = tmp_path / "output"
    calls = 0

    def fail_score(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        assert _FakeWatcher.last_instance is not None
        assert _FakeWatcher.last_instance._active_load == {"tier": 2, "repetition": 2}
        return False, "judge unavailable"

    monkeypatch.setattr(recovery.V4, "score_answer_or_error", fail_score)
    with pytest.raises(RuntimeError, match="scorer-only replay failed closed"):
        recovery.execute(_args(source, output))

    attempts = recovery.V4.load_jsonl(output / "scorer_attempts.T2.r2.jsonl")
    assert [row["state"] for row in attempts] == ["started", "failed"]
    assert attempts[0]["ordinal"] == attempts[1]["ordinal"] == 2
    assert attempts[0]["qid"] == attempts[1]["qid"] == "q-2"
    watcher = recovery.V4.load_jsonl(output / "runtime_watch.r2.jsonl")
    assert any(row["active_load"] == {"tier": 2, "repetition": 2} for row in watcher)

    with pytest.raises(ValueError, match="terminally aborted"):
        recovery.execute(_args(source, output))
    assert calls == 1
    assert requests == []


@pytest.mark.parametrize("failure", ("binding", "cadence"))
def test_watcher_evidence_rejects_inconsistent_binding_or_cadence(
    tmp_path: Path, failure: str
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    claim = {"claims": [{"payload": {"request_tag": "tag", "region": "q0"}}]}
    recovery._write_json(
        output / "recovery_proposal.json", {"region_claim": {"tag": "tag", "regions": ["q0"]}}
    )
    seconds = (0, 8) if failure == "cadence" else (0, 1)
    rows = [
        {
            "ok": True,
            "active_load": {"tier": 2, "repetition": 2},
            "api_probe_urls": {
                "frontdoor": "http://test" if failure != "binding" or index == 0 else "http://other"
            },
            "runtime_artifacts": {},
            "started_at": f"2026-07-28T00:00:{second:02d}Z",
            "finished_at": f"2026-07-28T00:00:{second:02d}Z",
        }
        for index, second in enumerate(seconds)
    ]
    _write(output / "runtime_watch.r2.jsonl", rows)
    with pytest.raises(ValueError, match="cadence-valid"):
        recovery._watcher_evidence(
            output / "runtime_watch.r2.jsonl",
            {"region_claim": {"tag": "tag", "regions": ["q0"]}},
            claim_before=claim,
            claim_after=claim,
        )


def test_failed_namespace_is_terminal_and_requires_an_explicit_successor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    source = _small_source(tmp_path)
    output = tmp_path / "output"
    complete = recovery._complete_r2
    monkeypatch.setattr(
        recovery,
        "_complete_r2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("crash before r2 complete")
        ),
    )
    with pytest.raises(RuntimeError, match="crash before r2 complete"):
        recovery.execute(_args(source, output))
    watcher_rows = recovery.V4.load_jsonl(output / "runtime_watch.r2.jsonl")
    assert watcher_rows and all(row["ok"] is True for row in watcher_rows)
    assert any(row["active_load"] == {"tier": 2, "repetition": 2} for row in watcher_rows)
    assert recovery.V4.load_json(output / "writer_abort.json")["no_admission"] is True
    assert recovery.V4.load_json(output / "run_seal.json")["status"] == (
        "terminal_aborted_no_admission"
    )

    monkeypatch.setattr(recovery, "_complete_r2", complete)
    with pytest.raises(ValueError, match="terminally aborted"):
        recovery.execute(_args(source, output))
    assert requests == [[1, 3, 4]]


def test_interrupted_generation_terminalizes_without_automatic_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    source = _small_source(tmp_path)
    output = tmp_path / "output"
    original_tower = recovery.V4.EvalTower
    first = True

    class InterruptingTower(original_tower):
        def _eval_batch(self, execution, client, **kwargs):
            nonlocal first
            if first:
                first = False
                partial = execution[:1]
                super()._eval_batch(partial, client, **kwargs)
                raise RuntimeError("interrupted")
            return super()._eval_batch(execution, client, **kwargs)

    monkeypatch.setattr(recovery.V4, "EvalTower", InterruptingTower)
    with pytest.raises(RuntimeError, match="interrupted"):
        recovery.execute(_args(source, output))
    monkeypatch.setattr(recovery.V4, "EvalTower", original_tower)

    with pytest.raises(ValueError, match="terminally aborted"):
        recovery.execute(_args(source, output))
    assert requests == [[1]]
    assert recovery.V4.load_json(output / "run_seal.json")["status"] == (
        "terminal_aborted_no_admission"
    )
    journal = recovery.V4.load_jsonl(output / "recovery_rows.T2.r2.jsonl")
    assert set(range(5)) - {1, 3, 4} <= {row["ordinal"] for row in journal}
    sidecar = recovery.V4.load_jsonl(
        output / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl"
    )
    assert {row["ordinal"] for row in sidecar if row.get("row_type") == "question_result"} == {
        1
    }
    watcher = recovery.V4.load_jsonl(output / "runtime_watch.r2.jsonl")
    assert all(row["ok"] is True for row in watcher)
    assert all(row["active_load"] in (None, {"tier": 2, "repetition": 2}) for row in watcher)
    assert any(row["active_load"] == {"tier": 2, "repetition": 2} for row in watcher)


def test_atomic_json_replacement_preserves_prior_bytes_on_publish_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"state":"old"}\n')
    monkeypatch.setattr(
        recovery.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("injected replace failure")),
    )

    with pytest.raises(OSError, match="injected replace failure"):
        recovery._write_json(path, {"state": "new"})

    assert path.read_text() == '{"state":"old"}\n'
    assert list(tmp_path.glob(".state.json.tmp-*")) == []


def test_snapshot_relocates_upstream_binding_without_self_overwrite(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    upstream = source / "source_binding.json"
    upstream.write_text('{"source_sha256":{"old":"binding"}}\n')
    plan = recovery.build_plan(source)
    output = tmp_path / "output"
    output.mkdir()

    snapshot = recovery._snapshot_source(source, output, plan)

    assert (snapshot / "upstream_source_binding.json").read_bytes() == upstream.read_bytes()
    wrapper = recovery.V4.load_json(snapshot / "source_binding.json")
    assert wrapper["source_sha256"] == plan["source_sha256"]
    assert wrapper["source_sha256"]["upstream_source_binding.json"] == (
        recovery.sha256_path(upstream)
    )


def test_failed_attempt_history_fails_closed_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    source = _small_source(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    _write(
        output / "generation_failed_attempts.T2.r2.jsonl",
        [{"failures": [{"ordinal": 1}], "disposition": "failed_closed_no_automatic_retry"}],
    )
    with pytest.raises(RuntimeError, match="failed generation-attempt history"):
        recovery.execute(_args(source, output))
    assert requests == []


@pytest.mark.parametrize("failure", ("claim", "preflight"))
def test_claim_or_preflight_failure_happens_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    _small_contract(monkeypatch)
    requests: list[list[int]] = []
    _patch_execute_environment(monkeypatch, requests)
    if failure == "claim":
        monkeypatch.setattr(
            recovery,
            "_capture_recovery_claim",
            lambda _args: (_ for _ in ()).throw(ValueError("claim failed")),
        )
    else:
        monkeypatch.setattr(
            recovery,
            "preflight_frontdoor_capacity",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("preflight failed")),
        )
    with pytest.raises(ValueError, match=f"{failure} failed"):
        recovery.execute(_args(_small_source(tmp_path), tmp_path / "output"))
    assert requests == []

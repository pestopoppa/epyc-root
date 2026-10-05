"""Adversarial eligibility tests for the E8 r2 race-only second successor."""
# NIB2-75 (2026-09-23): tests that needed the retired E8 sealed bundles were removed per OP-19.
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/benchmark/prepare_e8_quality_baseline_v5_partial_r2_race_retry.py"
SPEC = importlib.util.spec_from_file_location("e8_r2_race_retry_test", PATH)
assert SPEC and SPEC.loader
RETRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETRY)


QUESTION = {"qid": "q0"}
RACE = "[ERROR: placement timeout role=frontdoor reason=race_lost holders=[0, 1, 2] after 90.0s]"


def _provenance(**overrides: object) -> dict:
    value = {
        "schema": RETRY.FAILURE_PROVENANCE_SCHEMA,
        "class": "admission_timeout",
        "code": "race_lost",
        "phase": "admission",
        "generation_started": False,
        "tokens_generated": 0,
        "partial": False,
        "degraded": False,
        "role": "frontdoor",
        "workload_class": "eval_batch",
        "max_queue_wait_ms": 90_000,
    }
    value.update(overrides)
    return value


def _row(*, error: str = RACE, tokens: int = 0, answer: str = "") -> dict:
    return {
        "row_type": "question_result", "ordinal": 0,
        "answer": answer,
        "result": {
            "qid": "q0", "question_id": "q0", "correct": False,
            "error": True, "error_detail": error, "tokens_generated": tokens,
            "route": "frontdoor", "partial": False, "degraded": False,
            "failure_provenance": _provenance(),
        },
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _watcher(started_at: str, *, binding: str = "a") -> dict:
    return {
        "ok": True,
        "active_load": {"tier": 2, "repetition": 2},
        "started_at": started_at,
        "api_probe_urls": {"frontdoor": binding},
        "runtime_artifacts": {"server": {"identity": binding}},
    }


def test_real_admission_race_contract_reaches_v2_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the wire contract instead of constructing a provenance fixture."""
    from fastapi.testclient import TestClient

    from src.api import app
    from src.scheduling.contention_gate import ContentionDenied

    eval_tower = sys.modules[RETRY.V4.EvalTower.__module__]

    @app.post("/__test_e8_typed_admission_race")
    def _raise_typed_race() -> None:
        raise ContentionDenied(
            "placement lock race",
            role="frontdoor",
            workload_class="eval_batch",
            wait_budget_ms=90_000,
            failure_class="admission_timeout",
            code="race_lost",
        )

    api_client = TestClient(app)

    class ApiAdapter:
        def post(self, *_args: object, **_kwargs: object):
            return api_client.post("/__test_e8_typed_admission_race")

    wire_response = eval_tower.call_orchestrator_forced(
        prompt="q",
        force_role="frontdoor",
        client=ApiAdapter(),
        workload_class="eval_batch",
        timeout=90,
    )
    monkeypatch.setattr(
        eval_tower,
        "call_orchestrator_forced",
        lambda **_kwargs: dict(wire_response),
    )

    tower = eval_tower.EvalTower()
    with eval_tower.httpx.Client(timeout=1) as client:
        result = tower._eval_question(
            {
                "id": "q0",
                "qid": "q0",
                "suite": "test",
                "prompt": "q",
                "expected": "a",
                "force_role": "frontdoor",
            },
            client,
        )
    compact = eval_tower._compact_question_result(result)
    assert RETRY._race_lost(
        {"answer": result.answer, "result": compact},
        QUESTION,
    )


def test_copy_tree_rejects_destination_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    artifact = source / "artifact.json"
    artifact.write_text("sealed\n")
    expected = {"artifact.json": RETRY.sha256_path(artifact)}
    real_copy = RETRY.shutil.copyfile

    def corrupt_copy(origin: Path, destination: Path) -> None:
        real_copy(origin, destination)
        Path(destination).write_text("corrupt\n")

    monkeypatch.setattr(RETRY.shutil, "copyfile", corrupt_copy)
    with pytest.raises(ValueError, match="copy differs"):
        RETRY._copy_tree(source, tmp_path / "destination", expected)


def test_publish_revalidates_after_fsync_before_atomic_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staging = tmp_path / ".candidate.staging-test"
    destination = tmp_path / "candidate"
    source = tmp_path / "source"
    base = source / "source_snapshot"
    staging.mkdir()
    base.mkdir(parents=True)
    marker = staging / "mutation-marker"
    marker.write_text("before", encoding="utf-8")
    seen: list[str] = []

    def validate(path: Path, _plan: dict, **_kwargs: object) -> None:
        seen.append((path / "mutation-marker").read_text(encoding="utf-8"))
        if len(seen) == 2:
            raise ValueError("staged tree changed during fsync")

    def mutate_after_first_validation(_path: Path) -> None:
        marker.write_text("after", encoding="utf-8")

    monkeypatch.setattr(RETRY, "validate_staged_tree", validate)
    monkeypatch.setattr(RETRY, "_fsync_tree", mutate_after_first_validation)
    monkeypatch.setattr(RETRY, "source_hashes", lambda _path: {})
    monkeypatch.setattr(
        RETRY.V4,
        "atomic_publish_noreplace",
        lambda *_args: pytest.fail("must not publish a post-fsync mutation"),
    )

    with pytest.raises(ValueError, match="changed during fsync"):
        RETRY._validate_and_publish(
            staging,
            destination,
            {"source_sha256": {}, "predecessor_sha256": {}},
            source=source,
            base=base,
            persisted_plan={"source_sha256": {}, "predecessor_sha256": {}},
        )
    assert seen == ["before", "after"]
    assert staging.is_dir()
    assert not destination.exists()


def test_parent_fsync_fault_after_publish_quarantines_public_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staging = tmp_path / ".candidate.staging-test"
    destination = tmp_path / "candidate"
    source = tmp_path / "source"
    base = source / "source_snapshot"
    staging.mkdir()
    base.mkdir(parents=True)
    (staging / "sealed.txt").write_text("sealed\n", encoding="utf-8")
    monkeypatch.setattr(RETRY, "validate_staged_tree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(RETRY, "_fsync_tree", lambda _path: None)
    monkeypatch.setattr(RETRY, "source_hashes", lambda _path: {})
    real_fsync_dir = RETRY.V4.fsync_dir

    def fail_only_post_publish(path: Path) -> None:
        if path == destination.parent and destination.is_dir():
            raise OSError("injected parent fsync failure")
        real_fsync_dir(path)

    monkeypatch.setattr(RETRY.V4, "fsync_dir", fail_only_post_publish)
    with pytest.raises(OSError, match="injected parent fsync failure"):
        RETRY._validate_and_publish(
            staging,
            destination,
            {"source_sha256": {}, "predecessor_sha256": {}},
            source=source,
            base=base,
            persisted_plan={"source_sha256": {}, "predecessor_sha256": {}},
        )

    assert not destination.exists()
    quarantines = list(tmp_path.glob(".candidate.aborted-*"))
    assert len(quarantines) == 1
    abort = RETRY.V4.load_json(quarantines[0] / RETRY.RECOVERY.ABORT_MARKER_NAME)
    assert abort["status"] == "terminal_aborted_no_admission"
    seal = RETRY.V4.load_json(quarantines[0] / "run_seal.json")
    assert seal["status"] == "terminal_aborted_no_admission"
    assert seal["writer"] == "prepare_e8_quality_baseline_v5_partial_r2_race_retry"


def test_exact_race_lost_requires_typed_pre_generation_contract() -> None:
    assert RETRY._race_lost(_row(), QUESTION)
    assert not RETRY._race_lost(_row(tokens=1), QUESTION)
    assert not RETRY._race_lost(_row(answer="model output"), QUESTION)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("schema", "epyc.failure_provenance.v0"),
        ("class", "client_transport_timeout"),
        ("code", "contention_timeout"),
        ("phase", "client_transport"),
        ("generation_started", True),
        ("generation_started", "false"),
        ("tokens_generated", 1),
        ("tokens_generated", "0"),
        ("partial", True),
        ("partial", "false"),
        ("degraded", True),
        ("degraded", "false"),
        ("role", "worker"),
        ("workload_class", "campaign"),
        ("max_queue_wait_ms", 89_999),
        ("max_queue_wait_ms", "90000"),
    ],
)
def test_v2_rejects_each_mutated_provenance_field(key: str, value: object) -> None:
    row = _row(error="arbitrary wording ignored")
    row["result"]["failure_provenance"] = _provenance(**{key: value})
    assert not RETRY._race_lost(row, QUESTION)


@pytest.mark.parametrize("key", sorted(_provenance()))
def test_v2_rejects_each_missing_provenance_field(key: str) -> None:
    row = _row()
    del row["result"]["failure_provenance"][key]
    assert not RETRY._race_lost(row, QUESTION)


def test_v2_rejects_legacy_string_lookalike_and_client_timeout() -> None:
    legacy = _row()
    legacy["result"].pop("failure_provenance")
    assert not RETRY._race_lost(legacy, QUESTION)

    transport = _row()
    transport["result"]["failure_provenance"] = {
        "schema": RETRY.FAILURE_PROVENANCE_SCHEMA,
        "class": "client_transport_timeout",
        "code": "read_timeout",
        "phase": "client_transport",
        "role": "frontdoor",
        "workload_class": "eval_batch",
        "max_queue_wait_ms": 90_000,
    }
    assert not RETRY._race_lost(transport, QUESTION)


def test_v2_rejects_missing_explicit_result_negatives_and_copied_identity() -> None:
    for key in ("partial", "degraded"):
        row = _row()
        del row["result"][key]
        assert not RETRY._race_lost(row, QUESTION)
    copied = _row()
    copied["result"]["qid"] = copied["result"]["question_id"] = "other"
    with pytest.raises(ValueError, match="identity"):
        RETRY._race_lost(copied, QUESTION)


def test_duplicate_sidecar_ordinal_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "sidecar.jsonl"
    _write_jsonl(path, [_row(), _row()])
    with pytest.raises(ValueError, match="duplicate"):
        RETRY._rows(path)


def test_unknown_plan_schema_cannot_enter_v2_publication(tmp_path: Path) -> None:
    root = tmp_path / "candidate"
    root.mkdir()
    with pytest.raises(ValueError, match="schema is unsupported"):
        RETRY.validate_staged_tree(
            root,
            {"schema": "epyc.e8_quality_v5_partial_r2_race_retry_plan.v999"},
        )


def test_terminal_failure_ledger_validates_sidecar_completion_order(tmp_path: Path) -> None:
    first = _row()
    first["ordinal"] = 279
    second = _row()
    second["ordinal"] = 97
    sidecars = {279: first, 97: second}
    expected = [
        {"ordinal": ordinal, "sidecar_sha256": RETRY.canonical_hash(row)}
        for ordinal, row in sidecars.items()
    ]
    _write_jsonl(
        tmp_path / "generation_failed_attempts.T2.r2.jsonl",
        [{"failures": expected, "disposition": "failed_closed_no_automatic_retry"}],
    )

    path, digest = RETRY._terminal_failure_ledger(tmp_path, sidecars, [97, 279])

    assert path.name == "generation_failed_attempts.T2.r2.jsonl"
    assert digest == RETRY.sha256_path(path)


def test_terminal_failure_ledger_rejects_ordinal_sorted_order(tmp_path: Path) -> None:
    first = _row()
    first["ordinal"] = 279
    second = _row()
    second["ordinal"] = 97
    sidecars = {279: first, 97: second}
    ordinal_sorted = [
        {"ordinal": ordinal, "sidecar_sha256": RETRY.canonical_hash(sidecars[ordinal])}
        for ordinal in (97, 279)
    ]
    _write_jsonl(
        tmp_path / "generation_failed_attempts.T2.r2.jsonl",
        [{"failures": ordinal_sorted, "disposition": "failed_closed_no_automatic_retry"}],
    )

    with pytest.raises(ValueError, match="exact sidecar failures"):
        RETRY._terminal_failure_ledger(tmp_path, sidecars, [97, 279])


def test_tree_pin_rejects_source_tamper_before_any_artifact_read(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    item = source / "immutable.txt"
    item.write_text("before")
    expected = RETRY.canonical_hash(RETRY.source_hashes(source))
    item.write_text("after")
    with pytest.raises(ValueError, match="explicit terminal tree hash"):
        RETRY.build_plan(source, expected)


def test_contaminated_predecessor_watcher_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "watcher.jsonl"
    rows = [_watcher("2026-01-01T00:00:00Z"), _watcher("2026-01-01T00:00:05Z")]
    rows[0]["ok"] = False
    _write_jsonl(path, rows)
    with pytest.raises(ValueError, match="watcher is contaminated"):
        RETRY._require_clean_predecessor_watcher(path)


def test_predecessor_watcher_rejects_gap_over_ratified_limit(tmp_path: Path) -> None:
    path = tmp_path / "watcher.jsonl"
    _write_jsonl(
        path,
        [_watcher("2026-01-01T00:00:00Z"), _watcher("2026-01-01T00:00:07.001Z")],
    )
    with pytest.raises(ValueError, match="watcher is contaminated"):
        RETRY._require_clean_predecessor_watcher(path)


def test_predecessor_watcher_rejects_immutable_binding_drift(tmp_path: Path) -> None:
    path = tmp_path / "watcher.jsonl"
    _write_jsonl(
        path,
        [_watcher("2026-01-01T00:00:00Z", binding="one"), _watcher("2026-01-01T00:00:05Z", binding="two")],
    )
    with pytest.raises(ValueError, match="watcher is contaminated"):
        RETRY._require_clean_predecessor_watcher(path)


def test_saved_rows_rejects_conflicting_ordinal_collision(tmp_path: Path) -> None:
    base, predecessor = tmp_path / "base", tmp_path / "predecessor"
    (base / "eval_sidecars").mkdir(parents=True)
    (predecessor / "eval_sidecars").mkdir(parents=True)
    base_row = _row(answer="base")
    predecessor_row = _row(answer="predecessor")
    _write_jsonl(base / "eval_sidecars/question_results.e8-t2-r2.jsonl", [base_row])
    _write_jsonl(
        predecessor / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl",
        [predecessor_row],
    )
    with pytest.raises(ValueError, match="sources conflict"):
        RETRY._saved_rows(predecessor, base)


def _clean_row(ordinal: int) -> dict:
    return {
        "row_type": "question_result",
        "ordinal": ordinal,
        "answer": f"answer-{ordinal}",
        "started_at_s": 30.0,
        "ended_at_s": 31.0,
        "result": {
            "qid": f"q{ordinal}",
            "question_id": f"q{ordinal}",
            "error": False,
            "tokens_generated": 2,
            "route": "frontdoor",
        },
    }


def _bind_tree(root: Path) -> dict[str, str]:
    hashes = {
        str(path.relative_to(root)): RETRY.sha256_path(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "source_binding.json"
    }
    RETRY.RECOVERY._write_json(
        root / "source_binding.json",
        {
            "source_sha256": hashes,
            "source_tree_sha256": RETRY.canonical_hash(hashes),
        },
    )
    return hashes


def _rebind_terminal_snapshot(root: Path) -> None:
    hashes = {
        str(path.relative_to(root)): RETRY.sha256_path(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != root / "source_binding.json"
    }
    RETRY.RECOVERY._write_json(
        root / "source_binding.json",
        {
            "source_sha256": hashes,
            "source_tree_sha256": RETRY.canonical_hash(hashes),
        },
    )


def _mixed_chain_fixture(tmp_path: Path) -> tuple[Path, dict, list[dict], dict[int, dict]]:
    root = tmp_path / "mixed"
    original = root / "predecessor_snapshot"
    original.mkdir(parents=True)
    generation = [0, 1, 2, 3]
    questions = [
        {"qid": f"q{ordinal}", "scoring_method": "llm_judge"}
        for ordinal in generation
    ]
    race = {
        **_row(),
        "ordinal": 0,
        "started_at_s": 4.0,
        "ended_at_s": 6.0,
        "result": {**_row()["result"], "qid": "q0", "question_id": "q0"},
    }
    timeout = {
        **_row(
            error="[ERROR: Inference failed: chat_completions failed: timed out]",
            answer="[ERROR: Inference failed: chat_completions failed: timed out]",
        ),
        "ordinal": 1,
        "started_at_s": 30.0,
        "ended_at_s": 31.0,
        "result": {
            **_row()["result"],
            "qid": "q1",
            "question_id": "q1",
            "error_detail": "[ERROR: Inference failed: chat_completions failed: timed out]",
        },
    }
    scorer = {
        **_row(error="scoring_unavailable: synthetic", tokens=4, answer="preserved"),
        "ordinal": 2,
        "started_at_s": 30.0,
        "ended_at_s": 31.0,
        "result": {
            **_row(error="scoring_unavailable: synthetic", tokens=4)["result"],
            "qid": "q2",
            "question_id": "q2",
            "scoring_method": "llm_judge",
        },
    }
    overlap = _clean_row(3)
    overlap["started_at_s"], overlap["ended_at_s"] = 4.0, 6.0
    original_rows = {row["ordinal"]: row for row in (race, timeout, scorer, overlap)}
    (original / "eval_sidecars").mkdir()
    _write_jsonl(
        original / "eval_sidecars/question_results.e8-t2-r2-recovery.jsonl",
        list(original_rows.values()),
    )
    original_plan = {
        "schema": RETRY.SUCCESSOR.PLAN_SCHEMA,
        "generation_ordinals": generation,
    }
    RETRY.RECOVERY._write_json(original / "partial_r2_plan.json", original_plan)
    RETRY.RECOVERY._write_json(original / "recovery_proposal.json", {"sealed": True})
    watcher = [
        _watcher("1970-01-01T00:00:00Z"),
        {
            **_watcher("1970-01-01T00:00:05Z"),
            "finished_at": "1970-01-01T00:00:05Z",
            "ok": False,
            "api_failure_class": "api_transport_error",
            "api_probe_urls": {},
            "active_load": {"tier": 2, "repetition": 2},
            "binding_matches_pre": True,
            "immutable_files_match_pre": True,
            "autopilot_active": False,
        },
        {
            **_watcher("1970-01-01T00:00:10Z"),
            "finished_at": "1970-01-01T00:00:10Z",
            "ok": False,
            "api_failure_class": "api_transport_error",
            "api_probe_urls": {},
            "active_load": {"tier": 2, "repetition": 2},
            "binding_matches_pre": True,
            "immutable_files_match_pre": True,
            "autopilot_active": False,
        },
        _watcher("1970-01-01T00:00:15Z"),
        _watcher("1970-01-01T00:00:20Z"),
    ]
    for row in watcher:
        row.setdefault("finished_at", row["started_at"])
    _write_jsonl(original / "runtime_watch.r2.successor.jsonl", watcher)
    original_hashes = _bind_tree(original)
    watcher_evidence, _ = RETRY._mixed_watcher_evidence(
        original / "runtime_watch.r2.successor.jsonl"
    )
    classified = {
        "clean": [3],
        "race_lost": [0],
        "timeout": [1],
        "outer_timeout": [],
        "scorer_replay": [2],
    }
    descriptor = {
        "schema": RETRY.MIXED_REPAIR_SCHEMA,
        "repair_runner_sha256": RETRY.HISTORICAL_MIXED_REPAIR_RUNNER_SHA256,
        "predecessor": "/immutable/original",
        "predecessor_sha256": original_hashes,
        "predecessor_tree_sha256": RETRY.canonical_hash(original_hashes),
        "allowed_class_ordinals": classified,
        "allowed_class_ordinals_sha256": {
            kind: RETRY.canonical_hash(ordinals)
            for kind, ordinals in classified.items()
        },
        "classification_sha256": RETRY.canonical_hash(classified),
        "watcher_overlap_ordinals": [0, 3],
        "watcher_overlap_ordinals_sha256": RETRY.canonical_hash([0, 3]),
        "generation_retry_ordinals": [1, 3],
        "generation_retry_ordinals_sha256": RETRY.canonical_hash([1, 3]),
        "scorer_replay_ordinals": [2],
        "scorer_replay_ordinals_sha256": RETRY.canonical_hash([2]),
        "race_retry_ordinals": [0],
        "race_retry_ordinals_sha256": RETRY.canonical_hash([0]),
        "predecessor_watcher": watcher_evidence,
        "predecessor_provenance": {
            "path": "recovery_proposal.json",
            "sha256": RETRY.sha256_path(original / "recovery_proposal.json"),
        },
    }
    current_rows = {
        0: race,
        1: _clean_row(1),
        2: _clean_row(2),
        3: _clean_row(3),
    }
    plan = {**original_plan, "mixed_tail_repair": descriptor}
    RETRY.RECOVERY._write_json(root / "partial_r2_plan.json", plan)
    evidence = {
        "schema": RETRY.MIXED_REPAIR_SCHEMA,
        "descriptor_sha256": RETRY.canonical_hash(descriptor),
        **{
            key: descriptor[key]
            for key in (
                "predecessor_tree_sha256",
                "repair_runner_sha256",
                "allowed_class_ordinals",
                "allowed_class_ordinals_sha256",
                "classification_sha256",
                "watcher_overlap_ordinals",
                "watcher_overlap_ordinals_sha256",
                "generation_retry_ordinals",
                "generation_retry_ordinals_sha256",
                "scorer_replay_ordinals",
                "scorer_replay_ordinals_sha256",
                "race_retry_ordinals",
                "race_retry_ordinals_sha256",
            )
        },
        "generation_retry": [
            {
                "ordinal": ordinal,
                "before_sha256": RETRY.canonical_hash(original_rows[ordinal]),
                "after_sha256": RETRY.canonical_hash(current_rows[ordinal]),
            }
            for ordinal in (1, 3)
        ],
        "scorer_replay": [
            {
                "ordinal": 2,
                "before_sha256": RETRY.canonical_hash(original_rows[2]),
                "after_sha256": RETRY.canonical_hash(current_rows[2]),
            }
        ],
        "remaining_race_retry_ordinals": [0],
    }
    RETRY.RECOVERY._write_json(root / RETRY.MIXED_EVIDENCE_NAME, evidence)
    RETRY.RECOVERY._write_json(
        root / "recovery_proposal.json",
        {"schema": RETRY.MIXED_PROPOSAL_SCHEMA, "mixed_tail_repair": descriptor},
    )
    return root, plan, questions, current_rows


def test_mixed_predecessor_chain_recomputes_nested_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan, questions, current_rows = _mixed_chain_fixture(tmp_path)
    monkeypatch.setattr(
        RETRY,
        "_clean",
        lambda row, _question: row.get("result", {}).get("error") is not True,
    )
    monkeypatch.setattr(RETRY, "HISTORICAL_MIXED_PREDECESSOR", root)
    monkeypatch.setattr(
        RETRY,
        "HISTORICAL_MIXED_PREDECESSOR_TREE_SHA256",
        RETRY.canonical_hash(RETRY.source_hashes(root)),
    )

    chain = RETRY.validate_mixed_predecessor(root, plan, questions, current_rows)

    assert chain is not None
    assert chain["descriptor"]["generation_retry_ordinals"] == [1, 3]
    assert chain["descriptor"]["race_retry_ordinals"] == [0]


def test_mixed_predecessor_chain_rejects_runner_or_evidence_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan, questions, current_rows = _mixed_chain_fixture(tmp_path)
    monkeypatch.setattr(
        RETRY,
        "_clean",
        lambda row, _question: row.get("result", {}).get("error") is not True,
    )
    monkeypatch.setattr(RETRY, "HISTORICAL_MIXED_PREDECESSOR", root)
    monkeypatch.setattr(
        RETRY,
        "HISTORICAL_MIXED_PREDECESSOR_TREE_SHA256",
        RETRY.canonical_hash(RETRY.source_hashes(root)),
    )
    plan["mixed_tail_repair"]["repair_runner_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="runner"):
        RETRY.validate_mixed_predecessor(root, plan, questions, current_rows)

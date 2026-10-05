"""Adversarial unit tests for the narrow E8 v5 mixed-tail repair bridge."""
from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/benchmark/prepare_e8_quality_baseline_v5_partial_r2_mixed_tail_repair.py"
SPEC = importlib.util.spec_from_file_location("e8_mixed_tail_repair_test", PATH)
assert SPEC and SPEC.loader
REPAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPAIR)


QUESTION = {"qid": "q0", "scoring_method": "llm_judge"}
RACE = "[ERROR: placement timeout role=frontdoor reason=race_lost holders=[0, 1, 2] after 90.0s]"
SCORER = "scoring_unavailable: judge unavailable"


def _row(
    *,
    error: str = RACE,
    tokens: int = 0,
    answer: str | None = None,
    scoring_method: str | None = "llm_judge",
) -> dict:
    return {
        "row_type": "question_result",
        "ordinal": 0,
        "answer": error if answer is None else answer,
        "result": {
            "qid": "q0",
            "question_id": "q0",
            "error": True,
            "error_detail": error,
            "tokens_generated": tokens,
            "route": "frontdoor",
            "scoring_method": scoring_method,
        },
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def test_exact_allowed_classes_are_disjoint() -> None:
    race = _row(scoring_method=None)
    timeout = _row(error=REPAIR.TIMEOUT_ERROR, answer=REPAIR.TIMEOUT_ERROR, scoring_method="substring")
    scorer = _row(error=SCORER, tokens=1090, answer="preserved model answer")

    assert REPAIR._classify(race, QUESTION) == "race_lost"
    assert REPAIR._classify(timeout, QUESTION) == "timeout"
    assert REPAIR._classify(scorer, QUESTION) == "scorer_replay"
    assert not REPAIR._timeout(scorer, QUESTION)
    assert not REPAIR._scorer_only(timeout, QUESTION)


def _outer_timeout_row(**overrides: object) -> dict:
    row = _row(error="timed out", answer="", scoring_method=None)
    row.pop("answer")
    row["answer"] = ""
    row.update({"started_at_s": 100.0, "ended_at_s": 400.01, "elapsed_s": 300.01})
    row["result"] = {
        "qid": "q0", "question_id": "q0", "error": True,
        "error_detail": "timed out", "tokens_generated": 0, "latency_ms": 300010,
    }
    for key, value in overrides.items():
        if key.startswith("result_"):
            row["result"][key.removeprefix("result_")] = value
        else:
            row[key] = value
    return row


def test_outer_timeout_requires_the_sealed_unrouted_300_second_shape() -> None:
    assert REPAIR._classify(_outer_timeout_row(), QUESTION) == "outer_timeout"


@pytest.mark.parametrize(
    "overrides",
    [
        {"result_tokens_generated": False},
        {"result_route": None},
        {"answer": "unexpected"},
        {"elapsed_s": 299.0},
        {"ended_at_s": 399.0},
        {"result_latency_ms": 299000},
        {"started_at_s": False},
    ],
)
def test_outer_timeout_lookalikes_fail_closed(overrides: dict) -> None:
    with pytest.raises(ValueError, match="unapproved"):
        REPAIR._classify(_outer_timeout_row(**overrides), QUESTION)


@pytest.mark.parametrize(
    "row",
    [
        _row(error="timed out", answer=""),
        _row(error=REPAIR.TIMEOUT_ERROR, tokens=1, answer=REPAIR.TIMEOUT_ERROR),
        _row(error=SCORER, tokens=0, answer="preserved model answer"),
        _row(error=SCORER, tokens=2, answer="", scoring_method="llm_judge"),
    ],
)
def test_lookalike_errors_are_refused(row: dict) -> None:
    with pytest.raises(ValueError, match="unapproved"):
        REPAIR._classify(row, QUESTION)


def test_timeout_and_scorer_repairs_have_separate_execution_sets() -> None:
    timeout = _row(error=REPAIR.TIMEOUT_ERROR, answer=REPAIR.TIMEOUT_ERROR, scoring_method="substring")
    scorer = _row(error=SCORER, tokens=1090, answer="preserved model answer")
    classifications = {
        138: REPAIR._classify(timeout, QUESTION),
        224: REPAIR._classify(scorer, QUESTION),
    }
    scorer_targets = [ordinal for ordinal, kind in classifications.items() if kind == "scorer_replay"]
    generation_targets = [ordinal for ordinal, kind in classifications.items() if kind == "timeout"]

    assert scorer_targets == [224]
    assert generation_targets == [138]
    assert set(scorer_targets).isdisjoint(generation_targets)


def test_terminal_execution_sets_are_derived_without_fixed_counts() -> None:
    classified = {
        "clean": [246, 249, 250, 281, 282, 400],
        "race_lost": [97, 203, 279, 401],
        "timeout": [138, 253, 402],
        "outer_timeout": [],
        "scorer_replay": [224, 403],
    }
    overlap = [246, 249, 250, 279, 281, 282]

    generation, scorer, race = REPAIR._execution_sets(classified, overlap)

    assert generation == [138, 246, 249, 250, 253, 281, 282, 402]
    assert scorer == [224, 403]
    assert race == [97, 203, 279, 401]
    assert set(generation).isdisjoint(scorer)
    assert set(generation).isdisjoint(race)
    assert set(scorer).isdisjoint(race)


def test_reload_overlap_is_derived_from_sealed_execution_times() -> None:
    watcher = {
        "failure_intervals": [
            {"started_at": "2026-01-01T00:00:05Z", "finished_at": "2026-01-01T00:00:15Z"}
        ]
    }
    affected = {"started_at_s": REPAIR._timestamp("2026-01-01T00:00:00Z"), "ended_at_s": REPAIR._timestamp("2026-01-01T00:00:20Z")}
    unaffected = {"started_at_s": REPAIR._timestamp("2026-01-01T00:00:16Z"), "ended_at_s": REPAIR._timestamp("2026-01-01T00:00:20Z")}

    assert REPAIR._overlaps_reload(affected, watcher)
    assert not REPAIR._overlaps_reload(unaffected, watcher)


def test_sidecar_rewrite_preserves_every_unrelated_byte(tmp_path: Path) -> None:
    original = [
        b'{"row_type":"batch_start", "spaced": true}\r\n',
        b'{"answer":"old", "ordinal":0, "result":{"qid":"q0"}, "row_type":"question_result"}\n',
        b'{"row_type":"opaque", "value":"unchanged"}\n',
    ]
    source = tmp_path / "source.jsonl"
    source.write_bytes(b"".join(original))
    lines, rows = REPAIR._rows_with_bytes(source)
    replacement = {**rows[0][1], "answer": "new"}
    destination = tmp_path / "destination.jsonl"

    REPAIR._rewrite_target_rows(destination, lines, rows, {0: replacement})

    output = destination.read_bytes().splitlines(keepends=True)
    assert output[0] == original[0]
    assert output[2] == original[2]
    assert json.loads(output[1])["answer"] == "new"


def test_audit_only_execute_has_no_generation_path() -> None:
    source = inspect.getsource(REPAIR.execute)

    assert "_generate_with_watcher" not in source
    assert "audit-only" in source


def test_journal_copy_removes_only_replaced_ordinals(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    original = [
        b'{"ordinal":1, "response":"keep"}\r\n',
        b'{"ordinal":224, "response":"replace-scorer"}\n',
        b'{"ordinal":246, "response":"replace-generation"}\n',
        b'{"ordinal":2, "response":"keep"}\n',
    ]
    source.write_bytes(b"".join(original))
    destination = tmp_path / "destination.jsonl"

    REPAIR._copy_journal_without_targets(source, destination, {224, 246})

    assert destination.read_bytes() == original[0] + original[3]


def test_wrong_tree_hash_is_refused_before_artifact_reads(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "immutable.txt").write_text("before")
    expected = REPAIR.canonical_hash(REPAIR.source_hashes(source))
    (source / "immutable.txt").write_text("after")

    with pytest.raises(ValueError, match="explicit terminal tree hash"):
        REPAIR.build_plan(source, expected)


def test_completed_predecessor_is_not_a_terminal_failed_input(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "r2_complete.json").write_text("{}\n")
    expected = REPAIR.canonical_hash(REPAIR.source_hashes(source))

    with pytest.raises(ValueError, match="terminal failed successor"):
        REPAIR.build_plan(source, expected)


def test_terminal_failure_ledger_rejects_unapproved_failure(tmp_path: Path) -> None:
    path = tmp_path / "generation_failed_attempts.T2.r2.jsonl"
    _write_jsonl(path, [{"failures": [{"ordinal": 9, "sidecar_sha256": "x"}], "disposition": "failed_closed_no_automatic_retry"}])

    with pytest.raises(ValueError, match="failure ledger"):
        REPAIR._require_terminal_failure_ledger(tmp_path, [])


def _watcher_row(started_at: str, *, ok: bool, failure_class: str | None = None) -> dict:
    return {
        "started_at": started_at,
        "finished_at": started_at,
        "ok": ok,
        "api_failure_class": failure_class,
        "api_probe_urls": {} if not ok else {"frontdoor": "bound"},
        "active_load": {"tier": 2, "repetition": 2} if not ok else None,
        "binding_matches_pre": True,
        "immutable_files_match_pre": True,
        "autopilot_active": False,
        "runtime_artifacts": {"server": {"identity": "bound"}},
    }


def test_bounded_reload_watcher_is_audited_but_admitted(tmp_path: Path) -> None:
    watcher = tmp_path / "runtime_watch.r2.successor.jsonl"
    rows = [
        _watcher_row("2026-01-01T00:00:00Z", ok=True),
        _watcher_row("2026-01-01T00:00:05Z", ok=False, failure_class="api_transport_error"),
        _watcher_row("2026-01-01T00:00:10Z", ok=False, failure_class="api_transport_error"),
        _watcher_row("2026-01-01T00:00:15Z", ok=False, failure_class="api_transport_error"),
        _watcher_row("2026-01-01T00:00:20Z", ok=True),
    ]
    _write_jsonl(watcher, rows)

    evidence = REPAIR._require_bounded_reload_watcher(watcher)

    assert evidence["status"] == "bounded_api_reload_interruption"
    assert evidence["failed_sample_indexes"] == [1, 2, 3]


def test_multiple_bounded_reload_groups_are_derived(tmp_path: Path) -> None:
    watcher = tmp_path / "runtime_watch.r2.successor.jsonl"
    states = [
        (True, None),
        (False, "api_transport_error"),
        (False, "api_transport_error"),
        (True, None),
        (False, "api_transport_error"),
        (False, "api_transport_error"),
        (False, "api_transport_error"),
        (True, None),
    ]
    rows = [
        _watcher_row(
            f"2026-01-01T00:00:{index * 5:02d}Z",
            ok=ok,
            failure_class=failure_class,
        )
        for index, (ok, failure_class) in enumerate(states)
    ]
    _write_jsonl(watcher, rows)

    evidence = REPAIR._require_bounded_reload_watcher(watcher)

    assert evidence["failed_sample_groups"] == [[1, 2], [4, 5, 6]]
    assert evidence["failure_intervals"] == [
        {
            "started_at": "2026-01-01T00:00:05Z",
            "finished_at": "2026-01-01T00:00:10Z",
        },
        {
            "started_at": "2026-01-01T00:00:20Z",
            "finished_at": "2026-01-01T00:00:30Z",
        },
    ]
    gap_row = {
        "started_at_s": REPAIR._timestamp("2026-01-01T00:00:07Z"),
        "ended_at_s": REPAIR._timestamp("2026-01-01T00:00:08Z"),
    }
    assert REPAIR._overlaps_reload(gap_row, evidence)


def test_reload_group_over_thirty_seconds_is_rejected(tmp_path: Path) -> None:
    watcher = tmp_path / "runtime_watch.r2.successor.jsonl"
    rows = [
        _watcher_row("2026-01-01T00:00:00Z", ok=True),
        _watcher_row(
            "2026-01-01T00:00:05Z",
            ok=False,
            failure_class="api_transport_error",
        ),
        _watcher_row(
            "2026-01-01T00:00:10Z",
            ok=False,
            failure_class="api_transport_error",
        ),
        _watcher_row("2026-01-01T00:00:15Z", ok=True),
        _watcher_row("2026-01-01T00:00:20Z", ok=True),
    ]
    rows[2]["finished_at"] = "2026-01-01T00:00:36Z"
    _write_jsonl(watcher, rows)

    with pytest.raises(ValueError, match="unapproved contamination"):
        REPAIR._require_bounded_reload_watcher(watcher)


def test_terminal_failure_ledger_uses_sidecar_completion_order() -> None:
    first = _row(error=SCORER, tokens=3, answer="preserved")
    first["ordinal"] = 224
    second = _row(error=REPAIR.TIMEOUT_ERROR, answer=REPAIR.TIMEOUT_ERROR)
    second["ordinal"] = 138
    sidecars = {138: (11, second), 224: (4, first)}
    kinds = {138: "timeout", 224: "scorer_replay"}

    failures = REPAIR._terminal_failures(sidecars, kinds)

    assert [row["ordinal"] for row in failures] == [224, 138]
    assert failures == [
        {"ordinal": 224, "sidecar_sha256": REPAIR.canonical_hash(first)},
        {"ordinal": 138, "sidecar_sha256": REPAIR.canonical_hash(second)},
    ]


def test_repaired_race_ledger_uses_sidecar_completion_order(tmp_path: Path) -> None:
    first = _row(error=REPAIR.RACE.RECOVERY.RACE_LOST_PREFIX + "x", answer="")
    first["ordinal"] = 279
    second = _row(error=REPAIR.RACE.RECOVERY.RACE_LOST_PREFIX + "y", answer="")
    second["ordinal"] = 97
    sidecars = {97: (11, second), 279: (4, first)}
    ledger = tmp_path / "generation_failed_attempts.T2.r2.jsonl"

    REPAIR._terminal_race_ledger(ledger, sidecars, [97, 279])

    entries = REPAIR.V4.load_jsonl(ledger)
    assert [row["ordinal"] for row in entries[0]["failures"]] == [279, 97]
    assert entries[0]["failures"] == [
        {"ordinal": 279, "sidecar_sha256": REPAIR.canonical_hash(first)},
        {"ordinal": 97, "sidecar_sha256": REPAIR.canonical_hash(second)},
    ]


def test_unapproved_watcher_failure_is_rejected_by_predecessor_contract(tmp_path: Path) -> None:
    watcher = tmp_path / "runtime_watch.r2.successor.jsonl"
    rows = [
        _watcher_row("2026-01-01T00:00:00Z", ok=True),
        _watcher_row("2026-01-01T00:00:05Z", ok=False, failure_class="api_request_error"),
        _watcher_row("2026-01-01T00:00:10Z", ok=False, failure_class="api_transport_error"),
        _watcher_row("2026-01-01T00:00:15Z", ok=False, failure_class="api_transport_error"),
        _watcher_row("2026-01-01T00:00:20Z", ok=True),
    ]
    _write_jsonl(watcher, rows)

    with pytest.raises(ValueError, match="unapproved contamination"):
        REPAIR._require_bounded_reload_watcher(watcher)


def test_output_collision_stops_before_predecessor_validation(tmp_path: Path) -> None:
    output = tmp_path / "occupied"
    output.mkdir()
    args = type("Args", (), {
        "output_dir": output,
        "source_dir": tmp_path / "not-read",
        "expected_source_tree_sha256": "0" * 64,
    })()

    with pytest.raises(FileExistsError, match="output namespace already exists"):
        REPAIR.execute(args)


def test_historical_mixed_tail_bridge_cannot_execute(tmp_path: Path) -> None:
    args = type("Args", (), {
        "output_dir": tmp_path / "new-output",
        "source_dir": tmp_path / "source",
        "expected_source_tree_sha256": "0" * 64,
    })()

    with pytest.raises(RuntimeError, match="audit-only"):
        REPAIR.execute(args)
    assert not args.output_dir.exists()

from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

# NIB2-75 (2026-09-23): tests that needed the retired E8 sealed bundles were removed per OP-19.

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/benchmark/final_c1_retry.py"
SPEC = importlib.util.spec_from_file_location("e8_final_c1_retry_test", PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


@pytest.fixture(autouse=True)
def _clean_pinned_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_ratifier = tmp_path / "original-ratifier.sh"
    canonical_ratifier = tmp_path / "superseding-ratifier.sh"
    capacityfix_ratifier = tmp_path / "capacityfix-ratifier.sh"
    original_ratifier.write_text("#!/bin/bash\n", encoding="utf-8")
    canonical_ratifier.write_text("#!/bin/bash\n", encoding="utf-8")
    capacityfix_ratifier.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setattr(RUNNER, "ORIGINAL_RATIFIER", original_ratifier)
    monkeypatch.setattr(RUNNER, "SUPERSEDING_RATIFIER", canonical_ratifier)
    monkeypatch.setattr(RUNNER, "CANONICAL_RATIFIER", capacityfix_ratifier)
    monkeypatch.setattr(
        RUNNER,
        "_runtime_git_identity",
        lambda _repository: {
            "runtime_top": str(RUNNER.ROOT),
            "canonical_top": str(RUNNER.CANONICAL_REPOSITORY),
            "same_repository": True,
            "commit": "a" * 40,
            "tree": "b" * 40,
            "clean": True,
        },
    )
    _install_historical_receipts(tmp_path, monkeypatch)


def _install_historical_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Write the original and superseding receipts against the current SOURCE."""
    original_path = tmp_path / "original-receipt.json"
    original_path.write_text(
        json.dumps(_original_receipt(), sort_keys=True) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(RUNNER, "ORIGINAL_RECEIPT", original_path)
    monkeypatch.setattr(
        RUNNER, "ORIGINAL_RECEIPT_SHA256", RUNNER.sha256_path(original_path)
    )
    superseding_path = tmp_path / "superseding-receipt.json"
    superseding_path.write_text(
        json.dumps(_superseding_receipt(), sort_keys=True) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(RUNNER, "SUPERSEDING_RECEIPT", superseding_path)
    monkeypatch.setattr(
        RUNNER, "SUPERSEDING_RECEIPT_SHA256", RUNNER.sha256_path(superseding_path)
    )


def _common_receipt(*, schema: str, attestation: str, ratifier: Path) -> dict:
    return {
        "schema": schema,
        "status": "ratified",
        "protocol_id": RUNNER.PROTOCOL_ID,
        "ratified_at": "2026-07-28T20:00:00Z",
        "human_attestation": attestation,
        "amendment_script": {
            "path": str(ratifier),
            "sha256": RUNNER.sha256_path(ratifier),
        },
        "failed_race_evidence": {
            "namespace": str(RUNNER.SOURCE),
            "canonical": True,
            "files": RUNNER.FAILED_RACE_FILES,
            "recorded_trees": {
                "plan_failed_source_tree_sha256": "92241f793c254dcf71dfca452f8cc50416d2fb1410698584b514ff3c14c5571a",
                "proposal_source_tree_sha256": "b821900094e866027d9a1561b21d91eb09f6a02ff92b8d91b133df57c7d5ce2d",
            },
            "failed_timeout_sidecars": (
                "97:a550c07752f8dedc0fdf5c4582b587c90f3b624405ed1454f628e523c100cae9,"
                "279:a41be1b012bb33475a5d8c9fd2e810c5b6dab651d123e3006f07cfc3f7fc835e"
            ),
        },
        "source": {
            "path": str(RUNNER.SOURCE),
            "tree_sha256": RUNNER.SOURCE_TREE_SHA256,
        },
        "authorization": RUNNER._receipt_contract(),
        "non_authorizations": {
            "no_inference_by_ratifier": True,
            "no_lineup_mutation": True,
            "no_state_write": True,
        },
    }


def _original_receipt() -> dict:
    receipt = _common_receipt(
        schema=RUNNER.ORIGINAL_RECEIPT_SCHEMA,
        attestation=RUNNER.ORIGINAL_ATTESTATION,
        ratifier=RUNNER.ORIGINAL_RATIFIER,
    )
    receipt["instrument"] = RUNNER._provenance_instrument(
        commit=RUNNER.ORIGINAL_ORCH_COMMIT,
        tree=RUNNER.ORIGINAL_ORCH_TREE,
        runner_sha256=RUNNER.ORIGINAL_RUNNER_SHA256,
    )
    return receipt


def _superseding_receipt() -> dict:
    receipt = _common_receipt(
        schema=RUNNER.SUPERSEDING_RECEIPT_SCHEMA,
        attestation=RUNNER.SUPERSEDING_ATTESTATION,
        ratifier=RUNNER.SUPERSEDING_RATIFIER,
    )
    receipt["supersedes"] = {
        "path": str(RUNNER.ORIGINAL_RECEIPT),
        "sha256": RUNNER.ORIGINAL_RECEIPT_SHA256,
        "schema": RUNNER.ORIGINAL_RECEIPT_SCHEMA,
        "human_attestation": RUNNER.ORIGINAL_ATTESTATION,
    }
    receipt["instrument"] = {
        **RUNNER._provenance_instrument(
            commit=RUNNER.SUPERSEDING_ORCH_COMMIT,
            tree=RUNNER.SUPERSEDING_ORCH_TREE,
            runner_sha256=RUNNER.SUPERSEDING_RUNNER_SHA256,
        ),
    }
    return receipt


def test_execute_fault_after_output_creation_is_terminally_sealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    base = source / "source_snapshot"
    base.mkdir(parents=True)
    output = tmp_path / "candidate"
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", str(RUNNER.CONCURRENCY))
    monkeypatch.setattr(
        RUNNER,
        "build_plan",
        lambda *_args, **_kwargs: {"t1_core_id": "core"},
    )
    monkeypatch.setattr(
        RUNNER.V5,
        "parse_args",
        lambda _argv: SimpleNamespace(api_url="http://test", http_timeout_s=1),
    )
    monkeypatch.setattr(RUNNER.RECOVERY, "_capture_recovery_claim", lambda _args: {})
    monkeypatch.setattr(RUNNER, "_claim_is_exact_q3", lambda _claim: True)
    monkeypatch.setattr(RUNNER.V4, "runtime_binding", lambda _args: {})
    monkeypatch.setattr(
        RUNNER.RECOVERY,
        "preflight_frontdoor_capacity",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        RUNNER,
        "validate_failed_source",
        lambda _source: {
            "base": base,
            "base_hashes": {},
            "hashes": {},
            "journal": {},
        },
    )
    monkeypatch.setattr(RUNNER.RECOVERY, "_load_vector", lambda *_args: {})
    monkeypatch.setattr(RUNNER.RECOVERY, "_reconstruct_questions", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(RUNNER, "source_hashes", lambda _source: {})
    monkeypatch.setattr(RUNNER, "SOURCE_TREE_SHA256", RUNNER.canonical_hash({}))
    monkeypatch.setattr(
        RUNNER,
        "_write_json",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("injected output fault")),
    )

    with pytest.raises(RuntimeError, match="injected output fault"):
        RUNNER.execute(
            SimpleNamespace(
                source_dir=source,
                output_dir=output,
                api_url="http://test",
                amendment_receipt=tmp_path / "unused.json",
            )
        )

    assert RUNNER.V4.load_json(output / "run_seal.json")["status"] == (
        "terminal_aborted_no_admission"
    )
    assert RUNNER.V4.load_json(output / "writer_abort.json")["writer"] == (
        "final_c1_retry"
    )


def _receipt() -> dict:
    receipt = _common_receipt(
        schema=RUNNER.RECEIPT_SCHEMA,
        attestation=RUNNER.ATTESTATION,
        ratifier=RUNNER.CANONICAL_RATIFIER,
    )
    receipt["supersedes"] = {
        "path": str(RUNNER.SUPERSEDING_RECEIPT),
        "sha256": RUNNER.SUPERSEDING_RECEIPT_SHA256,
        "schema": RUNNER.SUPERSEDING_RECEIPT_SCHEMA,
        "human_attestation": RUNNER.SUPERSEDING_ATTESTATION,
    }
    receipt["instrument"] = {
        **RUNNER._provenance_instrument(
            commit="a" * 40,
            tree="b" * 40,
            runner_sha256=RUNNER.sha256_path(PATH),
            recovery_helper_sha256=RUNNER.sha256_path(RUNNER.RECOVERY_PATH),
        ),
        "validator": {
            "path": "scripts/benchmark/final_c1_validator.py",
            "sha256": RUNNER.sha256_path(RUNNER.VALIDATOR_PATH),
        },
    }
    receipt["capacity_fix"] = RUNNER._capacity_fix_contract()
    return receipt


def _write_receipt(path: Path, receipt: dict | None = None) -> Path:
    path.write_text(json.dumps(receipt or _receipt()) + "\n", encoding="utf-8")
    RUNNER.CANONICAL_RECEIPT = path
    return path


@pytest.mark.parametrize("receipt_name", ["ORIGINAL_RECEIPT", "SUPERSEDING_RECEIPT"])
def test_historical_receipts_cannot_authorize_execution(receipt_name: str) -> None:
    with pytest.raises(ValueError, match="capacity-fix receipt is required"):
        RUNNER.validate_receipt(
            getattr(RUNNER, receipt_name), require_execution=True
        )


@pytest.mark.parametrize("receipt_name", ["ORIGINAL_RECEIPT", "SUPERSEDING_RECEIPT"])
def test_historical_receipts_build_planning_only_plans(
    receipt_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # build_plan hashes the predecessor watcher and failed-attempt sidecars
    # straight from SOURCE. The real sealed race namespace under
    # /mnt/raid0/llm/epyc-root/artifacts/operator/ is historical host evidence
    # that is no longer present, so bind SOURCE to a hermetic stand-in and
    # re-issue the historical receipts against it (NIB2-69 triage 2026-09-15).
    source = tmp_path / "failed-race-source"
    source.mkdir()
    (source / "runtime_watch.r2.race_retry.jsonl").write_text("{}\n", encoding="utf-8")
    (source / "generation_failed_attempts.T2.r2.jsonl").write_text(
        "{}\n", encoding="utf-8"
    )
    monkeypatch.setattr(RUNNER, "SOURCE", source)
    _install_historical_receipts(tmp_path, monkeypatch)
    monkeypatch.setattr(
        RUNNER,
        "validate_failed_source",
        lambda _source: {
            "plan": {"core_id": "core", "t1_core_id": "t1"},
            "hashes": {},
            "base_hashes": {},
            "journal": {},
        },
    )
    plan = RUNNER.build_plan(Path("/unused"), getattr(RUNNER, receipt_name))
    assert plan["execution_authorized"] is False


def test_capacityfix_receipt_accepts_exact_clean_linked_worktree(tmp_path: Path) -> None:
    receipt = RUNNER.validate_receipt(
        _write_receipt(tmp_path / "capacityfix.json"), require_execution=True
    )
    assert receipt["schema"] == RUNNER.RECEIPT_SCHEMA
    assert receipt["capacity_fix"] == RUNNER._capacity_fix_contract()


def test_capacityfix_receipt_rejects_bad_superseding_ancestry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    superseding = _superseding_receipt()
    superseding["supersedes"]["sha256"] = "0" * 64
    bad_path = tmp_path / "bad-superseding.json"
    bad_path.write_text(json.dumps(superseding) + "\n", encoding="utf-8")
    monkeypatch.setattr(RUNNER, "SUPERSEDING_RECEIPT", bad_path)
    monkeypatch.setattr(
        RUNNER, "SUPERSEDING_RECEIPT_SHA256", RUNNER.sha256_path(bad_path)
    )
    with pytest.raises(ValueError, match="superseding final-c1 receipt differs"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "capacityfix.json"))


def test_capacityfix_receipt_rejects_altered_capacity_fix_contract(tmp_path: Path) -> None:
    receipt = _receipt()
    receipt["capacity_fix"]["helper"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "receipt.json", receipt))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("legacy_default_expected_concurrency", 1),
        ("final_c1_expected_concurrency", 3),
        ("helper", {"path": "scripts/benchmark/wrong.py", "sha256": "0" * 64}),
    ],
)
def test_capacityfix_receipt_rejects_capacity_contract_mutation(
    tmp_path: Path, field: str, value: object
) -> None:
    receipt = _receipt()
    receipt["capacity_fix"][field] = value
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "receipt.json", receipt))


def test_capacityfix_receipt_rejects_recovery_helper_instrument_drift(
    tmp_path: Path,
) -> None:
    receipt = _receipt()
    receipt["instrument"]["recovery_helper"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "receipt.json", receipt))


def test_source_alias_and_unreviewed_namespace_are_rejected(tmp_path: Path) -> None:
    with pytest.raises((FileNotFoundError, ValueError)):
        RUNNER.validate_failed_source(tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generation_concurrency", 3),
        ("request_timeout_s", 301),
        ("ordinals", [279, 97]),
        ("qids", list(reversed(RUNNER.RETRY_QIDS))),
        ("region_claim_regions", ["q2"]),
        ("no_auto_retry", False),
    ],
)
def test_receipt_rejects_broadened_authorization(
    tmp_path: Path, field: str, value: object
) -> None:
    receipt = _receipt()
    receipt["authorization"][field] = value
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "receipt.json", receipt))


def test_receipt_rejects_source_or_instrument_drift(tmp_path: Path) -> None:
    receipt = _receipt()
    receipt["source"]["tree_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "source.json", receipt))
    receipt = _receipt()
    receipt["instrument"]["runner"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "runner.json", receipt))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "/tmp/unrelated-orchestrator"),
        ("commit", "0" * 40),
        ("tree", "0" * 40),
    ],
)
def test_receipt_rejects_wrong_repository_commit_or_tree(
    tmp_path: Path, field: str, value: str
) -> None:
    receipt = _receipt()
    receipt["instrument"][field] = value
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / f"{field}.json", receipt))


def test_receipt_rejects_dirty_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = {
        "runtime_top": str(RUNNER.ROOT),
        "canonical_top": str(RUNNER.CANONICAL_REPOSITORY),
        "same_repository": True,
        "commit": "a" * 40,
        "tree": "b" * 40,
        "clean": False,
    }
    monkeypatch.setattr(RUNNER, "_runtime_git_identity", lambda _repository: identity)
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "dirty.json"))


def test_receipt_accepts_exact_clean_linked_worktree(tmp_path: Path) -> None:
    receipt = RUNNER.validate_receipt(_write_receipt(tmp_path / "linked.json"))
    assert receipt["instrument"]["commit"] == "a" * 40
    assert receipt["instrument"]["tree"] == "b" * 40


def test_receipt_rejects_unrelated_repo_even_with_same_files_and_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        RUNNER,
        "_runtime_git_identity",
        lambda _repository: {
            "runtime_top": "/tmp/copied-repository",
            "canonical_top": str(RUNNER.CANONICAL_REPOSITORY),
            "same_repository": False,
            "commit": "a" * 40,
            "tree": "b" * 40,
            "clean": True,
        },
    )
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "unrelated.json"))


def test_receipt_rejects_copy_outside_canonical_namespace(tmp_path: Path) -> None:
    canonical = _write_receipt(tmp_path / "canonical.json")
    copied = tmp_path / "copied.json"
    copied.write_bytes(canonical.read_bytes())
    RUNNER.CANONICAL_RECEIPT = canonical
    with pytest.raises(ValueError, match="missing or unsafe"):
        RUNNER.validate_receipt(copied)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol_id", "wrong"),
        ("ratified_at", "not-a-timestamp"),
    ],
)
def test_receipt_rejects_protocol_or_timestamp_mutation(
    tmp_path: Path, field: str, value: str
) -> None:
    receipt = _receipt()
    receipt[field] = value
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / f"{field}.json", receipt))


def test_receipt_rejects_extra_top_level_or_instrument_keys(tmp_path: Path) -> None:
    receipt = _receipt()
    receipt["ignored"] = True
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "extra-top.json", receipt))
    receipt = _receipt()
    receipt["instrument"]["ignored"] = True
    with pytest.raises(ValueError, match="exact authorization"):
        RUNNER.validate_receipt(_write_receipt(tmp_path / "extra-instrument.json", receipt))


def _questions() -> list[dict]:
    return [{"qid": f"q{ordinal}"} for ordinal in range(500)]


def _clean(ordinal: int) -> tuple[dict, dict]:
    qid = RUNNER.RETRY_QIDS[RUNNER.RETRY_ORDINALS.index(ordinal)]
    response = {"qid": qid, "answer": "ok", "error": None}
    sidecar = {
        "row_type": "question_result",
        "ordinal": ordinal,
        "elapsed_s": 1.0,
        "result": {
            "qid": qid,
            "question_id": qid,
            "correct": False,
            "tokens_generated": 1,
            "route": "frontdoor",
        },
    }
    return response, sidecar


def _timeout(ordinal: int) -> tuple[dict, dict]:
    qid = RUNNER.RETRY_QIDS[RUNNER.RETRY_ORDINALS.index(ordinal)]
    response = {"qid": qid, "answer": "", "error": "timed out"}
    sidecar = {
        "row_type": "question_result",
        "ordinal": ordinal,
        "answer": "",
        "elapsed_s": 90.0,
        "result": {
            "qid": qid,
            "question_id": qid,
            "correct": False,
            "error": True,
            "error_detail": "timed out",
            "tokens_generated": 0,
            "latency_ms": 90000,
            "route": "frontdoor",
            "partial": False,
            "degraded": False,
            "failure_provenance": {
                "schema": RUNNER.RACE.FAILURE_PROVENANCE_SCHEMA,
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
            },
        },
    }
    return response, sidecar


def _run_schedule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcomes: dict[int, tuple[dict, dict]],
) -> tuple[list[int], list[dict], dict[int, dict], dict | None]:
    calls: list[int] = []

    def generate(**kwargs):
        ordinal = kwargs["ordinal"]
        calls.append(ordinal)
        return copy.deepcopy(outcomes[ordinal])

    monkeypatch.setattr(RUNNER, "_generate_one", generate)
    monkeypatch.setattr(
        RUNNER.V5,
        "validate_clean_sidecar_result",
        lambda response, *_args, **_kwargs: response.get("error") is None,
    )
    questions = _questions()
    questions[97]["qid"], questions[279]["qid"] = RUNNER.RETRY_QIDS
    rows: dict[int, dict] = {}
    attempts, sidecars, failure = RUNNER._collect_schedule(
        output=tmp_path,
        watcher=object(),
        watcher_path=tmp_path / "runtime_watch.jsonl",
        runner_args=SimpleNamespace(),
        questions=questions,
        original_sidecars={97: {}, 279: {}},
        journal_path=tmp_path / "journal.jsonl",
        rows=rows,
    )
    return calls, attempts, rows, failure


def test_schedule_runs_exactly_two_clean_rows_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls, attempts, rows, failure = _run_schedule(
        tmp_path,
        monkeypatch,
        {97: _clean(97), 279: _clean(279)},
    )
    assert calls == [97, 279]
    assert [row["ordinal"] for row in attempts] == [97, 279]
    assert set(rows) == {97, 279}
    assert failure is None


def test_repeated_timeout_stops_schedule_without_second_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls, attempts, rows, failure = _run_schedule(
        tmp_path,
        monkeypatch,
        {97: _timeout(97), 279: _clean(279)},
    )
    assert calls == [97]
    assert [row["outcome"] for row in attempts] == ["terminal_failure"]
    assert rows == {}
    assert failure["ordinal"] == 97


def test_non_timeout_failure_is_instrument_error_not_terminal_disposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response, sidecar = _timeout(97)
    sidecar["result"]["error_detail"] = "connection reset"
    sidecar["result"]["failure_provenance"]["class"] = "backend_failure"
    with pytest.raises(RuntimeError, match="outside the ratified timeout"):
        _run_schedule(
            tmp_path,
            monkeypatch,
            {97: (response, sidecar), 279: _clean(279)},
        )
    assert not (tmp_path / RUNNER.TERMINAL_NAME).exists()


def test_structured_admission_timeout_is_wording_stable_and_other_classes_fail_closed() -> None:
    _response, sidecar = _timeout(97)
    sidecar["result"]["error_detail"] = "request deadline exceeded"
    question = {"qid": RUNNER.RETRY_QIDS[0]}
    assert RUNNER._terminal_timeout(sidecar, 97, question)

    sidecar["result"]["failure_provenance"]["code"] = "contention_timeout"
    assert not RUNNER._terminal_timeout(sidecar, 97, question)

    sidecar["result"]["failure_provenance"] = {
        "schema": RUNNER.RACE.FAILURE_PROVENANCE_SCHEMA,
        "class": "client_transport_timeout",
        "code": "read_timeout",
        "phase": "client_transport",
        "role": "frontdoor",
        "workload_class": "eval_batch",
        "max_queue_wait_ms": 90_000,
    }
    sidecar["result"]["error_detail"] = "timed out"
    assert not RUNNER._terminal_timeout(sidecar, 97, question)

    sidecar["result"]["failure_provenance"] = {
        "class": "slot_erase_timeout",
        "code": "timeout_after_slot_erase",
        "exception_class": "httpx.PoolTimeout",
        "exception_reason": "pool_timeout",
    }
    assert not RUNNER._terminal_timeout(sidecar, 97, question)


def test_historical_timeout_requires_hash_and_bound_latency_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _response, sidecar = _timeout(97)
    question = {"qid": RUNNER.RETRY_QIDS[0]}
    sidecar["result"].pop("failure_provenance")
    sidecar["elapsed_s"] = 300.0
    sidecar["result"]["error_detail"] = (
        "[ERROR: Inference failed: chat_completions failed: timed out]"
    )
    sidecar["result"]["latency_ms"] = 299000
    monkeypatch.setattr(RUNNER, "HISTORICAL_TIMEOUT_SIDECAR_SHA256", {RUNNER.canonical_hash(sidecar)})
    assert not RUNNER._terminal_timeout(sidecar, 97, question, allow_historical=True)

    sidecar["result"]["latency_ms"] = 300000
    monkeypatch.setattr(RUNNER, "HISTORICAL_TIMEOUT_SIDECAR_SHA256", {RUNNER.canonical_hash(sidecar)})
    assert RUNNER._terminal_timeout(sidecar, 97, question, allow_historical=True)


def test_cli_exposes_no_timeout_or_concurrency_override() -> None:
    with pytest.raises(SystemExit):
        RUNNER.parse_args(
            [
                "--amendment-receipt",
                "/tmp/receipt",
                "--evaltower-timeout-s",
                "301",
            ]
        )


def test_completion_metadata_is_passed_to_the_single_recovery_write() -> None:
    tree = ast.parse(PATH.read_text())
    execute = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    complete = next(
        node
        for node in ast.walk(execute)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_complete_r2"
    )
    assert any(keyword.arg == "completion_context" for keyword in complete.keywords)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_write_json"
        and node.args
        and isinstance(node.args[0], ast.BinOp)
        and isinstance(node.args[0].op, ast.Div)
        and isinstance(node.args[0].right, ast.Constant)
        and node.args[0].right.value == "r2_complete.json"
        for node in ast.walk(execute)
    )


def test_execute_passes_the_explicit_amended_c1_capacity_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    seen: dict[str, object] = {}

    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", str(RUNNER.CONCURRENCY))
    monkeypatch.setattr(RUNNER, "build_plan", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        RUNNER.V5,
        "parse_args",
        lambda _argv: SimpleNamespace(api_url="http://test", http_timeout_s=1),
    )
    monkeypatch.setattr(RUNNER.RECOVERY, "_capture_recovery_claim", lambda _args: {})
    monkeypatch.setattr(RUNNER, "_claim_is_exact_q3", lambda _claim: True)
    monkeypatch.setattr(RUNNER.V4, "runtime_binding", lambda _args: {})

    def stop_after_capacity(_binding: dict, **kwargs: object) -> dict:
        seen.update(kwargs)
        raise ValueError("capacity sentinel")

    monkeypatch.setattr(RUNNER.RECOVERY, "preflight_frontdoor_capacity", stop_after_capacity)
    with pytest.raises(ValueError, match="capacity sentinel"):
        RUNNER.execute(
            SimpleNamespace(
                output_dir=output,
                source_dir=source,
                amendment_receipt=tmp_path / "receipt.json",
                api_url="http://test",
            )
        )
    assert seen == {
        "required": RUNNER.CONCURRENCY,
        "claim": {},
        "expected_concurrency": RUNNER.CONCURRENCY,
    }


def _focused_sidecar_rows(*, label: str, qid: str) -> list[dict]:
    batch_id = "focused-batch"
    return [
        {
            "row_type": "batch_start",
            "eval_batch_id": batch_id,
            "label": label,
            "requested_n": 1,
            "concurrency": 1,
            "complete": False,
        },
        {
            "row_type": "question_result",
            "eval_batch_id": batch_id,
            "label": label,
            "requested_n": 1,
            "ordinal": 0,
            "started_at_s": 1785196801.0,
            "ended_at_s": 1785196802.0,
            "result": {"qid": qid},
        },
        {
            "row_type": "batch_complete",
            "eval_batch_id": batch_id,
            "label": label,
            "requested_n": 1,
            "completed_n": 1,
            "complete": True,
        },
    ]


def _focused_watcher(path: Path) -> Path:
    path.write_text(
        "".join(
            json.dumps(row) + "\n"
            for row in (
                {
                    "ok": True,
                    "active_load": {"tier": 2, "repetition": 2},
                    "started_at": "2026-07-28T00:00:00Z",
                    "finished_at": "2026-07-28T00:00:00Z",
                },
                {
                    "ok": True,
                    "active_load": {"tier": 2, "repetition": 2},
                    "started_at": "2026-07-28T00:00:05Z",
                    "finished_at": "2026-07-28T00:00:05Z",
                },
            )
        ),
        encoding="utf-8",
    )
    return path


def test_focused_sidecar_is_discovered_by_validated_content(tmp_path: Path) -> None:
    label = "e8-final-c1-t2-r2-o97"
    qid = RUNNER.RETRY_QIDS[0]
    path = tmp_path / "question_results.unexpected-upstream-name.jsonl"
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in _focused_sidecar_rows(label=label, qid=qid)),
        encoding="utf-8",
    )
    selected, row = RUNNER._discover_focused_sidecar(
        tmp_path,
        watcher_path=_focused_watcher(tmp_path / "watcher.jsonl"),
        label=label,
        qid=qid,
    )
    assert selected == path
    assert row["result"]["qid"] == qid


def test_focused_sidecar_rejects_ambiguous_or_wrong_contract(tmp_path: Path) -> None:
    label = "e8-final-c1-t2-r2-o97"
    qid = RUNNER.RETRY_QIDS[0]
    wrong = _focused_sidecar_rows(label=label, qid=qid)
    wrong[0]["concurrency"] = 3
    (tmp_path / "question_results.wrong.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in wrong), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="exactly one"):
        RUNNER._discover_focused_sidecar(
            tmp_path,
            watcher_path=_focused_watcher(tmp_path / "watcher.jsonl"),
            label=label,
            qid=qid,
        )

    rows = _focused_sidecar_rows(label=label, qid=qid)
    for name in ("first", "second"):
        (tmp_path / f"question_results.{name}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
    with pytest.raises(ValueError, match="exactly one"):
        RUNNER._discover_focused_sidecar(
            tmp_path,
            watcher_path=_focused_watcher(tmp_path / "watcher.jsonl"),
            label=label,
            qid=qid,
        )

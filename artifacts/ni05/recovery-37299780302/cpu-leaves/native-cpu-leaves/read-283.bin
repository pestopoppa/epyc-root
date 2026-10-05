"""Structural guards for the E8 r2 successor executor."""
from __future__ import annotations

import ast
from contextlib import nullcontext
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/benchmark/prepare_e8_quality_baseline_v5_partial_r2_successor.py"
FINALIZER_PATH = ROOT / "scripts/benchmark/finalize_e8_quality_baseline_v5_recovery_r2.py"
SPEC = importlib.util.spec_from_file_location("e8_r2_successor_test", PATH)
assert SPEC and SPEC.loader
SUCCESSOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUCCESSOR)


def test_existing_successor_namespace_refuses_before_planning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    monkeypatch.setattr(
        SUCCESSOR, "build_plan", lambda _source: pytest.fail("must not plan existing output")
    )
    with pytest.raises(FileExistsError, match="already exists"):
        SUCCESSOR.execute(SimpleNamespace(source_dir=source, output_dir=output))
    assert list(output.iterdir()) == []


def test_generation_is_not_nested_under_scorer_active_load() -> None:
    tree = ast.parse(PATH.read_text())
    execute = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute")
    nested_calls = [
        call
        for with_node in ast.walk(execute)
        if isinstance(with_node, ast.With)
        and any(isinstance(item.context_expr, ast.Call) and getattr(item.context_expr.func, "attr", None) == "active_load" for item in with_node.items)
        for call in ast.walk(with_node)
        if isinstance(call, ast.Call) and getattr(call.func, "attr", None) == "_generate_with_watcher"
    ]
    assert nested_calls == []


def test_finalizer_dispatches_successor_before_legacy_watcher_requirement() -> None:
    source = FINALIZER_PATH.read_text()
    assert source.index('if plan.get("schema") == SUCCESSOR.PLAN_SCHEMA:') < source.index(
        'required["watcher"] = intermediate / "runtime_watch.r2.jsonl"'
    )


def test_finalizer_hashes_nested_failed_source_bindings() -> None:
    source = FINALIZER_PATH.read_text()
    assert 'item != required["failed_binding"]' in source


def test_successor_admission_uses_frontdoor_capacity_not_observer_regions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Health probes may span all regions; only generated frontdoor traffic contends."""
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "compatible_frontdoor_capacity",
        lambda _instances, _live, held: (3, [{"regions": ["q0"]}, {"regions": ["q1"]}, {"regions": ["q2"]}])
        if held == {"q3"}
        else pytest.fail("claim was not passed to frontdoor admission"),
    )
    from src.runtime import instance_topology

    monkeypatch.setattr(
        instance_topology,
        "get_instance_regions",
        lambda: {
            ("frontdoor", 1): frozenset({"q0"}),
            ("frontdoor", 2): frozenset({"q1"}),
            ("frontdoor", 3): frozenset({"q2"}),
            ("worker_general", 1): frozenset({"q0", "q1", "q2", "q3"}),
        },
    )
    monkeypatch.setattr(
        instance_topology,
        "topology_idx_for_port",
        lambda role, port: {("frontdoor", 8070): 1, ("frontdoor", 8080): 2, ("frontdoor", 8180): 3}.get((role, port)),
    )
    monkeypatch.setattr(SUCCESSOR.RECOVERY, "_locked_global_regions", lambda _regions: {"q3"})
    proof = SUCCESSOR.RECOVERY.preflight_frontdoor_capacity(
        {"runtime_topology": [{"port": port, "roles": ["frontdoor"]} for port in (8070, 8080, 8180)]},
        required=3,
        claim={"claims": [{"payload": {"region": "q3"}}]},
    )
    assert proof["capacity"] == 3
    assert proof["held_global_regions"] == ["q3"]


def _patch_successor_prewrite(
    monkeypatch: pytest.MonkeyPatch,
    *,
    plan: dict[str, object],
) -> None:
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", str(SUCCESSOR.V4.CONCURRENCY))
    monkeypatch.setattr(SUCCESSOR, "build_plan", lambda _source: plan)
    monkeypatch.setattr(
        SUCCESSOR.V5,
        "parse_args",
        lambda _argv: SimpleNamespace(api_url="http://test", http_timeout_s=1),
    )
    monkeypatch.setattr(SUCCESSOR.RECOVERY, "_capture_recovery_claim", lambda _args: {})
    monkeypatch.setattr(SUCCESSOR.V4, "runtime_binding", lambda _args: {})
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "preflight_frontdoor_capacity",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_instrument_identity", lambda _args: {}
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "_load_vector",
        lambda _root, name: (
            {"questions": [{"qid": "q0"}]}
            if name == "question_vector.T2.json"
            else {"questions": [{"qid": "q0"}]}
        ),
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "_reconstruct_questions",
        lambda *_args, **_kwargs: [{"qid": "q0"}],
    )
    monkeypatch.setattr(SUCCESSOR, "source_hashes", lambda _source: {})


def test_successor_failure_after_output_creation_is_durably_aborted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    plan = {
        "failed_source_sha256": {},
        "t1_core_id": "t1",
    }
    _patch_successor_prewrite(monkeypatch, plan=plan)
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "_recovery_proposal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("proposal fault")
        ),
    )

    with pytest.raises(RuntimeError, match="proposal fault"):
        SUCCESSOR.execute(
            SimpleNamespace(source_dir=source, output_dir=output, api_url="http://test")
        )

    abort = SUCCESSOR.V4.load_json(
        output / SUCCESSOR.RECOVERY.ABORT_MARKER_NAME
    )
    assert abort["status"] == "terminal_aborted_no_admission"
    assert abort["no_admission"] is True


def test_successor_reaches_post_generation_shared_harvest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    (source / "source_snapshot").mkdir(parents=True)
    (source / "generation_judge_traces.T2.r2.jsonl").write_text(
        "", encoding="utf-8"
    )
    output = tmp_path / "output"
    plan = {
        "failed_source_sha256": {},
        "failed_source_tree_sha256": "f" * 64,
        "failed_watcher": {"eligibility": "excluded_audit_evidence"},
        "successor_runner_sha256": "a" * 64,
        "successor_watcher_path": "runtime_watch.r2.successor.jsonl",
        "t1_core_id": "t1",
        "generation_ordinals": [0],
        "imported_generation_ordinals": [],
    }
    _patch_successor_prewrite(monkeypatch, plan=plan)
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_recovery_proposal", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_bind_recovery_proposal", lambda *_args: None
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "_snapshot_source",
        lambda *_args: source / "source_snapshot",
    )
    monkeypatch.setattr(SUCCESSOR, "_copy_failed_audit", lambda *_args: None)
    monkeypatch.setattr(SUCCESSOR.V4, "load_jsonl", lambda _path: [])
    monkeypatch.setattr(SUCCESSOR, "_rows", lambda _path: {})
    monkeypatch.setattr(SUCCESSOR.RECOVERY, "_record", lambda *_args: None)
    monkeypatch.setattr(SUCCESSOR.V4, "api_health", lambda *_args: {})
    monkeypatch.setattr(SUCCESSOR.V4, "probe_url_mapping", lambda _health: {})

    class Watcher:
        fatal_error = None

        def __init__(self, *_args, **_kwargs):
            pass

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def sample(self) -> None:
            pass

        def active_load(self, **_kwargs):
            return nullcontext()

    monkeypatch.setattr(SUCCESSOR.V4, "RuntimeWatcher", Watcher)
    monkeypatch.setattr(SUCCESSOR.V4, "require_clean_watcher", lambda _watcher: None)
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_recover_saved_scorers", lambda *_args: None
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "_generate_with_watcher",
        lambda *_args: ([], [], []),
    )
    monkeypatch.setattr(SUCCESSOR.V4, "response_rows", lambda *_args: [])
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY,
        "_reconcile_generation_scorer_sidecar",
        lambda *_args: None,
    )
    captured: dict[str, object] = {}

    def harvest(path, watcher_path, rows, _journal, _questions, permitted):
        captured.update(
            {
                "path": path,
                "watcher_path": watcher_path,
                "permitted": permitted,
            }
        )
        rows[0] = {"response": {"qid": "q0"}}
        return []

    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_harvest_generation_sidecar", harvest
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_generation_targets", lambda *_args: []
    )

    def complete(root, *_args, completion_context=None):
        assert completion_context == {
            "status": "intermediate_r2_successor_complete",
            "watcher": {},
            "claim": {},
            "scorer_attempts": {},
            "scorer_attempts_sha256": None,
            "failed_watcher": plan["failed_watcher"],
        }
        SUCCESSOR.RECOVERY._write_json(root / "r2_complete.json", completion_context)

    monkeypatch.setattr(SUCCESSOR.RECOVERY, "_complete_r2", complete)
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_scorer_attempts_evidence", lambda *_args: {}
    )
    monkeypatch.setattr(
        SUCCESSOR.RECOVERY, "_watcher_evidence", lambda *_args, **_kwargs: {}
    )

    assert SUCCESSOR.execute(
        SimpleNamespace(source_dir=source, output_dir=output, api_url="http://test")
    ) == output
    assert captured["watcher_path"] == output / plan["successor_watcher_path"]
    assert captured["permitted"] == {0}

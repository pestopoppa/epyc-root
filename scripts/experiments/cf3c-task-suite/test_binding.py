"""Source-writer, policy activation, oracle separation and recovery controls."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

# Use the same source-pinned native bootstrap and wire-capture dependencies.
import test_suite
from binding import compile_cohort, digest, install_archive, validate_archive
from graph_trial import HistoryRenderer, history_projection


def test_cohort_is_prospective_paired_and_does_not_expand():
    cohort = compile_cohort()
    assert cohort == compile_cohort()
    assert len(cohort["cases"]) == 4 and len(cohort["schedule"]) == 24
    payload = {k: v for k, v in cohort.items() if k != "cohort_sha256"}
    assert cohort["cohort_sha256"] == digest(payload)
    assert cohort["automatic_extension"] is False
    for case in cohort["cases"]:
        validate_archive(case["initial_history"])
        rows = [r for r in cohort["schedule"] if r["case"] == case["id"]]
        assert {r["arm"] for r in rows} == set(test_suite.ARMS)
        assert len({r["seed"] for r in rows}) == 1
        assert case["expected"] not in case["prompt"]
        assert case["expected"] not in "".join(
            t["code"] for t in case["initial_history"]
        )
        if "paired" not in case["id"]:
            assert case["expected"] in "".join(
                t["output"] for t in case["initial_history"]
            )
    assert len({r["seed"] for r in cohort["schedule"]}) == 4


@pytest.mark.parametrize("kind", range(4))
def test_source_written_archive_activates_policies_and_preserves_recovery(
    tmp_path, monkeypatch, kind
):
    from src.features import Features, get_features, set_features
    from src.graph import context_arm_ab
    from src.graph.state import TaskState

    case = compile_cohort()["cases"][kind]
    original = copy.deepcopy(case["initial_history"])
    state = TaskState(task_id="trial", prompt=case["prompt"], context=case["prompt"])
    state.turns = 1
    repl = SimpleNamespace(task_id="trial", _session_artifact_dir=tmp_path)
    prior = get_features()
    set_features(
        Features(context_arm_ab=True, session_log=True, session_log_verbatim=True)
    )
    try:
        receipt = install_archive(state, repl, case["initial_history"])
        assert state.turns == 1
        assert [t["turn"] for t in state.history_turns] == list(range(-10, 0))
        assert receipt["scripted"] is True
        assert receipt["construction_cost_included"] is False
        log = Path(state.history_log_path).read_bytes()
        assert digest(original) == receipt["archive_sha256"]
        assert (
            "file_path=" + json.dumps(str(tmp_path / "session.verbatim.md"))
            in state.context
        )
        for turn in state.history_turns:
            begin, length = turn["output_byte_offset"], turn["output_byte_length"]
            assert log[begin : begin + length].decode() == turn["output"]
        assert case["initial_history"] == original
        monkeypatch.setattr(
            context_arm_ab, "settings", lambda: ("full_history", 16384, 0.5, set())
        )
        for arm in test_suite.ARMS:
            renderer = HistoryRenderer(context_arm_ab.render, arm)
            rendered = renderer(state)
            assert renderer.latest["active"] == (arm.startswith("A1-") or arm == "A2")
            if arm in {"A0", "A3"} and kind != 2:
                assert case["expected"] in rendered
            if arm == "A3":
                assert renderer.latest["reasoning_carrier"] is False
            assert Path(state.history_log_path).read_bytes() == log
        if kind in {0, 1}:
            for arm in ("A1-k4", "A1-k8", "A1-k12"):
                selected, _ = history_projection(state.history_turns, arm)
                assert case["expected"] not in "".join(t["output"] for t in selected)
            selected, _ = history_projection(state.history_turns, "A2")
            assert (case["expected"] in "".join(t["output"] for t in selected)) == (
                kind == 0
            )
        with pytest.raises(ValueError, match="existing native task history"):
            install_archive(state, repl, original)
    finally:
        set_features(prior)


@pytest.mark.parametrize("mutation", ("oracle", "empty", "short", "oversize"))
def test_archive_refuses_oracle_and_geometry_changes(mutation):
    archive = compile_cohort()["cases"][0]["initial_history"]
    if mutation == "oracle":
        archive[0]["expected"] = "hidden"
    elif mutation == "empty":
        archive[0]["code"] = ""
    elif mutation == "short":
        archive.pop()
    else:
        archive[0]["output"] = "x" * 1201
    with pytest.raises(ValueError):
        validate_archive(archive)


@pytest.mark.parametrize("probe", [False, True])
def test_real_trial_installs_archive_and_native_peek_recovers_hidden_receipt(
    tmp_path, monkeypatch, probe
):
    from graph_trial import ENDPOINT, SOURCE
    from src.config import get_config
    from src.features import get_features, set_features
    from src.graph import context_arm_ab, graph
    from src.repl_environment.task_root import request_scope

    class BeforeGeneration(Exception):
        pass

    case = compile_cohort()["cases"][1]
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    oracle = tmp_path / "oracle.json"
    oracle.write_text(case["expected"])
    row = {"arm": "A1-k12", "seed": 42, "repeat": 0}
    (attempt / "INPUT.json").write_text(
        json.dumps(
            {
                "source": str(SOURCE),
                "endpoint": ENDPOINT,
                "row": row,
                "prompt": case["prompt"],
                "initial_history": case["initial_history"],
                "recovery_probe_v1": probe,
            }
        )
    )

    captures = []
    if probe:
        from contextlib import contextmanager
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent.parent / "cf3c-binding"))
        import recovery_probe
        original_capture = recovery_probe.capture_peeks

        @contextmanager
        def capture(*args):
            with original_capture(*args) as evidence:
                captures.append(evidence)
                yield evidence

        monkeypatch.setattr(recovery_probe, "capture_peeks", capture)

    async def check_native_inputs(state, deps):
        assert len(state.history_turns) == 10 and state.turns == 0
        rendered = context_arm_ab.render(state, deps.repl)
        assert case["expected"] not in rendered
        assert case["expected"] not in state.context
        recovered = deps.repl._peek(n=99999, file_path=state.history_log_path)
        assert case["expected"] in recovered
        if probe:
            assert captures[0]["log_path"] == state.history_log_path
            assert captures[0]["events"][-1]["recovered_observation"] is True
            assert captures[0]["events"][-1]["source_log_sha256"]
            # The tool namespace must have bound the wrapper before REPL construction.
            assert deps.repl._globals["peek"].__func__ is deps.repl._peek.__func__
        assert deps.repl._peek(n=99, file_path=str(oracle)).startswith("[ERROR:")
        raise BeforeGeneration

    for key, value in test_suite.suite_runner.child_env(
        attempt, row, "offline-key"
    ).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(graph, "run_task", check_native_inputs)
    monkeypatch.setattr("sys.path", __import__("sys").path.copy())
    prior = get_features()
    get_config.cache_clear()
    try:
        with pytest.raises(BeforeGeneration):
            test_suite.suite_trial.run_trial(attempt)
        assert request_scope() is None
    finally:
        set_features(prior)
        get_config.cache_clear()


def test_recovery_control_row_builds_real_child_environment(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent.parent / "cf3c-binding"))
    from recovery_probe import PROBE_SEED, compile_probe

    probe = compile_probe(compile_cohort())
    row = test_suite.suite_runner.recovery_control_row(probe)
    env = test_suite.suite_runner.child_env(tmp_path, row, "offline-key")
    assert env["ORCHESTRATOR_CONTEXT_TRIAL_INDEX"] == "0"
    assert row["case"] == "native_recovery_control_v1"
    assert row["seed"] == PROBE_SEED
    assert probe["grade_cohort"] is False

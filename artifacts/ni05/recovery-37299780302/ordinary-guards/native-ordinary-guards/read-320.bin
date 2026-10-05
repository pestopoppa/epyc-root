from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "benchmark" / "eval_batch_serving_evaltower_window.py"

spec = importlib.util.spec_from_file_location("eval_batch_serving_evaltower_window", MODULE_PATH)
assert spec is not None and spec.loader is not None
window = importlib.util.module_from_spec(spec)
sys.modules["eval_batch_serving_evaltower_window"] = window
spec.loader.exec_module(window)


class FakeResult:
    def __init__(
        self,
        *,
        tier: int,
        quality: float,
        speed: float,
        reliability: float,
        wall_s: float,
        n_questions: int = 5,
        n_scored: int | None = None,
        errors: int = 0,
    ) -> None:
        scored = n_questions if n_scored is None else n_scored
        self.tier = tier
        self.quality = quality
        self.speed = speed
        self.cost = 0.25
        self.reliability = reliability
        self.n_questions = n_questions
        self.per_suite_quality = {"general": quality}
        self.per_suite_counts = {"general": scored}
        self.routing_distribution = {"frontdoor": 1.0}
        self.question_results = []
        self.core_id = "fake-core"
        self.details = {
            "eval_wall_s": wall_s,
            "speed_metric_mode": "aggregate_batch_tps",
            "aggregate_tps": speed,
            "n_scored": scored,
            "quality_denominator": scored,
            "errors": errors,
            "per_suite_counts": {"general": scored},
            "per_suite_total_counts": {"general": n_questions},
        }
        self.speed_metric_mode = "aggregate_batch_tps"
        self.median_request_speed = 0.0
        self.aggregate_speed = speed
        self.eval_concurrency = 4
        self.eval_wall_s = wall_s
        self.mean_tools_used = 0.0
        self.tool_use_rate = 0.0
        self.total_tool_calls = 0


class FakeTower:
    results: list[FakeResult] = []

    def __init__(self, *, url: str, timeout: float) -> None:
        self.url = url
        self.timeout = timeout

    def eval_t1(self, *, n: int, seed: int) -> FakeResult:
        return self.results.pop(0)

    def eval_t2(self, *, n: int, seed: int) -> FakeResult:
        return self.results.pop(0)

    def eval_t3(self, *, n: int, seed: int) -> FakeResult:
        return self.results.pop(0)


def _healthy_preflight(*, autopilot_active: bool = False) -> dict:
    return {
        "api_health": {"ok": True},
        "eval_batch_frontdoor_health": {"ok": False},
        "autopilot_active": autopilot_active,
        "config_attest": {"all_sampled_workers_enabled": False},
        "activation_commands": [],
    }


def _step(name: str, ok: bool = True):
    return window.activation_window.StepResult(
        name=name,
        command=name,
        returncode=0 if ok else 2,
        elapsed_s=0.01,
        stdout_tail="",
        stderr_tail="",
    )


def test_plan_only_writes_no_eval_or_activation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(window, "run_eval_arm", lambda *_args, **_kwargs: None)

    args = window.parse_args(["--output-dir", str(tmp_path), "--tier", "3", "--n", "12"])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "plan_only"
    assert report["applied"] is False
    assert report["current_arm"] is None
    assert report["planned_current_arm"]["tier"] == 3
    assert report["planned_eval_batch_arm"]["n"] == 12


def test_apply_refuses_active_autopilot_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(autopilot_active=True),
    )

    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 3)

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 75
    assert report["status"] == "blocked"
    assert "AutoPilot appears active" in report["blockers"][0]
    assert report["decision_grade"] is False


def test_apply_requires_explicit_min_concurrency_or_allow_serial(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 1)
    monkeypatch.setattr(
        window,
        "run_eval_arm",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("eval must not run before fanout guard")
        ),
    )

    args = window.parse_args(["--apply", "--confirm-clean-window", "--output-dir", str(tmp_path)])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc != 0
    assert report["status"] == "blocked"
    assert report["decision_grade"] is False
    assert any("requires explicit --min-eval-concurrency" in b for b in report["blockers"])


def test_successful_apply_runs_both_arms_and_rolls_back(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(
        window.activation_window,
        "execute_activation",
        lambda _args, *, output_dir: ([_step("start"), _step("reload"), _step("smoke")], []),
    )
    monkeypatch.setattr(
        window.activation_window,
        "_load_probe_summary",
        lambda _output_dir: {"status": "smoke_passed", "decision_grade": True},
    )
    monkeypatch.setattr(
        window.activation_window,
        "execute_rollback",
        lambda _args: [_step("rollback_reload"), _step("rollback_stop")],
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)

    calls: list[str] = []

    def fake_run_eval_arm(name: str, _args, **_kwargs):
        calls.append(name)
        if name == "current":
            return {
                "name": name,
                "ok": True,
                "error": None,
                "metrics": {
                    "quality": 2.0,
                    "speed": 10.0,
                    "reliability": 1.0,
                    "wall_s": 100.0,
                    "n_questions": 50,
                    "n_scored": 50,
                },
            }
        return {
            "name": name,
            "ok": True,
            "error": None,
            "metrics": {
                "quality": 2.1,
                "speed": 12.0,
                "reliability": 1.0,
                "wall_s": 25.0,
                "n_questions": 50,
                "n_scored": 50,
            },
        }

    monkeypatch.setattr(window, "run_eval_arm", fake_run_eval_arm)

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "comparison_complete_rolled_back"
    assert calls == ["current", "eval_batch"]
    assert report["decision_grade"] is True
    assert report["comparison"]["wall_speedup_current_over_eval_batch"] == 4.0
    assert [step["name"] for step in report["rollback_steps"]] == [
        "rollback_reload",
        "rollback_stop",
    ]


def test_degenerate_empty_current_arm_blocks_decision_grade(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)
    activated = False

    def fake_activate(_args, *, output_dir):  # noqa: ARG001
        nonlocal activated
        activated = True
        return ([_step("start")], [])

    monkeypatch.setattr(window.activation_window, "execute_activation", fake_activate)
    monkeypatch.setattr(
        window,
        "run_eval_arm",
        lambda _name, _args, **_kwargs: {
            "name": "current",
            "ok": True,
            "error": None,
            "metrics": {"quality": 0.0, "speed": 0.0, "reliability": 0.0, "n_questions": 0},
        },
    )

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 75
    assert report["status"] == "current_eval_degenerate"
    assert report["decision_grade"] is False
    assert activated is False
    assert any("degenerate" in b for b in report["blockers"])


def test_interrupt_after_activation_rolls_back_and_returns_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)
    monkeypatch.setattr(
        window.activation_window,
        "execute_activation",
        lambda _args, *, output_dir: ([_step("start"), _step("reload")], []),
    )
    monkeypatch.setattr(
        window.activation_window,
        "_load_probe_summary",
        lambda _output_dir: {"status": "smoke_passed", "decision_grade": True},
    )
    monkeypatch.setattr(
        window.activation_window,
        "execute_rollback",
        lambda _args: [_step("rollback_reload"), _step("rollback_stop")],
    )

    def fake_run_eval_arm(name: str, _args, **_kwargs):
        if name == "current":
            return {
                "name": name,
                "ok": True,
                "error": None,
                "metrics": {
                    "quality": 2.0,
                    "speed": 10.0,
                    "reliability": 1.0,
                    "wall_s": 100.0,
                    "n_questions": 50,
                    "n_scored": 50,
                },
            }
        raise window._RunInterrupted("SIGINT")

    monkeypatch.setattr(window, "run_eval_arm", fake_run_eval_arm)

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 130
    assert report["status"] == "interrupted"
    assert report["decision_grade"] is False
    assert [step["name"] for step in report["rollback_steps"]] == [
        "rollback_reload",
        "rollback_stop",
    ]


def test_skip_current_arm_runs_batch_only_and_is_not_decision_grade(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(
        window.activation_window,
        "execute_activation",
        lambda _args, *, output_dir: ([_step("start"), _step("reload"), _step("smoke")], []),
    )
    monkeypatch.setattr(
        window.activation_window,
        "_load_probe_summary",
        lambda _output_dir: {"status": "smoke_passed", "decision_grade": True},
    )
    monkeypatch.setattr(
        window.activation_window,
        "execute_rollback",
        lambda _args: [_step("rollback_reload"), _step("rollback_stop")],
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)

    calls: list[str] = []

    def fake_run_eval_arm(name: str, _args, **_kwargs):
        calls.append(name)
        return {
            "name": name,
            "ok": True,
            "error": None,
            "metrics": {
                "quality": 2.1,
                "speed": 12.0,
                "reliability": 1.0,
                "wall_s": 25.0,
                "n_questions": 50,
                "n_scored": 50,
            },
        }

    monkeypatch.setattr(window, "run_eval_arm", fake_run_eval_arm)

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--skip-current-arm",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "eval_batch_arm_complete_rolled_back"
    assert calls == ["eval_batch"]
    assert report["comparison"] is None
    assert report["decision_grade"] is False


def test_current_arm_failure_blocks_activation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    activated = False

    def fake_activate(_args, *, output_dir):
        nonlocal activated
        activated = True
        return ([_step("start")], [])

    monkeypatch.setattr(window.activation_window, "execute_activation", fake_activate)
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 3)
    monkeypatch.setattr(
        window,
        "run_eval_arm",
        lambda _name, _args, **_kwargs: {
            "name": "current",
            "ok": False,
            "error": "boom",
            "metrics": {"wall_s": 0.01},
        },
    )

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 75
    assert report["status"] == "current_eval_failed"
    assert activated is False
    assert report["decision_grade"] is False


def test_eval_result_metrics_includes_suite_and_batch_fields(monkeypatch) -> None:
    monkeypatch.setattr(window, "EvalTower", FakeTower)
    FakeTower.results = [
        FakeResult(
            tier=1,
            quality=2.2,
            speed=40.0,
            reliability=0.98,
            wall_s=7.0,
        )
    ]
    args = window.parse_args(["--tier", "1", "--n", "5", "--seed", "7"])

    arm = window.run_eval_arm("current", args)

    assert arm["ok"] is True
    assert arm["metrics"]["tier"] == 1
    assert arm["metrics"]["quality"] == 2.2
    assert arm["metrics"]["aggregate_tps"] == 40.0
    assert arm["metrics"]["eval_wall_s"] == 7.0
    assert arm["metrics"]["n_scored"] == 5
    assert arm["metrics"]["per_suite_counts"] == {"general": 5}


def test_tier_arm_sets_question_artifact_dir_when_output_dir_given(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # EV-11c: the tier arm must engage the per-question sidecar so a burned/errored
    # tier arm leaves durable per-row records under its --output-dir (previously the
    # verifier/retry/resume paths did this but the tier path did not).
    recorded: list[Path] = []

    class RecordingTower(FakeTower):
        def set_question_artifact_dir(self, directory) -> None:
            recorded.append(directory)

    monkeypatch.setattr(window, "EvalTower", RecordingTower)
    FakeTower.results = [
        FakeResult(tier=1, quality=2.0, speed=30.0, reliability=1.0, wall_s=5.0)
    ]
    args = window.parse_args(["--tier", "1", "--n", "5", "--seed", "42"])

    arm = window.run_eval_arm("current", args, output_dir=tmp_path)

    assert arm["ok"] is True
    assert recorded == [tmp_path]


def test_tier_arm_skips_sidecar_when_no_output_dir(monkeypatch) -> None:
    # Backward-compat: without an output dir (e.g. direct callers), the guard must
    # not attempt the sidecar even on a tower that supports it.
    recorded: list[Path] = []

    class RecordingTower(FakeTower):
        def set_question_artifact_dir(self, directory) -> None:
            recorded.append(directory)

    monkeypatch.setattr(window, "EvalTower", RecordingTower)
    FakeTower.results = [
        FakeResult(tier=1, quality=2.0, speed=30.0, reliability=1.0, wall_s=5.0)
    ]
    args = window.parse_args(["--tier", "1", "--n", "5", "--seed", "42"])

    arm = window.run_eval_arm("current", args)

    assert arm["ok"] is True
    assert recorded == []


def test_eval_result_metrics_uses_details_n_scored_before_compact_question_count() -> None:
    result = FakeResult(
        tier=1,
        quality=1.8,
        speed=20.0,
        reliability=0.6,
        wall_s=10.0,
        n_questions=5,
        n_scored=3,
        errors=2,
    )
    result.question_results = [
        {"qid": "q1", "error": False},
        {"qid": "q2", "error": False},
        {"qid": "q3", "error": False},
        {"qid": "q4", "error": True},
        {"qid": "q5", "error": True},
    ]

    metrics = window.eval_result_metrics(result, wall_s=11.0)

    assert metrics["n_questions"] == 5
    assert metrics["question_results_count"] == 5
    assert metrics["n_scored"] == 3
    assert metrics["errors"] == 2


def test_partial_scored_current_arm_blocks_decision_grade(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)
    monkeypatch.setattr(
        window.activation_window,
        "execute_activation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("activation must not run after partial-scored current arm")
        ),
    )
    monkeypatch.setattr(
        window,
        "run_eval_arm",
        lambda *_args, **_kwargs: {
            "name": "current",
            "ok": True,
            "error": None,
            "metrics": {
                "quality": 2.0,
                "speed": 10.0,
                "reliability": 0.8,
                "wall_s": 100.0,
                "n_questions": 50,
                "n_scored": 40,
                "errors": 10,
            },
        },
    )

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--min-eval-concurrency",
            "3",
            "--n",
            "50",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 75
    assert report["status"] == "current_eval_degenerate"
    assert report["decision_grade"] is False
    assert any("scored 40/50 non-error questions" in b for b in report["blockers"])


def test_write_report_versions_summary_and_uses_atomic_writers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_write_json(path: Path, payload: dict) -> None:
        calls.append(("json", path.name, payload.get("schema_version", "")))
        path.write_text(json.dumps(payload), encoding="utf-8")

    def fake_write_text(path: Path, text: str) -> None:
        calls.append(("text", path.name, ""))
        path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(window, "_atomic_write_json", fake_write_json)
    monkeypatch.setattr(window, "_atomic_write_text", fake_write_text)

    report = {
        "status": "plan_only",
        "decision_grade": False,
        "applied": False,
        "eval_spec": {"tier": 1, "n": 5, "seed": 42},
        "skip_current_arm": False,
        "keep_enabled": False,
        "eval_batch_url": "http://localhost:18070",
        "preflight": {"autopilot_active": False},
        "activation_commands": [],
        "rollback_commands": [],
        "blockers": [],
    }

    json_path, md_path = window.write_report(report, tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert report["schema_version"] == window.TIER_REPORT_SCHEMA_VERSION
    assert ("json", "summary.json", window.TIER_REPORT_SCHEMA_VERSION) in calls
    assert ("text", "summary.md", "") in calls


def test_write_verifier_report_versions_summary_and_uses_atomic_writers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_write_json(path: Path, payload: dict) -> None:
        calls.append(("json", path.name, payload.get("schema_version", "")))
        path.write_text(json.dumps(payload), encoding="utf-8")

    def fake_write_text(path: Path, text: str) -> None:
        calls.append(("text", path.name, ""))
        path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(window, "_atomic_write_json", fake_write_json)
    monkeypatch.setattr(window, "_atomic_write_text", fake_write_text)

    report = {
        "mode": "calibration",
        "status": "plan_only",
        "decision_grade": False,
        "applied": False,
        "suite": "scoring_verifiers",
        "split": "HE-R+",
        "roles": ["worker_general"],
        "scoring": "exact_match",
        "full": False,
        "n": 5,
        "seed": 42,
        "preflight": {"autopilot_active": False},
        "pin_command": "python runner.py",
        "blockers": [],
    }

    json_path, md_path = window.write_verifier_report(report, tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert report["schema_version"] == window.VERIFIER_REPORT_SCHEMA_VERSION
    assert ("json", "summary.json", window.VERIFIER_REPORT_SCHEMA_VERSION) in calls
    assert ("text", "summary.md", "") in calls


def test_atomic_write_json_replaces_tmp_and_preserves_schema(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    window._atomic_write_json(path, {"schema_version": "unit.v1", "value": 1})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schema_version": "unit.v1",
        "value": 1,
    }
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_skip_batch_arm_runs_current_only_no_activation(tmp_path: Path, monkeypatch) -> None:
    """--skip-batch-arm (R3 re-baseline, 2026-07-23): current arm only, zero
    activation/rollback — the batch-shaped NODE0 lane must never launch under
    the restored big+quarters lineup (thread overlap with live halves)."""
    monkeypatch.setattr(
        window.activation_window,
        "build_preflight",
        lambda _args: _healthy_preflight(),
    )

    def _forbidden_activation(_args, *, output_dir):
        raise AssertionError("activation must not run with --skip-batch-arm")

    monkeypatch.setattr(window.activation_window, "execute_activation", _forbidden_activation)
    monkeypatch.setattr(
        window.activation_window,
        "execute_rollback",
        lambda _args: [],
    )
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)

    calls: list[str] = []

    def fake_run_eval_arm(name: str, _args, **_kwargs):
        calls.append(name)
        return {
            "name": name,
            "ok": True,
            "error": None,
            "metrics": {
                "quality": 2.0,
                "speed": 10.0,
                "reliability": 1.0,
                "wall_s": 100.0,
                "n_questions": 50,
                "n_scored": 50,
            },
        }

    monkeypatch.setattr(window, "run_eval_arm", fake_run_eval_arm)

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--skip-batch-arm",
            "--min-eval-concurrency",
            "3",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert calls == ["current"]
    assert report["status"] == "current_arm_complete"
    assert report["skip_batch_arm"] is True
    assert report["activation_steps"] == []
    assert report["rollback_steps"] == []


def test_skip_both_arms_is_a_parse_error(tmp_path: Path) -> None:
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        window.parse_args(
            ["--skip-current-arm", "--skip-batch-arm", "--output-dir", str(tmp_path)]
        )


def test_absent_goodput_stays_unmeasured_in_arm_metrics() -> None:
    """RTG-23: an unmeasured goodput must not be reported as a measured 0.0 qph.

    `_details_float(details, "goodput_qph")` defaulted to 0.0, so a trial whose
    quality was never measured (the producer journals `null`) surfaced in the arm
    metrics as a real zero solved-task rate — the gap-handling doctrine
    `_arm_decision_blocker` applies to n_scored/reliability, inverted.
    """
    absent = FakeResult(tier=1, quality=2.0, speed=30.0, reliability=1.0, wall_s=5.0)
    assert "goodput_qph" not in absent.details
    assert window.eval_result_metrics(absent, wall_s=6.0)["goodput_qph"] is None

    explicit_null = FakeResult(tier=1, quality=2.0, speed=30.0, reliability=1.0, wall_s=5.0)
    explicit_null.details["goodput_qph"] = None
    assert window.eval_result_metrics(explicit_null, wall_s=6.0)["goodput_qph"] is None

    # A MEASURED value — including a measured zero — is reported unchanged.
    for measured in (0.0, 88.25):
        result = FakeResult(tier=1, quality=2.0, speed=30.0, reliability=1.0, wall_s=5.0)
        result.details["goodput_qph"] = measured
        assert window.eval_result_metrics(result, wall_s=6.0)["goodput_qph"] == measured

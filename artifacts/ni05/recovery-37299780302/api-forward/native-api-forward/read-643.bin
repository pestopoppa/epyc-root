from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "tasks" / "run_real_suite_v1_evaltower_window.py"

spec = importlib.util.spec_from_file_location("run_real_suite_v1_evaltower_window", MODULE_PATH)
assert spec is not None and spec.loader is not None
window = importlib.util.module_from_spec(spec)
sys.modules["run_real_suite_v1_evaltower_window"] = window
spec.loader.exec_module(window)


class FakeResult:
    tier = 1
    quality = 1.5
    speed = 20.0
    cost = 0.25
    reliability = 1.0
    n_questions = 2
    eval_wall_s = 10.0
    eval_concurrency = 1
    speed_metric_mode = "median_request_tps"
    aggregate_speed = 25.0
    median_request_speed = 20.0
    details = {
        "correct": 1,
        "total": 2,
        "errors": 0,
        "per_suite_counts": {"real_suite_v1": 2},
    }
    question_results = [
        {
            "qid": "real_suite_v1_0001",
            "suite": "real_suite_v1",
            "correct": True,
            "latency_ms": 100,
        },
        {
            "qid": "real_suite_v1_0002",
            "suite": "real_suite_v1",
            "correct": False,
            "latency_ms": 200,
            "route": "worker_general",
        },
    ]


def _write_suite(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "suite": "real_suite_v1",
                "version": "1.0",
                "questions": [
                    {
                        "id": "real_suite_v1_0001",
                        "tier": 1,
                        "prompt": "private prompt a",
                        "expected": "a",
                        "real_task_class": "code_change_implementation",
                    },
                    {
                        "id": "real_suite_v1_0002",
                        "tier": 2,
                        "prompt": "private prompt b",
                        "expected": "b",
                        "real_task_class": "debug_root_cause",
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_plan_only_summarizes_suite_without_running_eval(tmp_path: Path, monkeypatch) -> None:
    suite = tmp_path / "real_suite_v1.yaml"
    _write_suite(suite)
    monkeypatch.setattr(window, "autopilot_processes", lambda: [])
    monkeypatch.setattr(window, "api_health", lambda *_args, **_kwargs: {"ok": False})
    monkeypatch.setattr(
        window,
        "run_evaltower_eval",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    args = window.parse_args(["--suite-yaml", str(suite), "--n", "2"])
    report, rc = window.build_report(args, output_dir=tmp_path / "out", stamp="20260705T000000Z")

    assert rc == 0
    assert report["status"] == "plan_only"
    assert report["applied"] is False
    assert report["suite"]["question_count"] == 2
    assert report["suite"]["task_class_counts"] == {
        "code_change_implementation": 1,
        "debug_root_cause": 1,
    }
    assert report["raw_jsonl"] == ""


def test_apply_refuses_active_autopilot_by_default(tmp_path: Path, monkeypatch) -> None:
    suite = tmp_path / "real_suite_v1.yaml"
    _write_suite(suite)
    monkeypatch.setattr(window, "autopilot_processes", lambda: ["123 autopilot.py start"])
    monkeypatch.setattr(window, "api_health", lambda *_args, **_kwargs: {"ok": True})

    args = window.parse_args(
        [
            "--suite-yaml",
            str(suite),
            "--apply",
            "--confirm-clean-window",
            "--n",
            "2",
            "--allow-partial",
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path / "out", stamp="20260705T000000Z")

    assert rc == 75
    assert report["status"] == "blocked"
    assert "AutoPilot appears active" in report["blockers"][0]
    assert report["decision_grade"] is False


def test_apply_packages_prompt_free_ledger_with_task_classes(tmp_path: Path, monkeypatch) -> None:
    suite = tmp_path / "real_suite_v1.yaml"
    raw = tmp_path / "raw.jsonl"
    out = tmp_path / "out"
    _write_suite(suite)
    monkeypatch.setattr(window, "autopilot_processes", lambda: [])
    monkeypatch.setattr(window, "api_health", lambda *_args, **_kwargs: {"ok": True})
    monkeypatch.setattr(window, "run_evaltower_eval", lambda **_kwargs: FakeResult())

    args = window.parse_args(
        [
            "--suite-yaml",
            str(suite),
            "--raw-jsonl",
            str(raw),
            "--apply",
            "--confirm-clean-window",
            "--n",
            "2",
            "--allow-partial",
        ]
    )
    report, rc = window.build_report(args, output_dir=out, stamp="20260705T000000Z")

    assert rc == 0
    assert report["status"] == "packaged_observation"
    assert report["decision_grade"] is False
    raw_row = json.loads(raw.read_text(encoding="utf-8"))
    assert raw_row["eval_details"]["question_results"][0]["real_task_class"] == (
        "code_change_implementation"
    )
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    ledger_rows = [
        json.loads(line)
        for line in (out / "question_ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert summary["metrics"]["correct"] == 1
    assert summary["by_task_class"]["code_change_implementation"]["accuracy"] == 1.0
    assert summary["by_task_class"]["debug_root_cause"]["accuracy"] == 0.0
    assert "prompt" not in ledger_rows[0]
    assert "expected" not in ledger_rows[0]


def test_full_clean_50_question_run_is_decision_grade(tmp_path: Path, monkeypatch) -> None:
    suite = tmp_path / "real_suite_v1.yaml"
    questions = [
        {
            "id": f"real_suite_v1_{idx:04d}",
            "prompt": f"private {idx}",
            "expected": str(idx),
            "real_task_class": "code_change_implementation",
        }
        for idx in range(1, 51)
    ]
    suite.write_text(
        yaml.safe_dump({"suite": "real_suite_v1", "questions": questions}, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(window, "autopilot_processes", lambda: [])
    monkeypatch.setattr(window, "api_health", lambda *_args, **_kwargs: {"ok": True})
    monkeypatch.setattr(window, "run_evaltower_eval", lambda **_kwargs: FakeResult())

    args = window.parse_args(
        [
            "--suite-yaml",
            str(suite),
            "--raw-jsonl",
            str(tmp_path / "raw.jsonl"),
            "--apply",
            "--confirm-clean-window",
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path / "out", stamp="20260705T000000Z")

    assert rc == 0
    assert report["status"] == "clean_full_suite_packaged"
    assert report["decision_grade"] is True


def test_absent_goodput_is_carried_as_unmeasured_not_zero() -> None:
    """RTG-23: the producer journals `null` goodput when quality was not measured.

    `details.get("goodput_qph", 0.0)` turned that absence into a real 0.00 solved
    questions/hour — a measurement this row never made. It must stay None.
    """
    absent = FakeResult()
    absent.details = dict(FakeResult.details)  # no goodput_qph / task_rate_qph keys
    args = window.parse_args(["--n", "2"])

    row = window.eval_result_raw_row(
        result=absent,
        selected_questions=[],
        args=args,
        started_at="2026-09-14T00:00:00+00:00",
        finished_at="2026-09-14T00:01:00+00:00",
        calibration_id="cal-test",
    )
    assert row["eval_details"]["details"]["goodput_qph"] is None

    explicit_null = FakeResult()
    explicit_null.details = {**FakeResult.details, "goodput_qph": None}
    row_null = window.eval_result_raw_row(
        result=explicit_null,
        selected_questions=[],
        args=args,
        started_at="2026-09-14T00:00:00+00:00",
        finished_at="2026-09-14T00:01:00+00:00",
        calibration_id="cal-test",
    )
    assert row_null["eval_details"]["details"]["goodput_qph"] is None

    # A MEASURED value — including a measured zero — is carried through unchanged.
    for measured in (0.0, 123.5):
        result = FakeResult()
        result.details = {**FakeResult.details, "goodput_qph": measured}
        row_measured = window.eval_result_raw_row(
            result=result,
            selected_questions=[],
            args=args,
            started_at="2026-09-14T00:00:00+00:00",
            finished_at="2026-09-14T00:01:00+00:00",
            calibration_id="cal-test",
        )
        assert row_measured["eval_details"]["details"]["goodput_qph"] == measured

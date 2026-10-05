from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.autopilot import bsv_paired_runner


def _eval_result(correct: list[bool]) -> SimpleNamespace:
    return SimpleNamespace(
        tier=1,
        quality=sum(correct) / max(len(correct), 1) * 3.0,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
        routing_distribution={"frontdoor": 1.0},
        avg_prompt_tokens=900,
        question_results=[
            {"qid": f"q{i}", "suite": "suite", "correct": value}
            for i, value in enumerate(correct, start=1)
        ],
        eval_details={},
    )


class FakeTower:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []
        self.results = [
            _eval_result([True, True, False]),
            _eval_result([True, False, False]),
        ]

    def eval_t1(self, *, n: int, seed: int, trial_id=None):  # noqa: ANN001
        self.calls.append(("t1", n, seed))
        return self.results.pop(0)


def test_plan_mode_does_not_apply_or_eval(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    code = bsv_paired_runner.main(
        [
            "--output-dir",
            str(tmp_path),
            "--baseline-params",
            '{"a": 1}',
            "--candidate-params",
            '{"b": 2}',
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "plan"
    assert payload["baseline_param_keys"] == ["a"]
    assert payload["candidate_param_keys"] == ["b"]
    assert not (tmp_path / "baseline_eval.json").exists()


def test_run_paired_evaluation_writes_artifacts_and_restores(tmp_path: Path) -> None:
    applied: list[dict] = []

    def fake_apply(params):
        applied.append(dict(params))
        return {"status": "ok", "params": dict(params)}

    report = bsv_paired_runner.run_paired_evaluation(
        baseline_params={"flag": False},
        candidate_params={"flag": True},
        output_dir=tmp_path,
        t1_n=3,
        seed=123,
        min_shared_qids=3,
        tower=FakeTower(),
        apply_params_func=fake_apply,
    )

    assert applied == [{"flag": False}, {"flag": True}, {"flag": False}]
    assert report["comparison_type"] == "eval_result_pair"
    assert report["gate_decision"] == "block"
    assert "behavior signature severity is blocking" in report["blockers"]
    assert report["runner"]["mode"] == "run"
    assert report["runner"]["t1_n"] == 3
    assert (tmp_path / "baseline_eval.json").exists()
    assert (tmp_path / "candidate_eval.json").exists()
    assert (tmp_path / "bsv_paired_report.json").exists()
    candidate = json.loads((tmp_path / "candidate_eval.json").read_text())
    assert candidate["restore_baseline_result"]["params"] == {"flag": False}


def test_candidate_apply_failure_raises_before_candidate_eval(tmp_path: Path) -> None:
    tower = FakeTower()
    calls: list[dict] = []

    def fake_apply(params):
        calls.append(dict(params))
        if params.get("flag") is True:
            return {"status": "error", "errors": ["bad candidate"]}
        return {"status": "ok"}

    try:
        bsv_paired_runner.run_paired_evaluation(
            baseline_params={"flag": False},
            candidate_params={"flag": True},
            output_dir=tmp_path,
            t1_n=3,
            seed=123,
            min_shared_qids=3,
            tower=tower,
            apply_params_func=fake_apply,
        )
    except RuntimeError as exc:
        assert "candidate params failed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected candidate failure")

    assert calls == [{"flag": False}, {"flag": True}, {"flag": False}]
    assert tower.calls == [("t1", 3, 123)]
    assert (tmp_path / "baseline_eval.json").exists()
    assert not (tmp_path / "candidate_eval.json").exists()


def test_load_jsonish_accepts_file_and_inline(tmp_path: Path) -> None:
    p = tmp_path / "params.json"
    p.write_text('{"x": 1}')
    assert bsv_paired_runner._load_jsonish('{"y": 2}') == {"y": 2}
    assert bsv_paired_runner._load_jsonish(str(p)) == {"x": 1}
    assert bsv_paired_runner._load_jsonish(f"@{p}") == {"x": 1}

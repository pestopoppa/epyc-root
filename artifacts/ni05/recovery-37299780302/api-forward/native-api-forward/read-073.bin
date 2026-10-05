from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
import safety_gate as sg  # type: ignore[import-not-found]  # noqa: E402
from safety_gate import EvalResult  # type: ignore[import-not-found]  # noqa: E402


def _baseline_yaml(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# keep this operator note",
                "quality: 1.16",
                "speed: 18.0",
                "cost: 0.5",
                "reliability: 0.86",
                "frontdoor_speed: 12.7",
                "per_suite_quality:",
                "  coder: null",
                "  math: 1.1",
                "diversity_baseline:",
                "  frontdoor:",
                "    diversity_entropy: null",
                "",
            ]
        )
    )


_T1_ERA = "E16-eval-instrument"


def _t1_result() -> EvalResult:
    return EvalResult(
        tier=1,
        quality=1.82,
        speed=21.0,
        cost=0.4,
        reliability=0.94,
        per_suite_quality={"coder": 1.7, "math": 1.9},
        n_questions=100,
        # RTG-02 (2026-09-14): a real EvalTower result carries the eval-quality instrument era
        # it was measured under (eval_tower._stamp_eval_instrument), and the calibration stamps
        # THAT era onto the baseline — an unstamped result is refused. The fake tower must carry
        # it too, or this fixture would stop exercising the calibration path at all.
        details={"eval_quality_era": _T1_ERA, "eval_quality_era_status": "active"},
    )


def test_autopilot_logging_handlers_skip_file_handler_when_stream_is_log(tmp_path: Path) -> None:
    log_path = tmp_path / "autopilot.log"
    log_path.write_text("")

    with log_path.open("a") as stream:
        handlers = autopilot._autopilot_logging_handlers(log_path, stream=stream)

    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)


def test_autopilot_logging_handlers_keep_file_handler_for_terminal_stream(tmp_path: Path) -> None:
    log_path = tmp_path / "autopilot.log"
    log_path.write_text("")
    other_path = tmp_path / "terminal.log"
    other_path.write_text("")

    with other_path.open("a") as stream:
        handlers = autopilot._autopilot_logging_handlers(log_path, stream=stream)

    try:
        assert len(handlers) == 2
        assert isinstance(handlers[0], logging.StreamHandler)
        assert isinstance(handlers[1], logging.FileHandler)
    finally:
        for handler in handlers:
            handler.close()


class _FakeEvalTower:
    calls: list[tuple[int, int | None, int]] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def evaluate(self, *, tier: int = 0, n: int | None = None, seed: int = 42) -> EvalResult:
        self.calls.append((tier, n, seed))
        return _t1_result()

    def eval_t0(self) -> EvalResult:
        self.calls.append((0, None, 0))
        return _t1_result()

    def eval_t1(self, *, n: int = 100, seed: int = 42) -> EvalResult:
        self.calls.append((1, n, seed))
        return _t1_result()

    def eval_t2(self, *, n: int = 500, seed: int = 42) -> EvalResult:
        self.calls.append((2, n, seed))
        return _t1_result()


def test_calibrate_baseline_migrates_t2_and_persists_t1(tmp_path, monkeypatch):
    path = tmp_path / "autopilot_baseline.yaml"
    _baseline_yaml(path)
    saved_states: list[dict] = []

    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.4)
    monkeypatch.setattr(autopilot, "load_state", lambda: {"trial_counter": 188})
    monkeypatch.setattr(autopilot, "save_state", lambda state: saved_states.append(state))
    monkeypatch.setattr(autopilot, "EvalTower", _FakeEvalTower)
    _FakeEvalTower.calls.clear()

    baseline, result, migrated = autopilot.calibrate_baseline(
        tier=1,
        n=50,
        seed=7,
        baseline_path=path,
    )

    assert migrated is True
    assert result is not None
    assert _FakeEvalTower.calls == [(1, 50, 7)]
    assert baseline.quality_for_tier(2, strict=True) == pytest.approx(1.16)
    assert baseline.quality_for_tier(1, strict=True) == pytest.approx(1.82)
    assert saved_states[-1]["baseline_state"]["baselines_by_tier"] == {
        "1": 1.82,
        "2": 1.16,
    }
    # RTG-02: the persisted baseline must carry the era of the instrument that produced it,
    # or the eval-instrument re-baseline hold stays open and quality can never promote.
    assert saved_states[-1]["baseline_state"]["eval_quality_era"] == _T1_ERA

    written = yaml.safe_load(path.read_text())
    assert "# keep this operator note" in path.read_text()
    assert written["baselines_by_tier"] == {1: 1.82, 2: 1.16}
    assert written["per_suite_quality_by_tier"][1] == {"coder": 1.7, "math": 1.9}
    assert written["per_suite_quality_by_tier"][2] == {"coder": None, "math": 1.1}
    assert written["diversity_baseline"]["frontdoor"]["diversity_entropy"] is None


def test_calibrate_baseline_migrate_only_skips_eval_and_writes_t2(tmp_path, monkeypatch):
    path = tmp_path / "autopilot_baseline.yaml"
    _baseline_yaml(path)
    saved_states: list[dict] = []

    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.4)
    monkeypatch.setattr(autopilot, "load_state", lambda: {})
    monkeypatch.setattr(autopilot, "save_state", lambda state: saved_states.append(state))
    monkeypatch.setattr(autopilot, "EvalTower", _FakeEvalTower)
    _FakeEvalTower.calls.clear()

    baseline, result, migrated = autopilot.calibrate_baseline(
        baseline_path=path,
        migrate_only=True,
    )

    assert migrated is True
    assert result is None
    assert _FakeEvalTower.calls == []
    assert baseline.quality_for_tier(2, strict=True) == pytest.approx(1.16)
    assert baseline.quality_for_tier(1, strict=True) is None
    assert saved_states[-1]["baseline_state"]["baselines_by_tier"] == {"2": 1.16}


def test_calibrate_baseline_dry_run_does_not_write(tmp_path, monkeypatch):
    path = tmp_path / "autopilot_baseline.yaml"
    _baseline_yaml(path)
    before = path.read_text()

    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.4)
    monkeypatch.setattr(autopilot, "load_state", lambda: {})
    monkeypatch.setattr(autopilot, "save_state", lambda state: pytest.fail("dry-run saved state"))
    monkeypatch.setattr(autopilot, "EvalTower", _FakeEvalTower)
    _FakeEvalTower.calls.clear()

    baseline, result, migrated = autopilot.calibrate_baseline(
        tier=1,
        baseline_path=path,
        write=False,
    )

    assert migrated is True
    assert result is not None
    assert baseline.quality_for_tier(1, strict=True) == pytest.approx(1.82)
    assert path.read_text() == before

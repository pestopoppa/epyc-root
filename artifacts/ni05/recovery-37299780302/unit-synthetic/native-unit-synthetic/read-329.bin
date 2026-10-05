"""--resume-incomplete-from: run only a prior incomplete run's missing remainder.

Covers the EvalTower primitive (eval_resume_incomplete) and the window-runner
mode (build_resume_report): remainder selection with original-dataset ordinals,
dataset_sha256 mismatch refusal, plan-only listing, and the merged (prior +
resumed) summary. INFERENCE-FREE — the adapter/generation/scoring are mocked.

Run: .venv/bin/python -m pytest tests/unit/test_eval_resume_incomplete.py -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (REPO_ROOT / "scripts" / "autopilot", REPO_ROOT / "scripts" / "benchmark", REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import eval_tower  # noqa: E402
from eval_tower import EvalTower, QuestionResult  # noqa: E402

_WINDOW_PATH = REPO_ROOT / "scripts" / "benchmark" / "eval_batch_serving_evaltower_window.py"
_spec = importlib.util.spec_from_file_location("eval_batch_serving_evaltower_window", _WINDOW_PATH)
assert _spec is not None and _spec.loader is not None
window = importlib.util.module_from_spec(_spec)
sys.modules["eval_batch_serving_evaltower_window"] = window
_spec.loader.exec_module(window)


def _full_questions(n: int = 5) -> list[dict]:
    return [
        {
            "id": f"q{i}",
            "suite": "scoring_verifiers",
            "prompt": f"p{i}",
            "expected": str(i),
            "scoring_method": "exact_match",
        }
        for i in range(n)
    ]


class _SimpleAgg:
    reliability = 1.0
    ece = None
    auroc = None
    details = {"confidence_is_real": False, "confidence_source_counts": {}}


# ── EvalTower.eval_resume_incomplete primitive ────────────────────────────────


def test_eval_resume_incomplete_runs_only_remainder_with_original_ordinals(monkeypatch) -> None:
    tower = EvalTower()
    full = _full_questions(5)
    sha = eval_tower.dataset_content_sha256(full)
    monkeypatch.setattr(
        tower, "_load_verifier_suite_questions", lambda *a, **k: [dict(q) for q in full]
    )
    monkeypatch.setattr(tower, "_aggregate", lambda results, tier=2: _SimpleAgg())

    captured: dict = {}

    def fake_eval_batch(role_qs, client, **kw):  # noqa: ANN001
        captured["role_qs"] = role_qs
        return [
            QuestionResult(
                question_id=q["id"], suite=q["suite"], prompt=q["prompt"],
                expected=q["expected"], qid=q["id"], answer=q["expected"], correct=True,
            )
            for q in role_qs
        ]

    monkeypatch.setattr(tower, "_eval_batch", fake_eval_batch)

    out = tower.eval_resume_incomplete(
        suite="scoring_verifiers",
        split="HE-R+",
        roles=["worker_general"],
        completed_ids=["q0", "q1", "q2"],  # first 3 already done
        expected_dataset_sha256=sha,
    )

    assert out["resumed_n"] == 2
    assert out["resume_completed_n"] == 3
    assert out["resumed_ordinals"] == [3, 4]
    # Only the missing remainder is dispatched, tagged with ORIGINAL ordinals.
    assert [q["id"] for q in captured["role_qs"]] == ["q3", "q4"]
    assert [q.get("_ordinal") for q in captured["role_qs"]] == [3, 4]
    assert out["dataset_sha256"] == sha


def test_eval_resume_incomplete_refuses_on_dataset_sha_mismatch(monkeypatch) -> None:
    tower = EvalTower()
    full = _full_questions(5)
    monkeypatch.setattr(
        tower, "_load_verifier_suite_questions", lambda *a, **k: [dict(q) for q in full]
    )
    monkeypatch.setattr(
        tower,
        "_eval_batch",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run on mismatch")),
    )

    with pytest.raises(ValueError, match="dataset mismatch"):
        tower.eval_resume_incomplete(
            suite="scoring_verifiers",
            split="HE-R+",
            roles=["worker_general"],
            completed_ids=[],
            expected_dataset_sha256="deadbeefdeadbeef",
        )


# ── window runner: build_resume_report ────────────────────────────────────────


def _healthy_preflight(*, autopilot_active: bool = False) -> dict:
    return {
        "api_health": {"ok": True},
        "eval_batch_frontdoor_health": {"ok": False},
        "autopilot_active": autopilot_active,
        "config_attest": {"all_sampled_workers_enabled": False},
        "activation_commands": [],
    }


def _write_prior_run(
    directory: Path,
    *,
    suite: str,
    split: str,
    seed: int,
    sha: str,
    completed_ids: list[str],
    n_total: int = 5,
    label: str = "cal-worker_general",
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "mode": "calibration",
                "suite": suite,
                "split": split,
                "seed": seed,
                "full": True,
                "scoring": None,
                "result": {"dataset_sha256": sha, "n_questions": n_total},
            }
        ),
        encoding="utf-8",
    )
    rows: list[dict] = [{"row_type": "batch_start", "label": label}]
    for i, qid in enumerate(completed_ids):
        rows.append(
            {
                "row_type": "question_result",
                "label": label,
                "ordinal": i,
                "result": {"question_id": qid, "qid": qid, "suite": suite, "correct": True},
            }
        )
    # No batch_complete row -> incomplete run.
    (directory / f"question_results.{label}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )


class _FakeResumeTower:
    def __init__(self, *, url: str, timeout: float) -> None:
        self.url = url
        self.timeout = timeout

    def set_question_artifact_dir(self, directory) -> None:  # noqa: ANN001
        self._dir = directory

    def eval_resume_incomplete(self, *, roles, suite, expected_dataset_sha256, **kw):  # noqa: ANN001
        role = roles[0]
        return {
            "mode": "resume_incomplete",
            "resumed_n": 2,
            "resume_completed_n": 3,
            "resumed_ordinals": [3, 4],
            "dataset_sha256": expected_dataset_sha256,
            "per_role": {
                role: {
                    "rows": [
                        {"question_id": "q3", "qid": "q3", "suite": suite, "correct": True},
                        {"question_id": "q4", "qid": "q4", "suite": suite, "correct": False},
                    ]
                }
            },
        }


class _MismatchTower(_FakeResumeTower):
    def eval_resume_incomplete(self, **kw):  # noqa: ANN001
        raise ValueError(
            "resume dataset mismatch: reconstructed dataset_sha256=xxx != prior abc123"
        )


def test_resume_plan_only_lists_completed_and_remaining(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(window.activation_window, "build_preflight", lambda _a: _healthy_preflight())
    src = tmp_path / "prior"
    _write_prior_run(src, suite="scoring_verifiers", split="HE-R+", seed=42, sha="abc123",
                     completed_ids=["q0", "q1", "q2"])
    out = tmp_path / "out"
    args = window.parse_args(["--resume-incomplete-from", str(src), "--output-dir", str(out)])

    report, rc = window.build_resume_report(args, output_dir=out)

    assert rc == 0
    assert report["status"] == "plan_only"
    assert report["resumed"] is True
    assert report["resume_source_run"] == str(src)
    assert report["suite"] == "scoring_verifiers"
    assert report["split"] == "HE-R+"
    assert report["dataset_sha256"] == "abc123"
    plan = report["resume_plan"]["worker_general"]
    assert plan["completed_ids"] == 3
    assert plan["remaining_estimate"] == 2


def test_resume_missing_source_dir_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(window.activation_window, "build_preflight", lambda _a: _healthy_preflight())
    out = tmp_path / "out"
    args = window.parse_args(
        ["--resume-incomplete-from", str(tmp_path / "nope"), "--output-dir", str(out)]
    )
    report, rc = window.build_resume_report(args, output_dir=out)
    assert any("source dir not found" in b for b in report["blockers"])
    assert report["decision_grade"] is False


def test_resume_apply_merges_prior_and_resumed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(window.activation_window, "build_preflight", lambda _a: _healthy_preflight())
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)
    monkeypatch.setattr(window, "_optimized_live_stack_status", lambda: {"ok": True, "warnings": []})
    monkeypatch.setattr(window, "EvalTower", _FakeResumeTower)

    src = tmp_path / "prior"
    _write_prior_run(src, suite="scoring_verifiers", split="HE-R+", seed=42, sha="abc123",
                     completed_ids=["q0", "q1", "q2"])
    out = tmp_path / "out"
    args = window.parse_args(
        [
            "--resume-incomplete-from", str(src),
            "--roles", "worker_general",
            "--apply", "--confirm-clean-window",
            "--min-eval-concurrency", "3",
            "--output-dir", str(out),
        ]
    )

    report, rc = window.build_resume_report(args, output_dir=out)

    assert report["status"] == "complete"
    assert rc == 0
    assert report["resumed_n"] == 2
    assert report["resume_completed_n"] == 3
    merged = report["per_role"]["worker_general"]
    assert merged["n_questions"] == 5  # 3 prior + 2 resumed, merged by identity
    assert merged["correct"] == 4  # q0,q1,q2 (prior) + q3 (resumed) correct; q4 wrong
    assert merged["reliability"] == pytest.approx(1.0)
    # Binary-proxy rows -> calibration not real -> demoted (positive evidence).
    assert merged["confidence_is_real"] is False
    assert report["decision_grade"] is False
    assert report["decision_grade_reasons"]
    # Merged summary is durably written by the writer half.
    json_path, md_path = window.write_resume_report(report, out)
    assert json_path.exists() and md_path.exists()
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["schema_version"] == window.RESUME_REPORT_SCHEMA_VERSION
    assert written["resumed_n"] == 2


def test_resume_apply_refuses_on_dataset_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(window.activation_window, "build_preflight", lambda _a: _healthy_preflight())
    monkeypatch.setattr(window, "_resolved_eval_concurrency", lambda _roles=None: 4)
    monkeypatch.setattr(window, "_optimized_live_stack_status", lambda: {"ok": True, "warnings": []})
    monkeypatch.setattr(window, "EvalTower", _MismatchTower)

    src = tmp_path / "prior"
    _write_prior_run(src, suite="scoring_verifiers", split="HE-R+", seed=42, sha="abc123",
                     completed_ids=["q0", "q1", "q2"])
    out = tmp_path / "out"
    args = window.parse_args(
        [
            "--resume-incomplete-from", str(src),
            "--roles", "worker_general",
            "--apply", "--confirm-clean-window",
            "--min-eval-concurrency", "3",
            "--output-dir", str(out),
        ]
    )

    report, rc = window.build_resume_report(args, output_dir=out)

    assert report["status"] == "dataset_mismatch"
    assert rc == 75
    assert any("resume refused" in b for b in report["blockers"])
    assert report["decision_grade"] is False


def test_retry_and_resume_mutually_exclusive(tmp_path) -> None:
    args = window.parse_args(
        [
            "--retry-errors-from", str(tmp_path),
            "--resume-incomplete-from", str(tmp_path),
            "--output-dir", str(tmp_path / "o"),
        ]
    )
    with pytest.raises(SystemExit):
        window.main(
            [
                "--retry-errors-from", str(tmp_path),
                "--resume-incomplete-from", str(tmp_path),
                "--output-dir", str(tmp_path / "o"),
            ]
        )
    assert args.retry_errors_from is not None and args.resume_incomplete_from is not None

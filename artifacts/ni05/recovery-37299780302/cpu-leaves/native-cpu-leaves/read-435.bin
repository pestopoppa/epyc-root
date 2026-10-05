from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.calibration.irt_cold_start_ab import (
    load_baseline_records,
    run_audit,
    select_irt_stratified,
)


def _write_baseline(path: Path, n: int = 10) -> Path:
    results = {
        "general": {
            f"q{i}": {
                "question_id": f"q{i}",
                "prompt": f"Prompt {i}",
                "algorithmic_score": 3 if i % 2 else 1,
                "tokens_per_second": 10 + i,
                "total_time_ms": 1000 + i,
            }
            for i in range(n)
        }
    }
    path.write_text(
        json.dumps(
            {
                "model_role": "unit_model",
                "results": results,
                "summary": {
                    "avg_tokens_per_second": 14.5,
                    "avg_algorithmic_score": 2.0,
                    "questions_tested": n,
                    "questions_passed": n // 2,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_load_baseline_records_flattens_legacy_baseline_json(tmp_path: Path) -> None:
    path = _write_baseline(tmp_path / "baseline.json", n=3)

    baseline, records = load_baseline_records(path)

    assert baseline["model_role"] == "unit_model"
    assert [record.question_id for record in records] == ["q0", "q1", "q2"]
    assert records[0].prompt_hash
    assert records[1].algorithmic_score == 3.0


def test_run_audit_uses_keyed_irt_scores(tmp_path: Path) -> None:
    baseline_path = _write_baseline(tmp_path / "baseline.json", n=8)
    _, records = load_baseline_records(baseline_path)
    irt_path = tmp_path / "irt.npz"
    np.savez(
        irt_path,
        prompt_hashes=np.array([record.prompt_hash for record in records], dtype=object),
        latent_difficulty=np.linspace(-2, 2, len(records)).astype(np.float32),
        latent_discrimination=np.linspace(1, 8, len(records)).astype(np.float32),
    )

    report = run_audit(baseline_path, irt_path, sample_size=4, difficulty_bins=2)

    assert report["status"] == "ok"
    assert report["sample_size"] == 4
    assert report["scored_records"] == 8
    assert report["comparison"]["avg_algorithmic_score"]["abs_error"] is not None
    assert len(report["selected"]) == 4


def test_run_audit_can_score_prompt_embeddings_with_projector(tmp_path: Path) -> None:
    baseline_path = _write_baseline(tmp_path / "baseline.json", n=4)
    _, records = load_baseline_records(baseline_path)
    embeddings = np.arange(16, dtype=np.float32).reshape(4, 4)
    emb_path = tmp_path / "embeddings.npz"
    np.savez(
        emb_path,
        prompt_hashes=np.array([record.prompt_hash for record in records], dtype=object),
        embeddings=embeddings,
    )
    irt_path = tmp_path / "irt_projector.npz"
    np.savez(
        irt_path,
        latent_difficulty=np.zeros(4, dtype=np.float32),
        latent_discrimination=np.zeros(4, dtype=np.float32),
        embedding_dim=np.array(4, dtype=np.int64),
        projector_feature_mean=np.zeros(4, dtype=np.float32),
        projector_feature_scale=np.ones(4, dtype=np.float32),
        projector_weights=np.array(
            [
                [0.1, 0.0],
                [0.0, 0.1],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 1.0],
            ],
            dtype=np.float32,
        ),
        projector_target_mean=np.zeros(2, dtype=np.float32),
        projector_target_scale=np.ones(2, dtype=np.float32),
    )

    report = run_audit(baseline_path, irt_path, prompt_embeddings_path=emb_path, sample_size=2)

    assert report["status"] == "ok"
    assert report["scored_records"] == 4
    assert report["sample_size"] == 2
    assert all(item["latent_discrimination"] >= 0 for item in report["selected"])


def test_run_audit_reports_missing_scores_without_fake_selection(tmp_path: Path) -> None:
    baseline_path = _write_baseline(tmp_path / "baseline.json", n=2)
    irt_path = tmp_path / "irt_unkeyed.npz"
    np.savez(
        irt_path,
        latent_difficulty=np.zeros(2, dtype=np.float32),
        latent_discrimination=np.ones(2, dtype=np.float32),
    )

    report = run_audit(baseline_path, irt_path)

    assert report["status"] == "blocked_missing_irt_scores"
    assert report["scored_records"] == 0


def test_run_audit_acceptance_gate_accepts_when_thresholds_met(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "model_role": "unit_model",
                "results": {
                    "general": {
                        f"q{i}": {
                            "question_id": f"q{i}",
                            "prompt": f"Prompt {i}",
                            "algorithmic_score": 4.0,
                            "tokens_per_second": 20.0,
                            "total_time_ms": 100.0,
                        }
                        for i in range(4)
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    _, records = load_baseline_records(baseline_path)
    irt_path = tmp_path / "irt.npz"
    np.savez(
        irt_path,
        prompt_hashes=np.array([record.prompt_hash for record in records], dtype=object),
        latent_difficulty=np.linspace(-1, 1, len(records)).astype(np.float32),
        latent_discrimination=np.linspace(1, 4, len(records)).astype(np.float32),
    )

    report = run_audit(
        baseline_path,
        irt_path,
        sample_size=2,
        difficulty_bins=2,
        enable_acceptance_gate=True,
        max_relative_error=0.0,
        min_speedup_ratio=2.0,
    )

    assert report["status"] == "accepted"
    assert report["acceptance"]["status"] == "accepted"
    assert report["acceptance"]["meets_metric_thresholds"] is True
    assert report["acceptance"]["speedup_ratio"] == 2.0
    assert report["acceptance"]["meets_speedup_threshold"] is True


def test_run_audit_acceptance_gate_rejects_when_speedup_is_too_slow(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "model_role": "unit_model",
                "results": {
                    "general": {
                        f"q{i}": {
                            "question_id": f"q{i}",
                            "prompt": f"Prompt {i}",
                            "algorithmic_score": 4.0,
                            "tokens_per_second": 20.0,
                            "total_time_ms": 100.0,
                        }
                        for i in range(4)
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    _, records = load_baseline_records(baseline_path)
    irt_path = tmp_path / "irt.npz"
    np.savez(
        irt_path,
        prompt_hashes=np.array([record.prompt_hash for record in records], dtype=object),
        latent_difficulty=np.linspace(-1, 1, len(records)).astype(np.float32),
        latent_discrimination=np.linspace(1, 4, len(records)).astype(np.float32),
    )

    report = run_audit(
        baseline_path,
        irt_path,
        sample_size=3,
        difficulty_bins=2,
        enable_acceptance_gate=True,
        max_relative_error=0.0,
        min_speedup_ratio=10.0,
    )

    assert report["status"] == "rejected"
    assert report["acceptance"]["status"] == "rejected"
    assert report["acceptance"]["meets_speedup_threshold"] is False


def test_select_irt_stratified_spreads_across_difficulty_bins(tmp_path: Path) -> None:
    baseline_path = _write_baseline(tmp_path / "baseline.json", n=6)
    _, records = load_baseline_records(baseline_path)
    scored = [
        type("Scored", (), {"record": record, "latent_difficulty": float(idx), "latent_discrimination": float(idx)})()
        for idx, record in enumerate(records)
    ]

    selected = select_irt_stratified(scored, sample_size=3, difficulty_bins=3)

    assert len(selected) == 3
    assert {item.record.question_id for item in selected} == {"q1", "q3", "q5"}

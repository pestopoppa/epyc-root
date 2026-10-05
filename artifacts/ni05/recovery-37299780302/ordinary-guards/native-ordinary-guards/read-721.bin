from __future__ import annotations

from pathlib import Path

import run_manifest


def _inputs(tmp_path: Path) -> tuple[dict[str, Path], dict[str, object], dict[str, str]]:
    source = tmp_path / "source.py"
    source.write_text("answer = 42\n", encoding="utf-8")
    return (
        {"controller": source},
        {"type": "numeric_trial", "surface": "monitor"},
        {"class": "EvalTower", "url": "http://127.0.0.1:8000"},
    )


def test_manifest_is_deterministic_and_valid_when_sources_match(tmp_path: Path) -> None:
    source_paths, task, evaluator = _inputs(tmp_path)

    first = run_manifest.build_run_manifest(
        source_paths=source_paths, task=task, evaluator=evaluator
    )
    second = run_manifest.build_run_manifest(
        source_paths=source_paths, task=task, evaluator=evaluator
    )

    assert first == second
    assert run_manifest.manifest_drift_reasons(
        first, source_paths=source_paths, evaluator=evaluator
    ) == []


def test_manifest_rejects_source_or_evaluator_drift(tmp_path: Path) -> None:
    source_paths, task, evaluator = _inputs(tmp_path)
    manifest = run_manifest.build_run_manifest(
        source_paths=source_paths, task=task, evaluator=evaluator
    )

    source_paths["controller"].write_text("answer = 43\n", encoding="utf-8")
    reasons = run_manifest.manifest_drift_reasons(
        manifest,
        source_paths=source_paths,
        evaluator={**evaluator, "url": "http://127.0.0.1:9000"},
    )

    assert reasons == ["source-drift", "evaluator-drift"]


def test_manifest_rejects_tampering_and_missing_task(tmp_path: Path) -> None:
    source_paths, task, evaluator = _inputs(tmp_path)
    manifest = run_manifest.build_run_manifest(
        source_paths=source_paths, task=task, evaluator=evaluator
    )
    manifest["task"] = None

    reasons = run_manifest.manifest_drift_reasons(
        manifest, source_paths=source_paths, evaluator=evaluator
    )

    assert reasons == ["manifest-digest-mismatch", "missing-task"]

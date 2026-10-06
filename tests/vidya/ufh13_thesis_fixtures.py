"""Off-host UFH-13 fixtures built through the actual pinned producer helper."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

RESEARCH_COMMIT = "1bace97dc655ab5896291b4571781e53b821d9a3"
RESEARCH_ROOT_ENV = "UFH13_RESEARCH_ROOT"
SCORE_RELATIVE_PATH = "scripts/benchmark/thesis_ufh13/score.py"
SCORE_SHA256 = "544c1277d1eb00e9f685e40490385644573417f813a9989dacff83a7cdb4350f"
SYNTHETIC_RUN_ID = "synthetic-ufh13-run-1"
SYNTHETIC_SUITE_SHA256 = "c" * 64
SYNTHETIC_RESEARCH_COMMIT = "d" * 40
SYNTHETIC_SECRET = "SYNTHETIC_RAW_ANSWER_MUST_NOT_ESCAPE"


def _producer_belief_rows():
    root_value = os.environ.get(RESEARCH_ROOT_ENV)
    if not root_value:
        pytest.fail(f"{RESEARCH_ROOT_ENV} must name the explicit research Git checkout")
    root = Path(root_value)
    if not root.is_absolute() or not root.is_dir():
        pytest.fail(f"{RESEARCH_ROOT_ENV} must name an existing absolute directory")
    try:
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{RESEARCH_COMMIT}^{{commit}}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        )
        source = subprocess.run(
            ["git", "-C", str(root), "show", f"{RESEARCH_COMMIT}:{SCORE_RELATIVE_PATH}"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.fail(f"pinned UFH-13 producer commit/source is unavailable: {exc}")
    if hashlib.sha256(source).hexdigest() != SCORE_SHA256:
        pytest.fail("UFH-13 producer source differs from reviewed SHA-256")
    tree = ast.parse(source, filename=f"{RESEARCH_COMMIT}:{SCORE_RELATIVE_PATH}")
    definitions = {node.name: node for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assignments: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"ARM_NAMES", "BELIEF_SCHEMA"}:
                    assignments[target.id] = node.value
    function = definitions.get("belief_rows")
    digest_helper = definitions.get("_sha256")
    if not isinstance(function, ast.FunctionDef) or not isinstance(digest_helper, ast.FunctionDef):
        pytest.fail("pinned UFH-13 producer must define belief_rows and _sha256")
    if set(assignments) != {"ARM_NAMES", "BELIEF_SCHEMA"}:
        pytest.fail("pinned UFH-13 producer constants are missing")
    arm_names = ast.literal_eval(assignments["ARM_NAMES"])
    belief_schema = ast.literal_eval(assignments["BELIEF_SCHEMA"])
    if arm_names != ("A0", "A1", "A2") or belief_schema != "ufh13-thesis-belief/v1":
        pytest.fail("pinned UFH-13 producer constants differ from the reviewed literal schema")

    expected_helper = ast.parse(
        "def _sha256(path: Path) -> str:\n"
        "    return hashlib.sha256(path.read_bytes()).hexdigest()\n"
    ).body[0]
    if ast.dump(digest_helper, include_attributes=False) != \
            ast.dump(expected_helper, include_attributes=False):
        pytest.fail("pinned producer _sha256 is not the reviewed local Path.read_bytes digest")
    helper_names = {node.id for node in ast.walk(digest_helper) if isinstance(node, ast.Name)}
    if not helper_names <= {"path", "hashlib", "Path", "str"}:
        pytest.fail("pinned producer _sha256 has undeclared external dependencies")

    isolated = ast.Module(body=[digest_helper, function], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace: dict[str, Any] = {
        "Any": Any,
        "Path": Path,
        "ARM_NAMES": arm_names,
        "BELIEF_SCHEMA": belief_schema,
        "hashlib": hashlib,
    }
    exec(compile(isolated, f"{RESEARCH_COMMIT}:{SCORE_RELATIVE_PATH}", "exec"), namespace)
    return namespace["belief_rows"]


def synthetic_result() -> dict[str, Any]:
    return {
        "verdict": "SYNTHETIC_FIXTURE_ONLY",
        "rule": {"X": 0.75, "Y": 0.5,
                 "X_Y_status": "SYNTHETIC FIXTURE ONLY"},
        "n_items": 3,
        "accuracy": {"A0": 0.5, "A1": 0.25, "A2": 0.75},
        "accuracy_by_suite": {
            arm: {"synthetic-suite": value}
            for arm, value in {"A0": 0.5, "A1": 0.25, "A2": 0.75}.items()
        },
        "consultant_device_seconds": {"A0": 3.0, "A1": 2.0, "A2": 1.0},
        "G": 2.0,
        "G_ci95": [1.0, 3.0],
        "bootstrap": {"resamples": 5, "seed": 17,
                      "stratified_by": ["synthetic-suite"],
                      "g_undefined_resamples": 0, "interval": "percentile"},
        "d": 1.0 / 3.0,
        "d_ci95": [0.2, 0.5],
    }


def write_run(
    root: Path,
    *,
    result: dict[str, Any] | None = None,
    run_id: str = SYNTHETIC_RUN_ID,
    suite_sha256: str = SYNTHETIC_SUITE_SHA256,
    research_commit: str = SYNTHETIC_RESEARCH_COMMIT,
    preregistration_sha256: str | None = None,
    pilot: bool = False,
) -> Path:
    run = root / "synthetic-run"
    run.mkdir(parents=True, exist_ok=True)
    records = run / "records.jsonl"
    records.write_bytes((json.dumps({
        "schema": "ufh13-thesis-record/v1", "item_id": "synthetic-item",
        "raw_answer": SYNTHETIC_SECRET,
    }, sort_keys=True) + "\n").encode("utf-8"))
    rows = _producer_belief_rows()(
        result or synthetic_result(), run_id=run_id, records_path=records,
        scored_at="2026-10-06T00:00:00+00:00", suite_sha256=suite_sha256,
        preregistration_sha256=preregistration_sha256,
    )
    (run / "belief_measurements.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    (run / "run_manifest.json").write_text(json.dumps({
        "run_id": run_id,
        "suite_sha256": suite_sha256,
        "research_commit": research_commit,
        "preregistration_sha256": preregistration_sha256,
        "pilot": pilot,
        "items": ["synthetic-item-1", "synthetic-item-2", "synthetic-item-3"],
    }, sort_keys=True) + "\n", encoding="utf-8")
    return run

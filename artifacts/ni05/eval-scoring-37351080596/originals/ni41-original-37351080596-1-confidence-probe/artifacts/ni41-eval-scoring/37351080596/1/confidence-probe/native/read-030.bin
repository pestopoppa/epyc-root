#!/usr/bin/env python3
"""Adapter for nvidia/Scoring-Verifiers datasets (HE-R+, MBPP-R+).

Converts Scoring Verifiers JSONL format into Suite-compatible objects for
the eval tower. These are execution-based code benchmarks with verified
test inputs — both base and hardened (R+) variants.

Datasets:
  HE-R / HE-R+: HumanEval with robust/plus test inputs (164 problems)
  MBPP-R / MBPP-R+: MBPP with robust/plus test inputs (378/974 problems)

Usage:
    from scoring_verifiers_adapter import load_scoring_verifiers_suite

    suite = load_scoring_verifiers_suite("HE-R+")
    for q in suite.questions:
        print(q.id, q.prompt[:80])
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA_DIR = Path("/mnt/raid0/llm/data/eval/scoring_verifiers")

# Available datasets
DATASETS = {
    "HE-R": "HE-R.jsonl",
    "HE-R+": "HE-R+.jsonl",
    "MBPP-R": "MBPP-R.jsonl",
    "MBPP-R+": "MBPP-R+.jsonl",
}


@dataclass
class ScoringVerifiersProblem:
    """A single code problem from Scoring Verifiers."""

    task_id: str
    prompt: str
    entry_point: str
    canonical_solution: str
    test_code: str  # assertion-based test code
    base_input: list[Any]
    plus_input: list[Any]
    all_solutions: list[dict[str, Any]] = field(default_factory=list)


def load_problems(dataset_name: str) -> list[ScoringVerifiersProblem]:
    """Load problems from a Scoring Verifiers JSONL file.

    Args:
        dataset_name: One of "HE-R", "HE-R+", "MBPP-R", "MBPP-R+".

    Returns:
        List of ScoringVerifiersProblem objects.

    Raises:
        FileNotFoundError: If dataset file not found.
        ValueError: If dataset name is invalid.
    """
    if dataset_name not in DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_name}. Choose from: {list(DATASETS.keys())}")

    path = DATA_DIR / DATASETS[dataset_name]
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. "
            f"Download with: huggingface_hub.hf_hub_download('nvidia/Scoring-Verifiers', '{DATASETS[dataset_name]}', repo_type='dataset')"
        )

    problems = []
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            # MBPP-R uses 'assertion' or 'test_list' instead of 'test'
            test_code = row.get("test", "") or row.get("assertion", "")
            if not test_code and "test_list" in row:
                test_code = "\n".join(row["test_list"])

            problems.append(ScoringVerifiersProblem(
                task_id=row["task_id"],
                prompt=row["prompt"],
                entry_point=row.get("entry_point", ""),
                canonical_solution=row.get("canonical_solution", ""),
                test_code=test_code,
                base_input=row.get("base_input", []),
                plus_input=row.get("plus_input", []),
                all_solutions=row.get("all_solutions", []),
            ))

    return problems


def load_scoring_verifiers_suite(dataset_name: str):
    """Load a Scoring Verifiers dataset as a Suite-compatible object.

    Args:
        dataset_name: One of "HE-R", "HE-R+", "MBPP-R", "MBPP-R+".

    Returns:
        Suite object compatible with the benchmark suite loader.
    """
    # Import here to allow standalone use
    try:
        from suites import Suite, Question
    except ImportError:
        from scripts.benchmark.suites import Suite, Question

    problems = load_problems(dataset_name)

    is_plus = dataset_name.endswith("+")
    _base_name = dataset_name.replace("+", "").replace("-", "")
    domain = "humaneval" if "HE" in dataset_name else "mbpp"

    questions = []
    for prob in problems:
        # Build the evaluation prompt (just the function signature/docstring)
        prompt = prob.prompt.strip()

        # For execution scoring, include entry_point and test code
        scoring = [{"type": "execution", "entry_point": prob.entry_point}]
        if prob.test_code:
            scoring.append({"type": "test_assertion", "code": prob.test_code})

        questions.append(Question(
            id=prob.task_id,
            tier=2 if is_plus else 1,  # R+ is harder (Tier 2)
            name=f"{prob.task_id} ({prob.entry_point})",
            prompt=prompt,
            expected=prob.canonical_solution,
            scoring=scoring,
        ))

    return Suite(
        name=f"scoring_verifiers_{dataset_name.lower().replace('+', 'plus').replace('-', '_')}",
        version=1,
        domain=domain,
        description=f"nvidia/Scoring-Verifiers {dataset_name}: {len(problems)} problems "
                    f"({'hardened' if is_plus else 'base'} test inputs)",
        questions=questions,
        inference_params={
            "temperature": 0.0,
            "max_tokens": 1024,
            "timeout": 120,
        },
    )


def list_available() -> dict[str, dict[str, Any]]:
    """List available datasets with metadata.

    Returns:
        Dict of {name: {path, exists, row_count}}.
    """
    result = {}
    for name, filename in DATASETS.items():
        path = DATA_DIR / filename
        exists = path.exists()
        row_count = 0
        if exists:
            with open(path) as f:
                row_count = sum(1 for _ in f)
        result[name] = {"path": str(path), "exists": exists, "row_count": row_count}
    return result


if __name__ == "__main__":
    print("=== Scoring Verifiers Adapter ===\n")

    info = list_available()
    for name, meta in info.items():
        status = f"{meta['row_count']} problems" if meta["exists"] else "NOT DOWNLOADED"
        print(f"  {name}: {status}")

    print()

    # Load and show each available suite
    for name in DATASETS:
        path = DATA_DIR / DATASETS[name]
        if not path.exists():
            continue
        suite = load_scoring_verifiers_suite(name)
        print(f"Suite: {suite.name}")
        print(f"  Domain: {suite.domain}")
        print(f"  Description: {suite.description}")
        print(f"  Questions: {len(suite.questions)}")
        print(f"  Tier distribution: T1={sum(1 for q in suite.questions if q.tier == 1)}, "
              f"T2={sum(1 for q in suite.questions if q.tier == 2)}")
        if suite.questions:
            q = suite.questions[0]
            print(f"  Sample: {q.id} ({q.name})")
            print(f"    Prompt: {q.prompt[:100]}...")
        print()

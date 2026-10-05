"""EvalTower T1 integration for synthesized tasks (NIB2-44 AW-5).

Synthesized tasks enter T1 validation batches only — gold-ring T0
sentinels remain fixed. Each task carries provenance so EvalTower can
filter by ``discovered_via`` / ``difficulty_band`` / ``verifier_type``
and the review pipeline can flag tasks where >3 models fail.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

log = logging.getLogger("autopilot.env_synth.eval_integration")


@dataclass
class T1TaskEntry:
    """Flat record emitted to EvalTower T1 validation batches."""

    task_id: str
    suite: str = "env_synth_t1"
    prompt: str = ""
    expected: str = ""  # ground_truth_hint (for judge only)
    scoring_method: str = "custom"  # "custom" → VerifierSpec scorer
    scoring_config: dict = None  # verifier spec, expected_tool_calls
    provenance: dict = None  # discovered_via, difficulty_band, verifier_type
    consecutive_model_failures: int = 0
    flagged_for_review: bool = False

    def __post_init__(self) -> None:
        if self.scoring_config is None:
            self.scoring_config = {}
        if self.provenance is None:
            self.provenance = {}


def load_arena(arena_path: Path) -> Iterator[dict]:
    """Stream records from the EnvSynth arena JSONL file."""
    if not arena_path.exists():
        return
    for line in arena_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def arena_to_t1(
    arena_path: Path,
    *,
    only_bands: Optional[Iterable[str]] = None,
) -> list[T1TaskEntry]:
    """Project the arena JSONL into T1 task entries.

    When ``only_bands`` is supplied, filter to those difficulty bands
    (e.g. ``{"medium", "hard"}`` skips easy warm-ups).
    """
    bands = set(only_bands) if only_bands else None
    out: list[T1TaskEntry] = []
    for rec in load_arena(arena_path):
        band = rec.get("difficulty_band", "")
        if bands is not None and band not in bands:
            continue
        verifier = rec.get("verifier") or {}
        boundary = rec.get("boundary_contract")
        if boundary is not None and (
            rec.get("evaluation_tier") != "dynamic_t1" or rec.get("t0_eligible") is not False
        ):
            raise ValueError(
                "hypothesis-boundary task is not explicitly bound to dynamic T1 / T0-ineligible"
            )
        out.append(
            T1TaskEntry(
                task_id=rec.get("task_id", ""),
                prompt=rec.get("prompt", ""),
                expected=rec.get("ground_truth_hint", ""),
                scoring_method="custom",
                scoring_config={
                    "verifier": verifier,
                    "expected_tool_calls": rec.get("expected_tool_calls", [1, 2]),
                },
                provenance={
                    "discovered_via": "env_synth",
                    "difficulty_band": band,
                    "verifier_type": verifier.get("type", ""),
                    "environment_id": rec.get("environment_id", ""),
                    "tool_set": rec.get("tool_set", []),
                    "evaluation_tier": "dynamic_t1",
                    "t0_eligible": False,
                    "boundary_contract": boundary,
                },
            )
        )
    return out


def flag_human_review(
    entries: list[T1TaskEntry],
    failures_by_task: dict[str, int],
    *,
    fail_threshold: int = 3,
) -> list[T1TaskEntry]:
    """Mark entries whose model-failure count ≥ ``fail_threshold``.

    Mutates + returns the list for chaining. ``failures_by_task`` is
    expected to come from the EvalTower T1 run aggregation — keyed by
    ``task_id``.
    """
    for entry in entries:
        n = int(failures_by_task.get(entry.task_id, 0))
        entry.consecutive_model_failures = n
        entry.flagged_for_review = n >= fail_threshold
    return entries

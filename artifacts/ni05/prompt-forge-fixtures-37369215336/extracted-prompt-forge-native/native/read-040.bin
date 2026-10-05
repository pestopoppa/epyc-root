"""Gap diagnosis + weekly rollup for EnvSynth (NIB2-44 AW-3).

Parses the AR-3 trial journal looking for per-suite quality stagnation
(no improvement > ``stagnation_threshold`` over the last ``window``
trials) and emits gap descriptors the ETD agent can consume on its
next discovery cycle.

"Stagnation" here is intentionally simple — slope of a linear fit on
quality over the last N trials. A more principled Bayesian test is a
future refinement; the current signal is robust enough for the
training-free Phase 1 loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

log = logging.getLogger("autopilot.env_synth.gap_diagnosis")


@dataclass
class SuiteStagnation:
    suite: str
    latest_quality: float
    window_slope: float       # per-trial quality delta (linear fit)
    window_size: int
    gap_descriptor: str


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return num / den


def iter_trial_events(journal_path: Path) -> Iterable[dict]:
    """Yield dict events from a JSONL trial journal."""
    if not journal_path.exists():
        return
    for line in journal_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def diagnose_stagnation(
    journal_path: Path,
    *,
    window: int = 10,
    stagnation_threshold: float = 0.01,   # ≤1pp improvement per trial
) -> list[SuiteStagnation]:
    """Return per-suite stagnation records from a trial journal.

    Expected event shape (loose; extra keys ignored):

        {"suite": "math", "quality": 1.26, "trial_id": 42}

    Events without both fields are skipped silently.
    """
    per_suite: dict[str, list[float]] = {}
    for event in iter_trial_events(journal_path):
        suite = event.get("suite")
        quality = event.get("quality")
        if not suite or quality is None:
            continue
        try:
            per_suite.setdefault(suite, []).append(float(quality))
        except (TypeError, ValueError):
            continue

    findings: list[SuiteStagnation] = []
    for suite, series in per_suite.items():
        if len(series) < 3:
            continue
        tail = series[-window:]
        slope = _linear_slope(tail)
        if abs(slope) < stagnation_threshold:
            findings.append(SuiteStagnation(
                suite=suite,
                latest_quality=tail[-1],
                window_slope=slope,
                window_size=len(tail),
                gap_descriptor=_gap_descriptor(suite, tail[-1]),
            ))
    return findings


def _gap_descriptor(suite: str, quality: float) -> str:
    """Turn a suite+quality pair into an ETD re-prompt hint.

    Mapping is deliberately mechanical — the autopilot can override with
    better wording later when more suites are added.
    """
    band = "harder" if quality > 2.0 else "medium-difficulty"
    return (
        f"need more {band} {suite} tasks exercising tool-use and multi-step "
        f"reasoning to break the stagnation plateau at quality~{quality:.2f}"
    )


def render_arena_rollup(findings: Iterable[SuiteStagnation]) -> str:
    """Render a markdown rollup for ``arena.md`` (AW-3 weekly cron output)."""
    findings = list(findings)
    if not findings:
        return "# EnvSynth arena rollup\n\nNo stagnation detected across the scanned window.\n"
    lines = ["# EnvSynth arena rollup", ""]
    lines.append("| Suite | Latest q | Slope | Window | Gap descriptor |")
    lines.append("|-------|----------|-------|--------|----------------|")
    for f in findings:
        lines.append(
            f"| {f.suite} | {f.latest_quality:.3f} | {f.window_slope:+.4f} | "
            f"{f.window_size} | {f.gap_descriptor} |"
        )
    return "\n".join(lines) + "\n"

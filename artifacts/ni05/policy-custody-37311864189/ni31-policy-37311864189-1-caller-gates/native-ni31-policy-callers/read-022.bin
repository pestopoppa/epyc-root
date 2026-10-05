#!/usr/bin/env python3
"""Run the PII pre-commit hook against the `pii_hygiene_eval` fixture.

The hook intentionally allow-lists research/fixtures/pii_* when run inside the
root repo, so this validator stages each fixture row as a normal file in a
temporary git repository and compares the hook's block/pass behavior with the
fixture's expected_match field.

REPORTING CONTRACT (RC-11, handoffs/active/reviewer-calibration-accounting.md).
This validator used to print one aggregate, `passed/total`. That number merged
two errors with opposite costs: a secret the hook let through, and clean text
the hook refused. The 39/40 -> 42/42 repair of 2026-08-25 was a pure over-block
(false-reject) repair, yet it was reported, cited in the wiki, and used to call
the candidate gate green as a single improved fraction. The two sides are now
counted and printed SEPARATELY, each against its own denominator:

  * **false-accept (FA)** — a `expected_match=true` row the hook did NOT block:
    PII would have been committed. Denominator = the must-block rows.
  * **false-reject (FR)** — a `expected_match=false` row the hook DID block:
    clean content refused. Denominator = the must-not-block rows.

Both sides are computable ON THIS FIXTURE, so both are reported as rates. What
is NOT computable here is the FIELD false-accept rate, and the report says so
rather than letting the fixture FA rate be read as one: the fixture's must-block
rows are hand-written and are the only labelled PII that exists in this repo, so
they estimate the hook's behaviour on the secrets somebody already thought of
and nothing else. Alongside that statement the report prints the negative-side
LABEL COVERAGE histogram, which is the diagnostic that makes an untested rule
visible -- e.g. a detector whose only must-not-block row cannot reach it.

PROVENANCE NOTE (RC-12). This file previously described the fixture as
"held-out". It is not, and the word has been removed. `research/fixtures/
pii_hygiene_eval.jsonl` was created in the same commit as the hook it certifies
(`788dc3dc2`), and when fixture and hook later disagreed, commit `09dc82c56`
resolved the disagreement by editing the FIXTURE to match the hook and
recomputing the score. Selection and certification therefore happen on the same
sample; the numbers below are an internal consistency check, not an independent
estimate of the hook's error rates, and are reported as observations.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "research" / "fixtures" / "pii_hygiene_eval.jsonl"
DEFAULT_HOOK = ROOT / "scripts" / "hooks" / "pii_precommit.sh"

#: The four cells of the confusion matrix. FA and FR are the two error cells and
#: are NEVER summed into one number by anything in this module.
TRUE_BLOCK = "true_block"
TRUE_PASS = "true_pass"
FALSE_ACCEPT = "false_accept"
FALSE_REJECT = "false_reject"


def _run(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def _clear_worktree(repo: Path) -> None:
    _run(["git", "reset", "-q"], repo)
    for child in repo.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def classify(expected_block: bool, actual_block: bool) -> str:
    """Which confusion cell one case lands in.

    The hook blocks a commit it believes carries PII, so `expected_block` is
    "this row contains PII". Letting PII through is the ACCEPT error; refusing
    clean text is the REJECT error.
    """
    if expected_block:
        return TRUE_BLOCK if actual_block else FALSE_ACCEPT
    return FALSE_REJECT if actual_block else TRUE_PASS


def row_labels(row: dict[str, Any]) -> tuple[str, ...]:
    """The PII label kinds a fixture row is annotated with (possibly empty)."""
    spans = row.get("labels") or []
    if not isinstance(spans, list):
        return ()
    return tuple(sorted({str(s.get("label")) for s in spans if isinstance(s, dict) and s.get("label")}))


@dataclass
class CaseResult:
    """One fixture row's outcome."""

    index: int
    expected_block: bool
    actual_block: bool
    kind: str
    labels: tuple[str, ...]
    context_type: str
    text: str
    detail: str = ""


@dataclass
class Sides:
    """False-accept and false-reject, counted separately and never summed.

    There is deliberately no `accuracy`, no `passed`, and no combined total on
    this object. RC-11: a single aggregate over a mixed must-block/must-not-block
    population hides which of two opposite-cost errors moved.
    """

    fa_errors: int = 0
    fa_denominator: int = 0
    fr_errors: int = 0
    fr_denominator: int = 0
    fa_causes: Counter = field(default_factory=Counter)
    fr_causes: Counter = field(default_factory=Counter)
    negative_label_coverage: Counter = field(default_factory=Counter)

    @property
    def fa_rate(self) -> float | None:
        """None, not 0.0, when there are no must-block rows to be wrong about."""
        return self.fa_errors / self.fa_denominator if self.fa_denominator else None

    @property
    def fr_rate(self) -> float | None:
        return self.fr_errors / self.fr_denominator if self.fr_denominator else None

    @property
    def total_errors(self) -> int:
        """Only for the exit code. Never printed as a rate."""
        return self.fa_errors + self.fr_errors


def summarize(results: list[CaseResult]) -> Sides:
    """Fold per-case outcomes into the two sides plus their cause histograms."""
    sides = Sides()
    for r in results:
        if r.expected_block:
            sides.fa_denominator += 1
            if r.kind == FALSE_ACCEPT:
                sides.fa_errors += 1
                for label in r.labels or ("<unlabelled>",):
                    sides.fa_causes[label] += 1
        else:
            sides.fr_denominator += 1
            for label in r.labels or ("<no-pii-span>",):
                sides.negative_label_coverage[label] += 1
            if r.kind == FALSE_REJECT:
                sides.fr_errors += 1
                sides.fr_causes[r.context_type or "<no-context-type>"] += 1
    return sides


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "text" not in row or "expected_match" not in row:
            raise ValueError(f"{path}:{lineno}: expected text and expected_match fields")
        rows.append(row)
    return rows


def evaluate(rows: list[dict[str, Any]], hook: Path) -> list[CaseResult]:
    """Run `hook` over every row and return one CaseResult each."""
    temp = Path(tempfile.mkdtemp(prefix="pii_fixture_eval_"))
    results: list[CaseResult] = []
    try:
        _run(["git", "init", "-q"], temp)
        _run(["git", "config", "user.email", "fixture@example.invalid"], temp)
        _run(["git", "config", "user.name", "Fixture"], temp)

        for idx, row in enumerate(rows, 1):
            _clear_worktree(temp)
            case_path = temp / f"case_{idx:02d}.txt"
            case_path.write_text(str(row["text"]) + "\n")
            _run(["git", "add", case_path.name], temp)

            proc = _run([str(hook)], temp, check=False)
            blocked = proc.returncode != 0
            expected = bool(row["expected_match"])
            results.append(CaseResult(
                index=idx,
                expected_block=expected,
                actual_block=blocked,
                kind=classify(expected, blocked),
                labels=row_labels(row),
                context_type=str(row.get("context_type") or ""),
                text=str(row["text"]),
                detail="\n".join(proc.stderr.strip().splitlines()[:3]),
            ))
    finally:
        shutil.rmtree(temp)

    return results


def _histogram(counter: Counter) -> str:
    if not counter:
        return "(none)"
    return ", ".join(f"{k}={v}" for k, v in sorted(counter.items()))


def report(sides: Sides, results: list[CaseResult]) -> list[str]:
    """The two sides, printed separately, with the non-computable side named."""
    lines = [
        "PII fixture eval -- false-accept and false-reject reported SEPARATELY (RC-11).",
        f"  false-accept (PII the hook let through): {sides.fa_errors}/{sides.fa_denominator} "
        f"must-block rows"
        + (f" = {sides.fa_rate:.1%}" if sides.fa_rate is not None else " = n/a (no must-block rows)"),
        f"    cause histogram (missed label kind): {_histogram(sides.fa_causes)}",
        f"  false-reject (clean text the hook blocked): {sides.fr_errors}/{sides.fr_denominator} "
        f"must-not-block rows"
        + (f" = {sides.fr_rate:.1%}" if sides.fr_rate is not None else " = n/a (no must-not-block rows)"),
        f"    cause histogram (context_type of over-block): {_histogram(sides.fr_causes)}",
        "  NOT COMPUTABLE HERE: the FIELD false-accept rate. The must-block rows are hand-written",
        "    and are the only labelled PII in this repo, so the rate above estimates the hook's",
        "    behaviour on secrets someone already thought of and nothing else. The negative-side",
        "    label coverage below is reported in its place -- a label kind with no reachable",
        "    must-not-block row has an untested false-reject direction.",
        f"    negative-side label coverage: {_histogram(sides.negative_label_coverage)}",
        "  Provenance: fixture and hook share an origin commit and the fixture has been edited to",
        "    agree with the hook, so these are same-sample observations, not independent estimates.",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PII pre-commit hook against the fixture.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--hook", type=Path, default=DEFAULT_HOOK)
    args = parser.parse_args()

    rows = load_rows(args.fixture)
    results = evaluate(rows, args.hook)
    sides = summarize(results)

    for line in report(sides, results):
        print(line)

    failures = [r for r in results if r.kind in (FALSE_ACCEPT, FALSE_REJECT)]
    if failures:
        for r in failures:
            print(
                f"{r.kind} case {r.index}: expected_block={r.expected_block} "
                f"actual_block={r.actual_block} text={r.text[:100]!r}\n{r.detail}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

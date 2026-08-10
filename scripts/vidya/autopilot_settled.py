#!/usr/bin/env python3
"""Read-only Vidya standing for AutoPilot operator-hypothesis resolutions.

This is deliberately a planner lookup, not a hypothesis-generation gate.  It
answers whether the trial evidence named by a resolution is still usable after
the append-only AutoPilot supersession ledger is folded.  It never appends a
Vidya frame and never mutates either repository.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.autopilot_journal import as_record  # noqa: E402
from measurement_record import grade  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORCH_ROOT = REPO_ROOT / "repos" / "epyc-orchestrator"
DEFAULT_RESOLUTIONS = (
    DEFAULT_ORCH_ROOT / "orchestration" / "operator_hypothesis_resolutions.jsonl"
)


@dataclass(frozen=True)
class TrialStanding:
    trial_id: int
    shard: str = ""
    state: str = "unmapped"
    grade_q: str = ""
    grade_t: str = ""
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "shard": self.shard,
            "state": self.state,
            "grade": {"Q": self.grade_q, "T": self.grade_t} if self.grade_q else None,
            "reasons": list(self.reasons),
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _journal_view(orch_root: Path) -> dict[int, list[tuple[Path, dict[str, Any]]]]:
    """Fold journal supersessions without importing AutoPilot runtime code."""
    trials: dict[int, list[tuple[Path, dict[str, Any]]]] = {}
    supersessions: list[dict[str, Any]] = []
    for shard in sorted((orch_root / "orchestration").glob("autopilot_journal*.jsonl")):
        for row in _read_jsonl(shard):
            if isinstance(row.get("trial_id"), int):
                trials.setdefault(int(row["trial_id"]), []).append((shard, row))
            elif row.get("type") == "supersession":
                supersessions.append(row)

    for event in supersessions:
        fields = event.get("fields")
        targets = event.get("target_trial_ids")
        if not isinstance(fields, dict) or not isinstance(targets, list):
            continue
        for raw_target in targets:
            try:
                target = int(raw_target)
            except (TypeError, ValueError):
                continue
            for index, (shard, row) in enumerate(trials.get(target, [])):
                effective = copy.deepcopy(row)
                effective.update(copy.deepcopy(fields))
                trials[target][index] = (shard, effective)
    return trials


def trial_standing(
    trial_id: int,
    *,
    journal_view: dict[int, list[tuple[Path, dict[str, Any]]]],
) -> TrialStanding:
    matches = journal_view.get(int(trial_id), [])
    if not matches:
        return TrialStanding(trial_id, reasons=("no journal row for cited trial",))
    if len(matches) != 1:
        return TrialStanding(
            trial_id,
            state="ambiguous",
            reasons=(f"trial id occurs in {len(matches)} journal shards",),
        )
    shard, row = matches[0]
    corrupted_by = str(row.get("bug_corrupted_by") or "").strip()
    if corrupted_by:
        return TrialStanding(
            trial_id,
            shard=shard.name,
            state="invalidated",
            reasons=(f"superseded/effective row is bug_corrupted_by={corrupted_by}",),
        )
    measurement = row.get("measurement")
    if not isinstance(measurement, dict) or not measurement or measurement.get("capture_error"):
        return TrialStanding(
            trial_id,
            shard=shard.name,
            state="ungraded",
            reasons=("trial predates a usable write-time measurement tuple",),
        )
    try:
        record = as_record(shard, row)
        q, t, reasons = grade(record)
    except Exception as exc:  # fail explicit: absence of a grade is not a weak pass
        return TrialStanding(
            trial_id,
            shard=shard.name,
            state="ungraded",
            reasons=(f"Vidya grading failed: {type(exc).__name__}: {exc}",),
        )
    state = "sealed" if (q, t) == ("Witnessed", "Attested") else "provisional"
    return TrialStanding(
        trial_id,
        shard=shard.name,
        state=state,
        grade_q=q,
        grade_t=t,
        reasons=tuple(str(reason) for reason in reasons),
    )


def resolution_standings(
    *,
    orch_root: Path = DEFAULT_ORCH_ROOT,
    resolutions_path: Path = DEFAULT_RESOLUTIONS,
) -> dict[str, Any]:
    rows = _read_jsonl(resolutions_path)
    view = _journal_view(orch_root)
    resolutions: list[dict[str, Any]] = []
    for row in rows:
        hypothesis_id = str(row.get("hypothesis_id") or "").strip()
        ids = row.get("evidence_trial_ids") or []
        standings = [trial_standing(int(tid), journal_view=view) for tid in ids]
        states = {item.state for item in standings}
        if not standings:
            effective = "ungraded"
        elif states == {"sealed"}:
            effective = "sealed"
        elif "invalidated" in states or "ambiguous" in states:
            effective = "review_required"
        else:
            effective = "provisional"
        resolutions.append(
            {
                "hypothesis_id": hypothesis_id,
                "recorded_status": row.get("status"),
                "effective_standing": effective,
                "trials": [item.as_dict() for item in standings],
            }
        )
    return {
        "schema_version": "autopilot-settled-ground.v1",
        "read_only": True,
        "resolutions": resolutions,
    }


def render(payload: dict[str, Any]) -> str:
    rows = payload.get("resolutions") or []
    if not rows:
        return "  (none; no operator-hypothesis resolutions recorded)"
    lines = ["  Read-only Vidya check of previously resolved operator hypotheses:"]
    for row in rows:
        lines.append(
            f"  - [{row['hypothesis_id']}] recorded={row['recorded_status']} "
            f"standing={row['effective_standing']}"
        )
        for trial in row.get("trials") or []:
            grade_text = ""
            if trial.get("grade"):
                grade_text = f" grade={trial['grade']['Q']}/{trial['grade']['T']}"
            lines.append(
                f"      trial #{trial['trial_id']} {trial['state']}{grade_text}; "
                + "; ".join(trial.get("reasons") or [])[:260]
            )
        if row["effective_standing"] == "review_required":
            lines.append(
                "      RETRACTION/IDENTITY ALERT: do not treat this region as settled until "
                "the resolution is re-adjudicated."
            )
        elif row["effective_standing"] == "provisional":
            lines.append(
                "      This is not promotion-grade evidence; it may guide exploration only."
            )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orch-root", type=Path, default=DEFAULT_ORCH_ROOT)
    parser.add_argument("--resolutions", type=Path, default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = resolution_standings(
        orch_root=args.orch_root,
        resolutions_path=args.resolutions,
    )
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else render(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

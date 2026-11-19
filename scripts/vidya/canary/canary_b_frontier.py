"""Canary B frontier assertion (VB-CANARY-B-FRONTIER): pure logic, no orchestrator import.

Question: once AutoPilot records a post-fence frontier keep, does that trial id (with its
numbers) reach the planner-facing frontier channels? Until a real qualifying journal row
exists the assertion is NOT EXERCISED (never FAIL). Two labelled SYNTHETIC controls, built in
CANARY_SCRATCH only (never the orchestrator journal or the ledger), prove the assertion can
both see a qualifying keep (positive) and refuses to see a fenced/excluded row (negative).

The renderer (rows -> channel text) is injected: canary_b.py supplies the real orchestrator
renderer (journal -> archive -> pareto_summary / pareto_geometry / insights_structured).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Mapping

FENCE_TS_DEFAULT = 1786378983.880697  # pareto_exclude_before_ts, 2026-08-10T16:23Z
SYNTHETIC_LABEL = "SYNTHETIC-CONTROL"
# Channels that carry a fenced frontier. journal_summary is deliberately excluded: it is
# "unfenced (all epochs)" by its own header, so a pre-fence row legitimately appears there.
FRONTIER_CHANNELS = ("pareto_summary", "pareto_geometry", "insights_structured")

NOT_EXERCISED, PASS, FAIL, CONTROL_FAILED = "NOT_EXERCISED", "PASS", "FAIL", "CONTROL_FAILED"


def _epoch(row: Mapping) -> float | None:
    raw = row.get("timestamp")
    if not raw:
        return None
    text = str(raw)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return None


def qualifies(row: Mapping, fence_ts: float) -> bool:
    """A real trigger row: after the fence, frontier, a kept decision, not bug-corrupted."""
    ep = _epoch(row)
    return (ep is not None and ep >= fence_ts
            and row.get("pareto_status") == "frontier"
            and row.get("keep_revert_decision") == "keep"
            and not row.get("bug_corrupted_by")
            and bool(row.get("trial_id")))


def qualifying_rows(rows: Iterable[Mapping], fence_ts: float = FENCE_TS_DEFAULT) -> list[dict]:
    return [dict(r) for r in rows if qualifies(r, fence_ts)]


def numbers_of(row: Mapping) -> dict[str, str]:
    """The strings the prompt must carry, formatted as the journal/archive text formats them."""
    return {"trial": f"#{int(row['trial_id'])}", "quality": f"{float(row['quality']):.3f}"}


def trial_visible(channels: Mapping[str, str], row: Mapping) -> bool:
    n = numbers_of(row)
    text = "\n".join(str(channels.get(c) or "") for c in FRONTIER_CHANNELS)
    return n["trial"] in text and n["quality"] in text


def synthetic_rows(fence_ts: float = FENCE_TS_DEFAULT) -> tuple[dict, dict]:
    """(positive, negative): a post-fence frontier keep and a pre-fence excluded frontier row
    (the shape of real trial 1472). Ids are far outside the live id range."""
    base = {"species": "numeric_swarm", "action_type": "numeric_trial", "tier": 1,
            "cost": 0.5, "reliability": 0.98, "pareto_status": "frontier",
            "config_snapshot": {}, "config_diff": {}, "eval_details": {},
            "hypothesis": SYNTHETIC_LABEL}
    after = datetime.fromtimestamp(fence_ts + 90 * 86400).astimezone().isoformat()
    before = datetime.fromtimestamp(fence_ts - 5 * 86400).astimezone().isoformat()
    pos = dict(base, trial_id=990001, timestamp=after, quality=2.345, speed=77.7,
               keep_revert_decision="keep")
    neg = dict(base, trial_id=990002, timestamp=before, quality=2.111, speed=50.0,
               keep_revert_decision="excluded")
    return pos, neg


def run_controls(renderer: Callable[[list[dict], Path], Mapping[str, str]], scratch: Path,
                 fence_ts: float = FENCE_TS_DEFAULT) -> dict:
    """renderer(rows, scratch_dir) -> channel texts. Both controls render ONE synthetic journal
    holding the positive and the negative row, so a leak of the fenced row is visible."""
    pos, neg = synthetic_rows(fence_ts)
    assert qualifies(pos, fence_ts) and not qualifies(neg, fence_ts), "fixture self-check"
    scratch = Path(scratch)
    out = {"label": SYNTHETIC_LABEL, "scratch": str(scratch)}
    try:
        channels = renderer([pos, neg], scratch)
    except Exception as exc:  # noqa: BLE001 - a broken control is a result, not a crash
        out.update(ok=False, error=f"{type(exc).__name__}: {exc}")
        return out
    out["positive_visible"] = trial_visible(channels, pos)
    out["negative_hidden"] = not trial_visible(channels, neg)
    out["ok"] = out["positive_visible"] and out["negative_hidden"]
    return out


def frontier_verdict(real_rows: Iterable[Mapping], channels: Mapping[str, str], controls: dict,
                     fence_ts: float = FENCE_TS_DEFAULT) -> dict:
    """NOT_EXERCISED when no real qualifying row exists (never FAIL). A failed control makes the
    assertion untrustworthy (CONTROL_FAILED), whatever the real rows say."""
    qual = qualifying_rows(real_rows, fence_ts)
    res = {"qualifying_real_rows": [int(r["trial_id"]) for r in qual], "controls": controls}
    if not controls.get("ok"):
        res.update(status=CONTROL_FAILED, reason="synthetic control did not behave; assertion untrusted")
    elif not qual:
        res.update(status=NOT_EXERCISED,
                   reason="no real post-fence frontier keep in the journal (hold: AutoPilot has not run)")
    else:
        missing = [int(r["trial_id"]) for r in qual if not trial_visible(channels, r)]
        res.update(missing=missing, status=FAIL if missing else PASS,
                   reason=("qualifying keep(s) absent from the planner frontier channels" if missing
                           else "every qualifying keep appears with its id and quality"))
    return res


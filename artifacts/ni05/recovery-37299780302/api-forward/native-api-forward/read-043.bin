"""AP-55-ARM preparation: the shadow run must be able to answer "would enforce have held?".

Pins: shadow ``hold`` stays False while the recorded counterfactual carries the
enforce/strict answer from the same rule; the summary carries it; older summaries
are re-derived identically (basis ``reconstructed``); an errored gate would hold;
the review script counts gated / attempted / committed promotions, refuses to call
a window without a shadow verdict ready (exit 3), and never writes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import ap55_shadow_review as review  # noqa: E402
from src.autopilot_core import ap55_promotion_gate as g  # noqa: E402


def _gate(mode: str) -> dict:
    return g.promotion_gate(
        [],
        tier=1,
        baseline_revision="r1",
        candidate_key="k",
        candidate_counts=(5, 10),
        candidate_fingerprint=None,
        counts_fn=lambda row: (0, 0),
        key_fn=lambda row: "",
        mode=mode,
    )


def test_shadow_never_holds_but_records_what_enforce_would_do():
    shadow, enforce = _gate("shadow"), _gate("enforce")
    assert shadow["hold"] is False
    assert enforce["hold"] is True
    assert shadow["counterfactual"]["enforce"] == {
        "hold": enforce["hold"], "hold_reasons": enforce["hold_reasons"],
    }
    assert shadow["counterfactual"] == enforce["counterfactual"]
    summary = g.gate_summary(shadow)
    assert summary["hold"] is False
    assert summary["would_hold_enforce"] is True
    assert summary["would_hold_enforce_reasons"] == enforce["hold_reasons"]
    assert "would_hold_strict" in summary


def test_recorded_and_reconstructed_counterfactuals_agree():
    summary = g.gate_summary(_gate("shadow"))
    legacy = {k: v for k, v in summary.items() if not k.startswith("would_hold")}
    recorded = g.would_hold_from_summary(summary)
    rebuilt = g.would_hold_from_summary(legacy)
    assert recorded["basis"] == "recorded"
    assert rebuilt["basis"] == "reconstructed"
    assert (recorded["hold"], recorded["hold_reasons"]) == (rebuilt["hold"], rebuilt["hold_reasons"])
    assert g.would_hold_from_summary({}) == {"basis": "absent", "hold": None, "hold_reasons": []}
    with pytest.raises(ValueError):
        g.would_hold_from_summary(summary, "shadow")


def test_errored_gate_would_hold_under_enforce(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(g, "seed_rerun_verdict", boom)
    gate = _gate("shadow")
    assert gate["hold"] is False
    summary = g.gate_summary(gate)
    assert summary["would_hold_enforce"] is True
    legacy = {k: v for k, v in summary.items() if not k.startswith("would_hold")}
    assert g.would_hold_from_summary(legacy)["hold_reasons"] == ["gate_error"]


# ── review script ────────────────────────────────────────────────────────


def _row(tid: int, summary: dict | None, *, attempted: bool = False, **kw) -> dict:
    details: dict = {}
    if summary is not None:
        details["ap55_promotion_gate"] = summary
    if attempted:
        details["promotion_status"] = "pending_commit"
    return {"trial_id": tid, "timestamp": f"2026-09-18T00:00:{tid:02d}+00:00",
            "eval_details": details, **kw}


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    d = tmp_path / "orchestration"
    d.mkdir()
    (d / "autopilot_journal.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return d


def test_review_counts_the_three_denominators(tmp_path, capsys):
    hold = g.gate_summary(_gate("shadow"))
    assert hold["would_hold_enforce"] is True
    clear = {**hold, "would_hold_enforce": False, "would_hold_enforce_reasons": []}
    legacy_hold = {k: v for k, v in hold.items() if not k.startswith("would_hold")}
    rows = [
        _row(0, hold),  # before the window
        _row(1, clear, attempted=True),  # committed, not held
        _row(2, hold, attempted=True),  # committed, held
        _row(3, legacy_hold, attempted=True),  # attempted only, held (reconstructed)
        _row(4, clear),  # gated only
        _row(5, None),  # no verdict
        _row(6, hold, attempted=True, bug_corrupted_by="abc"),
        {"type": "baseline_promotion", "source_trial_id": 1},
        {"type": "baseline_promotion", "source_trial_id": 2},
    ]
    d = _write(tmp_path, rows)
    before = (d / "autopilot_journal.jsonl").read_bytes()
    rep = review.review(d, since_trial=1)
    b = rep["enforce_would_hold"]
    assert (b["gated"]["n"], b["gated"]["would_hold"]) == (4, 2)
    assert (b["attempted"]["n"], b["attempted"]["would_hold"]) == (3, 2)
    assert (b["committed"]["n"], b["committed"]["would_hold"], b["committed"]["trial_ids"]) == (2, 1, [2])
    assert b["committed"]["rate"] == 0.5
    assert rep["counterfactual_basis"] == {"recorded": 3, "reconstructed": 1}
    assert rep["excluded"] == {"no_gate_verdict": 1, "bug_corrupted": 1}
    assert rep["verdict"].startswith("READY FOR REVIEW: enforce would have held 1 of 2")
    assert review.main(["--journal-dir", str(d), "--since-trial", "1"]) == 0
    assert "AUTOPILOT_AP55_PROMOTION_GATE shadow -> enforce" in capsys.readouterr().out
    assert (d / "autopilot_journal.jsonl").read_bytes() == before  # read-only


def test_review_without_a_shadow_run_is_not_ready(tmp_path):
    enforce = g.gate_summary(_gate("enforce"))
    d = _write(tmp_path, [_row(1, None), _row(2, enforce, attempted=True)])
    rep = review.review(d)
    assert rep["shadow_run_observed"] is False
    assert rep["verdict"].startswith("NOT READY")
    assert review.main(["--journal-dir", str(d), "--json"]) == review.NO_SHADOW_RUN_EXIT


def test_review_flags_a_mixed_window(tmp_path):
    d = _write(tmp_path, [_row(1, g.gate_summary(_gate("shadow"))),
                          _row(2, g.gate_summary(_gate("enforce")))])
    assert review.review(d)["verdict"].startswith("MIXED WINDOW")


def test_review_since_timestamp_filters(tmp_path):
    d = _write(tmp_path, [_row(1, g.gate_summary(_gate("shadow"))),
                          _row(9, g.gate_summary(_gate("shadow")))])
    since = review._parse_ts("2026-09-18T00:00:05+00:00")
    rep = review.review(d, since=since)
    assert rep["window"]["first_trial_id"] == 9
    assert rep["enforce_would_hold"]["gated"]["n"] == 1

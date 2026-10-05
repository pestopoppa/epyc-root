"""Dashboard `_pareto_from_journal` must mirror the live archive's representative policy
(2026-06-04). A trusted within-noise row (mad_noise / reproduction_confirmed) is a
representative candidate, NOT corruption: cluster by config fingerprint, admit one
robust-MEDIAN representative per config, and still exclude genuine corruption
(kills / reloads / commit-invalidations). Dominance is tested on the median, not a lucky
per-trial speed sample.
"""
import json

import src.api.routes.dashboard as dash


def _write_journal(tmp_path, rows):
    p = tmp_path / "journal.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return p


def _row(tid, q, s, *, tier=1, cost=0.5, rel=1.0, **extra):
    r = {
        "trial_id": tid, "tier": tier, "quality": q, "speed": s, "cost": cost,
        "reliability": rel, "timestamp": f"2026-06-04T10:{tid:02d}:00+00:00",
        "config_snapshot": {"type": "seed_batch", "n_questions": 10},
    }
    r.update(extra)
    return r


def test_within_noise_cluster_becomes_one_median_representative(tmp_path, monkeypatch):
    rows = [
        _row(1, 1.90, 45.0, rel=0.97),  # normal admit: higher q, lower reliability
        # 3 trusted within-noise reproductions of the SAME config, noisy speed, perfect rel:
        _row(10, 1.80, 50.0, bug_corrupted_by="mad_noise"),                 # legacy tag
        _row(11, 1.80, 70.0, bug_corrupted_by="mad_noise"),                 # lucky-fast sample
        _row(12, 1.80, 60.0, eval_details={"learning_exclusion": {"by": "mad_noise"}}),  # post-fix
        _row(13, 2.00, 99.0, bug_corrupted_by="autopilot_killed_mid_trial"),  # genuine corruption
    ]
    monkeypatch.setattr(dash, "_AUTOPILOT_JOURNAL_PATH", _write_journal(tmp_path, rows))
    arch = dash._pareto_from_journal(None, current_run_only=False)

    reps = [e for e in arch["frontier"] if e.get("is_representative")]
    assert len(reps) == 1, "one representative per config fingerprint"
    assert reps[0]["n_reproductions"] == 3
    assert reps[0]["objectives"][1] == 60.0, "MEDIAN of [50,70,60], not the lucky 70"

    all_tids = {e["trial_id"] for e in arch["all_entries"]}
    assert 13 not in all_tids, "genuine corruption (kill) stays excluded"

    # rep (q1.8, rel1.0) and normal (q1.9, rel0.97) are mutually non-dominated → both on frontier
    assert {round(e["objectives"][0], 2) for e in arch["frontier"]} == {1.8, 1.9}


def test_legacy_mad_noise_rows_are_no_longer_skipped(tmp_path, monkeypatch):
    """Regression for the frozen panel: a journal whose only post-baseline rows are
    legacy bug_corrupted_by='mad_noise' must still surface a representative, not vanish."""
    rows = [
        _row(1, 1.50, 40.0),  # baseline normal point
        _row(2, 1.80, 55.0, bug_corrupted_by="mad_noise"),
        _row(3, 1.80, 57.0, bug_corrupted_by="mad_noise"),
    ]
    monkeypatch.setattr(dash, "_AUTOPILOT_JOURNAL_PATH", _write_journal(tmp_path, rows))
    arch = dash._pareto_from_journal(None, current_run_only=False)
    assert any(e.get("is_representative") for e in arch["frontier"])
    # the q=1.8 representative dominates the q=1.5/40 baseline → frontier advanced past it
    assert max(e["objectives"][0] for e in arch["frontier"]) == 1.80


def test_genuine_corruption_reasons_excluded(tmp_path, monkeypatch):
    """Kills, exogenous reloads, and commit-SHA invalidations are NOT within-noise and must
    be dropped entirely (only mad_noise is the de-overloaded benign tag)."""
    rows = [
        _row(1, 1.50, 40.0),
        _row(2, 9.9, 99.0, bug_corrupted_by="exogenous_operator_reload"),
        _row(3, 9.9, 99.0, bug_corrupted_by="deadbeefcafe1234"),  # commit-sha scrub tag
    ]
    monkeypatch.setattr(dash, "_AUTOPILOT_JOURNAL_PATH", _write_journal(tmp_path, rows))
    arch = dash._pareto_from_journal(None, current_run_only=False)
    all_tids = {e["trial_id"] for e in arch["all_entries"]}
    assert all_tids == {1}, "only the clean baseline row survives"

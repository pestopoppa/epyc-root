"""Pareto representative-admission policy correction (2026-06-04).

A TRUSTED within-quality-noise measurement (mad_noise / reproduction_confirmed) is
excluded from AP-22 / strategy learning, but it must still be able to extend the
MULTI-OBJECTIVE frontier on speed / cost / reliability. `ParetoArchive.upsert_representative`
admits ONE representative point per stable config fingerprint, with dominance tested on
robust-MEDIAN objectives across the reproduction cluster — never a lucky single-trial
speed sample. See `handoffs/active/autopilot-continuous-optimization.md` (2026-06-04 entry).

Objectives are (quality, speed, -cost, reliability), all maximised.
"""
from scripts.autopilot.pareto_archive import ParetoArchive, ParetoEntry


def _archive(tmp_path) -> ParetoArchive:
    return ParetoArchive(state_path=tmp_path / "state.json")


def test_representative_admitted_when_non_dominated_on_reliability(tmp_path):
    """The real stuck case: a within-noise quality level (q=1.816) at perfect reliability
    is non-dominated by a higher-quality-but-lower-reliability point and must reach the
    frontier — the exact region the quality-only MAD filter used to hide."""
    a = _archive(tmp_path)
    # Existing frontier: higher quality, but reliability 0.974 (like real trial 256).
    a.update(ParetoEntry(trial_id=256, objectives=(1.895, 59.7, -0.5, 0.974), eval_tier=1))
    status, _ = a.upsert_representative(
        "cfgA", 1, (1.816, 56.4, -0.5, 1.0), trial_id=379
    )
    assert status == "frontier"
    assert a.frontier_size(1) == 2  # neither dominates the other


def test_dominance_uses_cluster_median_not_lucky_sample(tmp_path):
    """Guardrail 1: a single lucky-fast speed sample must not set frontier geometry —
    dominance is tested on the cluster MEDIAN."""
    a = _archive(tmp_path)
    fp = "cfgA"
    speeds = [54.5, 60.75, 43.8, 56.4, 58.2]  # median 56.4; 60.75 is the lucky sample
    status = median = None
    for tid, spd in enumerate(speeds, start=10):
        status, median = a.upsert_representative(fp, 1, (1.816, spd, -0.5, 1.0), trial_id=tid)
    assert median[1] == 56.4, "representative speed is the median, not the 60.75 sample"
    # Exactly one representative entry for the fingerprint — not five noisy points.
    reps = [e for e in a.frontier(1) if e.config_fingerprint == fp]
    assert len(reps) == 1
    assert reps[0].n_reproductions == 5
    assert reps[0].objectives[1] == 56.4


def test_dedup_by_fingerprint_not_trial_id(tmp_path):
    """Reproductions of the same config (even via different trial ids / action types) collapse
    to a single representative; a different config gets its own."""
    a = _archive(tmp_path)
    # cfgA faster/lower-quality, cfgB slower/higher-quality → mutually non-dominated, so
    # both stay on the frontier and dedup is observable per fingerprint.
    a.upsert_representative("cfgA", 1, (1.70, 55.0, -0.5, 1.0), trial_id=1)
    a.upsert_representative("cfgA", 1, (1.70, 57.0, -0.5, 1.0), trial_id=2)  # same fp
    a.upsert_representative("cfgB", 1, (1.90, 45.0, -0.5, 1.0), trial_id=3)  # different fp
    fps = {e.config_fingerprint for e in a.frontier(1)}
    assert fps == {"cfgA", "cfgB"}
    assert sum(1 for e in a.frontier(1) if e.config_fingerprint == "cfgA") == 1


def test_dominated_representative_stays_off_frontier(tmp_path):
    """If the robust-median representative is dominated on every axis, it is recorded but
    does not pollute the frontier."""
    a = _archive(tmp_path)
    a.update(ParetoEntry(trial_id=1, objectives=(2.0, 80.0, -0.1, 1.0), eval_tier=1))
    status, _ = a.upsert_representative("weak", 1, (1.5, 40.0, -0.5, 0.9), trial_id=2)
    assert status == "dominated"
    assert all(e.config_fingerprint != "weak" for e in a.frontier(1))


def test_empty_fingerprint_falls_back_to_plain_update(tmp_path):
    """No stable identity → behave like a normal per-trial update (no clustering)."""
    a = _archive(tmp_path)
    status, objs = a.upsert_representative("", 1, (1.8, 50.0, -0.5, 1.0), trial_id=1)
    assert status == "frontier"
    assert objs == (1.8, 50.0, -0.5, 1.0)
    assert a.reproduction_count(1, "") == 0  # nothing clustered


def test_tier_segregation(tmp_path):
    """A (tier, fingerprint) is distinct per tier — a T2 representative never lands on T1."""
    a = _archive(tmp_path)
    a.upsert_representative("cfgA", 1, (1.8, 50.0, -0.5, 1.0), trial_id=1)
    a.upsert_representative("cfgA", 2, (1.5, 40.0, -0.5, 1.0), trial_id=2)
    assert a.reproduction_count(1, "cfgA") == 1
    assert a.reproduction_count(2, "cfgA") == 1
    assert a.frontier_size(1) == 1 and a.frontier_size(2) == 1


def test_cluster_and_representative_persist_round_trip(tmp_path):
    """The reproduction cluster + representative survive explicit payload reloads so medians
    keep accumulating across autopilot restarts."""
    a = _archive(tmp_path)
    for tid, spd in [(1, 50.0), (2, 60.0)]:
        a.upsert_representative("cfgA", 1, (1.8, spd, -0.5, 1.0), trial_id=tid)
    payload = {
        "all_entries": [entry.to_dict() for entry in a._all_entries],
        "hv_history_by_tier": {
            str(tier): [[trial_id, hv] for trial_id, hv in history]
            for tier, history in a._hv_history_by_tier.items()
        },
        "repro_clusters": a._repro_clusters,
    }

    b = ParetoArchive.from_archive_payload(
        payload,
        state_path=tmp_path / "state.json",
        read_only=False,
    )

    assert b.reproduction_count(1, "cfgA") == 2
    assert b.frontier_size(1) == 1
    # A further reproduction continues the median over the persisted cluster.
    _, median = b.upsert_representative("cfgA", 1, (1.8, 70.0, -0.5, 1.0), trial_id=3)
    assert median[1] == 60.0  # median of [50, 60, 70]

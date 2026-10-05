"""All-era Pareto view (2026-07-03): `/dashboard/api/pareto?scope=all_eras` must show
EVERY journaled trial across instrument eras — era-labeled from the append-only
registry (instrument_eras.yaml) — instead of clearing history at each era cutover.
Scaling contract: pre-E2 speeds get the codified ×0.5 read-time deinflation (the
2026-06-01 double-count fix); later boundaries (E5 v6+iqk cutover) are labeled,
never rescaled. scope="current" keeps the operational exclude-before-epoch view.
"""
import asyncio
import json

import src.api.routes.dashboard as dash

ERAS_YAML = """
eras:
  - id: E0
    until: "2026-04-26"
    scope: cpu_bench
    note: "ignored: not an autopilot scope"
  - id: E2
    from: "2026-06-01T19:20:16Z"
    scope: autopilot_speed
    note: "speed de-double-count"
  - id: E3a
    from: "2026-06-04T06:41:00Z"
    scope: autopilot_quality
    note: "tool sentinels live"
  - id: E5-autopilot-speed
    from: "2026-06-26T22:07:11Z"
    scope: autopilot_speed
    note: "v6+iqk cutover"
"""

E2_TS = 1780341616.0
E5_TS = 1782511631.0


def _eras_file(tmp_path, monkeypatch, text=ERAS_YAML):
    p = tmp_path / "instrument_eras.yaml"
    p.write_text(text)
    monkeypatch.setenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", str(p))
    return p


def _row(tid, q, s, ts, *, tier=1, cost=0.5, rel=1.0):
    return {
        "trial_id": tid, "tier": tier, "quality": q, "speed": s, "cost": cost,
        "reliability": rel, "timestamp": ts,
        "config_snapshot": {"type": "seed_batch", "n_questions": 10},
    }


def _journal(tmp_path, monkeypatch, rows):
    p = tmp_path / "journal.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(dash, "_AUTOPILOT_JOURNAL_PATH", p)
    return p


def _state(tmp_path, monkeypatch, **extra):
    p = tmp_path / "state.json"
    data = {
        "trial_counter": 999,
        "pareto_epoch_ts": E5_TS,
        "pareto_exclude_before_ts": E5_TS,
        "pareto_pre_epoch_speed_factor": 0.5,
    }
    data.update(extra)
    p.write_text(json.dumps(data))
    monkeypatch.setattr(dash, "_AUTOPILOT_STATE_PATH", p)
    return p


ROWS = [
    _row(1, 1.50, 80.0, "2026-05-30T12:00:00+00:00"),   # pre-E2: speed inflated 2x
    _row(2, 1.60, 50.0, "2026-06-02T12:00:00+00:00"),   # E2: honest v5 speed
    _row(3, 1.70, 52.0, "2026-06-10T12:00:00+00:00"),   # E3a
    _row(4, 1.80, 70.0, "2026-06-28T12:00:00+00:00"),   # E5: v6+iqk
]


def _call(scope, max_dominated=600):
    resp = asyncio.run(dash.pareto(max_dominated=max_dominated, scope=scope))
    return json.loads(resp.body)


def test_era_regions_from_registry(tmp_path, monkeypatch):
    _eras_file(tmp_path, monkeypatch)
    regions, err = dash._autopilot_era_regions()
    assert err is None
    assert [r["id"] for r in regions] == ["pre-E2", "E2", "E3a", "E5"]
    assert regions[0]["from_ts"] is None and regions[0]["until_ts"] == E2_TS
    assert regions[1]["from_ts"] == E2_TS
    assert regions[-1]["until_ts"] is None
    # non-autopilot scopes (cpu_bench E0) never become boundaries
    assert all("E0" not in (r.get("era_ids") or []) for r in regions)


def test_era_regions_fail_open_with_error(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", str(tmp_path / "missing.yaml"))
    regions, err = dash._autopilot_era_regions()
    assert regions == [] and "unavailable" in err


def test_region_index_for_ts(tmp_path, monkeypatch):
    _eras_file(tmp_path, monkeypatch)
    regions, _ = dash._autopilot_era_regions()
    assert dash._era_region_index_for_ts(regions, E2_TS - 1) == 0
    assert dash._era_region_index_for_ts(regions, E2_TS) == 1
    assert dash._era_region_index_for_ts(regions, E5_TS + 1) == 3
    assert dash._era_region_index_for_ts(regions, None) is None


def test_all_eras_scope_shows_and_deinflates_history(tmp_path, monkeypatch):
    _eras_file(tmp_path, monkeypatch)
    _journal(tmp_path, monkeypatch, ROWS)
    _state(tmp_path, monkeypatch)
    d = _call("all_eras")

    assert d["available"] and d["scope"] == "all_eras"
    assert d["source"] == "journal_all_eras"
    assert d["era_registry_error"] is None

    pts = {e["trial_id"]: e for lst in ([d["frontier"], d["dominated"]]) for e in lst}
    assert set(pts) == {1, 2, 3, 4}, "no era is cleared from the all-era view"
    # pre-E2 speed deinflated ×0.5; every other era untouched (E5 never rescales)
    assert pts[1]["objectives"][1] == 40.0 and pts[1]["speed_deinflated"]
    assert pts[2]["objectives"][1] == 50.0 and not pts[2]["speed_deinflated"]
    assert pts[4]["objectives"][1] == 70.0 and not pts[4]["speed_deinflated"]
    # era labels ride on every shipped point
    assert pts[1]["era"] == "pre-E2" and pts[1]["era_index"] == 0
    assert pts[2]["era"] == "E2" and pts[3]["era"] == "E3a" and pts[4]["era"] == "E5"

    eras = {e["id"]: e for e in d["eras"]}
    assert eras["pre-E2"]["n_points"] == 1
    assert eras["E5"]["first_trial_id"] == 4 and eras["E5"]["last_trial_id"] == 4
    # hypervolume history spans all eras, not just the post-cutover segment
    assert [h[0] for h in d["hypervolume_history"]] == [1, 2, 3, 4]


def test_current_scope_unchanged_and_excludes_pre_epoch(tmp_path, monkeypatch):
    _eras_file(tmp_path, monkeypatch)
    _journal(tmp_path, monkeypatch, ROWS)
    _state(tmp_path, monkeypatch)
    d = _call("current")

    assert d["scope"] == "current" and d["eras"] is None
    pts = {e["trial_id"] for lst in ([d["frontier"], d["dominated"]]) for e in lst}
    assert pts == {4}, "current view still scopes to the post-E5 era"
    assert d["exclusions"]["before_ts"]["count"] == 3


def test_pareto_payload_surfaces_active_testing_era(tmp_path, monkeypatch):
    _eras_file(tmp_path, monkeypatch)
    _journal(tmp_path, monkeypatch, ROWS)
    _state(
        tmp_path,
        monkeypatch,
        active_instrument_eras={
            "autopilot_speed": "E8-autopilot-speed",
            "cpu_bench": "E8-cpu-kernel",
        },
        frontier_rerun_required={
            "required": True,
            "reason": "E8-autopilot-speed production-consolidated-v8 era opened",
        },
        pareto_epoch_ts=1785004723.0,
        pareto_exclude_before_ts=1785004723.0,
    )
    d = _call("current")

    assert d["active_instrument_eras"] == {
        "autopilot_speed": "E8-autopilot-speed",
        "cpu_bench": "E8-cpu-kernel",
    }
    assert d["pareto_epoch_ts"] == 1785004723.0
    assert d["pareto_exclude_before_ts"] == 1785004723.0
    assert d["frontier_rerun_required"]["required"] is True
    assert "production-consolidated-v8" in d["frontier_rerun_required"]["reason"]


# v8 production cutover boundary (E8-autopilot-speed row, 2026-07-25T18:38:43Z).
E8_TS = 1785004723.0


def test_e8_boundary_region_from_repo_registry(monkeypatch):
    """Task A pin (2026-07-26): against the REAL repo registry, the E8 cutover
    must produce a region starting exactly at the E8-autopilot-speed boundary,
    and a post-boundary entry must label as E8 (current, not historical)."""
    monkeypatch.delenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", raising=False)
    regions, err = dash._autopilot_era_regions()
    assert err is None
    e8_regions = [r for r in regions if r["from_ts"] == E8_TS]
    assert e8_regions, (
        "E8 boundary (from_ts=1785004723.0) missing from instrument_eras.yaml "
        "autopilot-scoped regions"
    )
    assert any("E8" in str(r["id"]) for r in e8_regions)
    assert any("E8-autopilot-speed" in (r.get("era_ids") or []) for r in e8_regions)
    # An entry timestamped just after the boundary lands in the E8 region.
    entry = {"timestamp": E8_TS + 60.0}
    dash._label_pareto_entries_with_eras([entry], regions)
    assert "E8" in str(entry["era"])
    e8_index = e8_regions[0]["index"]
    assert entry["era_index"] == e8_index


def test_historical_instrument_label_on_all_era_view(tmp_path, monkeypatch):
    """Task B (quality-axis era honesty): every entry outside the LATEST era
    region is flagged historical_instrument=True; latest-region entries get
    False; values are labeled, NEVER rescaled by this flag."""
    _eras_file(tmp_path, monkeypatch)
    _journal(tmp_path, monkeypatch, ROWS)
    _state(tmp_path, monkeypatch)
    d = _call("all_eras")

    pts = {e["trial_id"]: e for lst in ([d["frontier"], d["dominated"]]) for e in lst}
    assert pts[4]["historical_instrument"] is False, "latest-era point must not be flagged"
    assert pts[1]["historical_instrument"] is True
    assert pts[2]["historical_instrument"] is True
    assert pts[3]["historical_instrument"] is True
    # Label-only contract: objectives untouched relative to the pre-existing
    # behaviour (E5 speed intact; the ONLY rescale remains pre-E2 deinflation).
    assert pts[4]["objectives"][1] == 70.0
    assert pts[3]["objectives"][1] == 52.0
    assert pts[1]["objectives"][1] == 40.0 and pts[1]["speed_deinflated"]


def test_historical_instrument_unknown_ts_is_null(tmp_path, monkeypatch):
    """Entries with no parsable timestamp get None (unknown), never False —
    the client must not render them as current-instrument points."""
    _eras_file(tmp_path, monkeypatch)
    regions, err = dash._autopilot_era_regions()
    assert err is None
    entries = [{"timestamp": None}, {"timestamp": "2026-06-28T12:00:00+00:00"}]
    dash._label_pareto_entries_with_eras(entries, regions)
    assert entries[0]["era_index"] is None
    assert entries[0]["historical_instrument"] is None
    assert entries[1]["era"] == "E5"
    assert entries[1]["historical_instrument"] is False


def test_all_eras_without_registry_shows_unscaled_with_warning(tmp_path, monkeypatch):
    """Registry unreadable → fail open WITHOUT deinflation (the state's
    pareto_epoch_ts is a rebase marker, not the E2 boundary) + surfaced error."""
    monkeypatch.setenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", str(tmp_path / "missing.yaml"))
    _journal(tmp_path, monkeypatch, ROWS)
    _state(tmp_path, monkeypatch)
    d = _call("all_eras")

    assert d["available"] and d["era_registry_error"]
    assert d["eras"] is None
    pts = {e["trial_id"]: e for lst in ([d["frontier"], d["dominated"]]) for e in lst}
    assert set(pts) == {1, 2, 3, 4}
    assert pts[1]["objectives"][1] == 80.0 and not pts[1]["speed_deinflated"]

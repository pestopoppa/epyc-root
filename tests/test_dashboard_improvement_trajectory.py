"""Production-anchored improvement history and secondary CoR drill-down."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from dashboard import loop_status

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "dashboard/static/loop.html"
HARNESS = REPO / "tests/js/render_harness.js"
PRODUCTION = {"resolved": True, "commit": "d" * 40,
              "label": "production-consolidated-v9"}


def _store(root: Path) -> None:
    con = sqlite3.connect(root / "experiments.db")
    con.execute("""CREATE TABLE experiments (
        attempt_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
        campaign_id TEXT NOT NULL, deployment TEXT, epoch_sha256 TEXT NOT NULL,
        hypothesis_id TEXT, mechanism_id TEXT, target_surface TEXT,
        target_symbol TEXT, statement TEXT, falsifier TEXT, status TEXT NOT NULL,
        effect_fraction REAL, exact_effect REAL, target_effect REAL,
        refusal_reason TEXT, result_sha256 TEXT, payload TEXT NOT NULL)""")
    con.commit()
    con.close()


def _insert(root: Path, attempt: str, recorded_at: str, mechanism: str,
            status: str, payload: dict, reason: str | None = None) -> None:
    con = sqlite3.connect(root / "experiments.db")
    con.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        attempt, recorded_at, "ak-loop", None, "e" * 64, None, mechanism,
        "tg128", "kernel", "statement", "falsifier", status, None, None,
        None, reason, None, json.dumps(payload)))
    con.commit()
    con.close()


def _accumulator(root: Path) -> None:
    (root / "accumulator-bundle.json").write_text(json.dumps({
        "schema": "epyc.autokernel.accumulator_bundle.v2",
        "champion_of_record": "a" * 40, "tip": "b" * 40,
        "keeps": ["akm-one", "akm-two", "akm-three"],
        "measurement_validity": "current_snapshot", "compounded_bench_pct": 3.25,
    }))


def _comparison(effect: float = 12.5) -> dict:
    return {"effect_pct": effect, "noise_floor_pct": 1.0, "pairs": 20,
            "surface": "tg128", "model": "/models/Qwen3.8-27B-Q8_0.gguf"}


def test_backend_admits_only_exact_three_way_production_history_join(tmp_path: Path) -> None:
    _store(tmp_path)
    head = "a" * 40
    comparison = _comparison()
    _insert(tmp_path, "keep", "2026-09-01T00:00:01Z", "akm-one", "kept",
            {"champion_head": head, "comparison": {"marginal": "not composed"}})
    reason = ("champion aaaaaaaaaaaa measures +12.500% against frozen production "
              "dddddddddddd (production-consolidated-v9) over 20 tg128 pairs, floor 1.0%")
    _insert(tmp_path, "refresh", "2026-09-01T00:00:00Z",
            "champion-vs-production", "champion_vs_production",
            {"mechanism_id": "champion-vs-production", "reason": reason}, reason)
    (tmp_path / "champion-vs-production.aaaaaaaaaaaa.json").write_text(
        json.dumps(comparison))

    rows = loop_status.read_knowledge(tmp_path)["body"]["trajectory_rows"]
    result = loop_status.improvement_trajectory(tmp_path, rows, PRODUCTION)
    headline = result["production_headline"]
    assert headline["state"] == "available"
    assert headline["curves"][0]["id"] == "Qwen3.8-27B-Q8_0.gguf"
    assert headline["curves"][0]["primary_surface"] == "tg128"
    assert len(headline["curves"][0]["surface_series"]) == 1
    assert headline["curves"][0]["points"][0]["gain_pct"] == 12.5
    assert "comparison" not in headline["curves"][0]["points"][0]

    comparison["effect_pct"] = 99.0
    (tmp_path / "champion-vs-production.aaaaaaaaaaaa.json").write_text(
        json.dumps(comparison))
    result = loop_status.improvement_trajectory(tmp_path, rows, PRODUCTION)
    assert result["production_headline"]["state"] == "unavailable"
    assert len(result["production_headline"]["evidence_errors"]) == 1


def test_backend_keeps_glm_cor_measurement_secondary(tmp_path: Path) -> None:
    _store(tmp_path)
    _accumulator(tmp_path)
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    assert result["production_headline"]["state"] == "unavailable"
    local = result["campaign_drilldown"]
    assert local["state"] == "available"
    assert local["basis"] == "gain_pct_vs_campaign_cor"
    assert local["bench_checkpoints"] == [{
        "keep_count": 3, "gain_pct": 3.25,
        "evidence_state": "cheap_screen_estimate",
    }]


def test_backend_distinguishes_absent_and_malformed_local_evidence(tmp_path: Path) -> None:
    _store(tmp_path)
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    assert result["campaign_drilldown"]["state"] == "absent"
    (tmp_path / "accumulator-bundle.json").write_text("not json")
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    assert result["campaign_drilldown"]["state"] == "malformed"


def test_backend_projects_bounded_experiment_events_without_comparison_samples(tmp_path: Path) -> None:
    _store(tmp_path)
    _insert(tmp_path, "kept", "2026-09-01T00:00:01Z", "akm-keep", "kept",
            {"champion_head": "a" * 40, "comparison": {**_comparison(1.5),
                "anchor_samples": list(range(20)), "decisive": True}})
    _insert(tmp_path, "null", "2026-09-01T00:00:02Z", "akm-null", "measured_null",
            {"comparison": {**_comparison(.1), "decisive": False}})
    _insert(tmp_path, "reg", "2026-09-01T00:00:03Z", "akm-reg", "measured_regression",
            {"comparison": {**_comparison(-2.0), "decisive": True}})
    _insert(tmp_path, "ref", "2026-09-01T00:00:04Z", "akm-ref", "refused_at_formation",
            {"reason": "critic refused"}, "critic refused")
    _insert(tmp_path, "bad", "2026-09-01T00:00:05Z", "akm-bad", "measurement_invalid", {})
    body = loop_status.read_knowledge(tmp_path)["body"]
    result = loop_status.improvement_trajectory(tmp_path, body["trajectory_rows"], PRODUCTION)
    events = result["experiment_events"]
    assert events["counts"] == {"kept": 1, "measured_null": 1, "regression": 1,
                                 "formation_refusal": 1, "invalid_or_setup": 1}
    keep = next(e for e in events["events"] if e["disposition"] == "kept")
    assert keep["effect_pct"] == 1.5 and keep["floor_pct"] == 1.0
    assert "anchor_samples" not in json.dumps(keep)


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_leads_with_production_curves_and_demotes_cor(tmp_path: Path) -> None:
    payload = {"knowledge": {"improvement_trajectory": {
        "schema": loop_status.TRAJECTORY_SCHEMA,
            "production_headline": {
                "state": "available", "detail": "direct only",
                "baseline": {"commit": "d" * 40, "label": "production-consolidated-v9"},
                "baseline_epochs": [{"commit": "d" * 40,
                    "label": "production-consolidated-v9", "effective_at": "2026-08-11T00:00:00Z"}],
                "evidence_errors": [{"evidence": "broken.json", "reason": "unjoined"}],
                "exceptions": [{"commit": "e" * 40, "evidence_state": "missing_production_ab",
                                "note": "current champion has no direct production A/B"}],
                "curves": [{"id": "qwen", "model": "Qwen3.8-27B-Q8_0.gguf",
                            "surface": "tg128", "primary_surface": "tg128",
                            "metric": "tg128", "backend": "gpu", "instrument_epochs": [{
                                "recipe": "gpu-direct", "era": "gpu-era",
                                "baseline": {"commit": "d" * 40, "label": "production-consolidated-v9"},
                                "starts_at": "2026-09-01T00:00:00Z", "starts_commit": "a" * 40}],
                            "points": [
                            {"commit": "a" * 40, "recorded_at": "2026-09-01T00:00:00Z",
                             "gain_pct": 5.6, "pairs": 20, "recipe": "gpu-direct",
                             "era": "gpu-era", "baseline": {"commit": "d" * 40, "label": "production-consolidated-v9"}},
                            {"commit": "b" * 40, "recorded_at": "2026-09-02T00:00:00Z",
                             "gain_pct": 7.2, "pairs": 20, "recipe": "gpu-direct",
                             "era": "gpu-era", "baseline": {"commit": "d" * 40, "label": "production-consolidated-v9"}}]}]},
        "campaign_drilldown": {"state": "available", "keeps": [{}, {}, {}],
                               "bench_checkpoints": [{"gain_pct": .83}],
                               "serving_checks": [{"keep_count": 2, "gain_pct": .33,
                                                   "evidence_state": "serving_inconclusive"}]},
        "experiment_events": {"counts": {"kept": 1, "formation_refusal": 1},
            "events": [{"recorded_at": "2026-09-01T12:00:00Z", "mechanism_id": "akm-kept",
                        "disposition": "kept", "producer_status": "kept", "effect_pct": 1.2,
                        "floor_pct": .6, "commit": "a" * 40, "epoch": "c" * 64,
                        "model": "Qwen", "surface": "tg128", "profile_target": "kernel",
                        "hypothesis": "faster", "critic_rationale": None, "comparison": {"pairs": 20},
                        "evidence": [], "transfer_applicability": None, "identifiers": {}},
                       {"recorded_at": "2026-09-01T13:00:00Z", "mechanism_id": "akm-refused",
                        "disposition": "formation_refusal", "producer_status": "refused_at_formation",
                        "effect_pct": None, "floor_pct": None, "commit": None, "epoch": "c" * 64,
                        "model": None, "surface": "tg128", "profile_target": "kernel",
                        "hypothesis": "unsafe", "critic_rationale": "critic refused", "comparison": None,
                        "evidence": [], "transfer_applicability": None, "identifiers": {}}]},
    }}}
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                        PAGE.read_text(), re.DOTALL)
    page_js, data = tmp_path / "page.js", tmp_path / "payload.json"
    page_js.write_text("\n".join(blocks))
    data.write_text(json.dumps(payload))
    proc = subprocess.run(["node", str(HARNESS), str(page_js), str(data),
                           "renderImprovementTrajectory"], capture_output=True,
                          text=True, timeout=30, check=True)
    card = json.loads(proc.stdout)["by_id"]["trajectory"]
    assert "declared baseline 0%" in card
    assert "epoch-band" in card and "epoch-boundary" in card
    assert "Qwen3.8-27B-Q8_0.gguf" in card
    assert "data-point-count=\"2\"" in card
    assert "cumulative +7.200%" in card
    assert "Campaign-local CoR drill-down" in card
    assert "not production-relative" in card
    assert "1 unjoinable production receipt" in card
    assert "missing_production_ab" in card
    assert 'tabindex="0" role="button"' in card
    assert "trajectory-event-drawer" in card
    assert "trajectory-picker" in card
    assert "trajectory-legend" not in card
    segments = [tuple(map(float, pair)) for pair in re.findall(
        r'd="M([0-9.]+),[0-9.]+ L([0-9.]+),', card)]
    assert segments and all(end > start for start, end in segments)
    assert max(end for _, end in segments) - min(start for start, _ in segments) > 500
    dispositions = re.findall(r'class="point trajectory-event"[^>]+data-disposition="([^"]+)"', card)
    assert dispositions and set(dispositions) == {"kept"}
    for forbidden in ("measured_null", "formation_refusal", "invalid_or_setup", "data-event-filter"):
        assert forbidden not in card


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_whole_page_sibling_failure_cannot_prevent_trajectory_mount(tmp_path: Path) -> None:
    payload = {"knowledge": {"improvement_trajectory": {
        "schema": loop_status.TRAJECTORY_SCHEMA,
        "production_headline": {"state": "available", "detail": "direct",
            "evidence_errors": [], "exceptions": [], "baseline_epochs": [],
            "curves": [{"id": "curve", "model": "model", "surface": "tg128",
                        "recipe": "recipe", "baseline": {"commit": "d" * 40, "label": "v9"},
                        "points": [{"commit": "a" * 40, "recorded_at": "2026-09-01T00:00:00Z",
                                    "gain_pct": 1.0, "evidence_state": "serving_verified_direct",
                                    "era": "era"}]}]},
        "campaign_drilldown": {"state": "absent"},
        "experiment_events": {"events": [], "counts": {}}}}}
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", PAGE.read_text(), re.DOTALL)
    source = "\n".join(blocks).replace(
        "renderSerial(d);", 'throw new Error("synthetic sibling renderer");', 1)
    page_js, data = tmp_path / "page.js", tmp_path / "payload.json"
    page_js.write_text(source); data.write_text(json.dumps(payload))
    proc = subprocess.run(["node", str(HARNESS), str(page_js), str(data), "render"],
                          capture_output=True, text=True, timeout=30, check=True)
    result = json.loads(proc.stdout)
    assert result["threw"] == ["render: synthetic sibling renderer"]
    assert "<svg" in result["by_id"]["trajectory"]


def test_trajectory_is_first_surface_and_absorbs_redundant_panels() -> None:
    page = PAGE.read_text()
    main = page.split("<main>", 1)[1]
    assert '<section id="sec-champion"' not in main
    assert '<section id="sec-tiles"' not in main
    assert main.index('id="sec-trajectory"') < main.index('id="sec-capabilities"')
    assert main.index('id="sec-capabilities"') < main.index('id="sec-accumulator"')
    assert main.index('id="sec-accumulator"') < main.index('id="sec-serial"')
    trajectory = main[main.index('id="sec-trajectory"'):main.index('</section>')]
    for retained_host in ('id="champ"', 'id="champ-badge"', 'id="tiles"', 'id="trajectory"'):
        assert retained_host in trajectory
    knowledge = main[main.index('id="sec-knowledge"'):]
    assert knowledge.index("<details>") < knowledge.index('id="know"')


def _history(root: Path, *, active: dict | None = None,
             points: list | None = None, epochs: list | None = None) -> None:
    (root / loop_status.HISTORICAL_TRAJECTORY_FILENAME).write_text(json.dumps({
        "schema": loop_status.HISTORICAL_TRAJECTORY_SCHEMA,
        "generated_at": "2026-09-14T00:00:00Z", "points": points or [],
        "missing_checkpoints": [], "baseline_epochs": epochs or [{
            "commit": "d" * 40, "label": "production-consolidated-v9",
            "effective_at": "2026-08-11T00:00:00Z"}],
        **({"active_campaign": active} if active else {}),
    }))


def test_new_retained_promotion_auto_appears_as_compatible_provisional(tmp_path: Path) -> None:
    _store(tmp_path)
    cor, tip1, tip2 = "c" * 40, "1" * 40, "2" * 40
    active = {"id": "campaign-era", "model": "GLM-5.3-Flash",
              "store": str(tmp_path), "champion_of_record": cor}
    _history(tmp_path, active=active)

    def publish(tip: str, keeps: list[str], gain: float) -> None:
        (tmp_path / "accumulator-bundle.json").write_text(json.dumps({
            "schema": "epyc.autokernel.accumulator_bundle.v2",
            "champion_of_record": cor[:12], "tip": tip, "keeps": keeps,
            "measurement_validity": "current_snapshot", "compounded_bench_pct": gain}))
        (tmp_path / loop_status.STATUS_FILENAME).write_text(json.dumps({
            "schema": loop_status.STATUS_SCHEMA, "generated_at": "2026-09-14T01:00:00Z",
            "champion_head": tip, "model": "/models/GLM-5.3-Flash.gguf",
            "surface": "serving:glm53-cpu-mtp-recipe"}))

    publish(tip1, ["keep-1"], .4)
    first = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    provisional = [p for c in first["production_headline"]["curves"] for p in c["points"]
                   if p["evidence_state"] == "accumulated_chained_provisional"]
    assert [(p["commit"], p["gain_pct"], p["keep_count"]) for p in provisional] == [(tip1, .4, 1)]

    publish(tip2, ["keep-1", "keep-2"], .83)
    second = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    provisional = [p for c in second["production_headline"]["curves"] for p in c["points"]
                   if p["evidence_state"] == "accumulated_chained_provisional"]
    assert [(p["commit"], p["gain_pct"], p["keep_count"]) for p in provisional] == [(tip2, .83, 2)]


def test_baseline_epochs_break_v9_v10_and_admit_model_first_seen_in_v10(tmp_path: Path) -> None:
    _store(tmp_path)
    v9, v10, sha = "d" * 40, "e" * 40, "a" * 64
    def point(commit: str, model: str, baseline: str, label: str, at: str) -> dict:
        return {"commit": commit, "recorded_at": at, "model": model, "surface": "tg128",
                "recipe": "recipe", "era": label, "gain_pct": 5.0,
                "baseline": {"commit": baseline, "label": label},
                "evidence_state": "serving_verified_direct",
                "evidence": {"path": "receipt", "sha256": sha}}
    _history(tmp_path, points=[
        point("1" * 40, "legacy-model", v9, "production-consolidated-v9", "2026-09-01T00:00:00Z"),
        point("2" * 40, "legacy-model", v10, "production-consolidated-v10", "2026-10-01T00:00:00Z"),
        point("3" * 40, "new-model", v10, "production-consolidated-v10", "2026-10-02T00:00:00Z")],
        epochs=[{"commit": v9, "label": "production-consolidated-v9", "effective_at": "2026-08-11T00:00:00Z"},
                {"commit": v10, "label": "production-consolidated-v10", "effective_at": "2026-10-01T00:00:00Z"}])
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)["production_headline"]
    assert [e["label"] for e in result["baseline_epochs"]] == ["production-consolidated-v9", "production-consolidated-v10"]
    legacy = [c for c in result["curves"] if c["model"] == "legacy-model"]
    assert len(legacy) == 1
    assert [p["baseline"]["commit"] for p in legacy[0]["points"]] == [v9, v10]
    assert len(legacy[0]["instrument_epochs"]) == 2
    new = [c for c in result["curves"] if c["model"] == "new-model"]
    assert len(new) == 1 and new[0]["points"][0]["baseline"]["label"] == "production-consolidated-v10"


def test_one_headline_trajectory_per_model_with_surface_details(tmp_path: Path) -> None:
    _store(tmp_path)
    base, sha = "d" * 40, "a" * 64
    def p(commit: str, at: str, surface: str, recipe: str, gain: float) -> dict:
        return {"commit": commit, "recorded_at": at, "model": "Qwen3.8-Flash-Next",
                "surface": surface, "recipe": recipe, "era": ("old" if commit[0] != "e" else "hot"),
                "gain_pct": gain, "baseline": {"commit": base, "label": "pristine"},
                "evidence_state": "serving_verified_direct",
                "evidence": {"path": "receipt", "sha256": sha}}
    points=[]
    for commit, at, recipe, plain, mtp in (
        ("6" * 40, "2026-09-06T22:18:06Z", "old-harness-defaults", 69.34, 48.34),
        ("9" * 40, "2026-09-07T13:01:06Z", "old-harness-shim-off", 71.51, 51.49),
        ("e" * 40, "2026-09-08T08:53:12Z", "canonical-hot-process-thp-disable", 118.57, 82.55)):
        points.extend((p(commit, at, "plain-decode", recipe, plain),
                       p(commit, at, "mtp-decode", recipe, mtp)))
    _history(tmp_path, points=points)
    headline=loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)["production_headline"]
    assert [c["id"] for c in headline["curves"]] == ["Qwen3.8-Flash-Next"]
    assert len({c["id"] for c in headline["curves"]}) == len(headline["curves"])
    model=headline["curves"][0]
    assert model["primary_surface"] == "plain-decode"
    assert {s["surface"] for s in model["surface_series"]} == {"plain-decode", "mtp-decode"}
    for surface in model["surface_series"]:
        assert [p["commit"][0] for p in surface["points"]] == ["6", "9", "e"]
        assert [p["recorded_at"] for p in surface["points"]] == [
            "2026-09-06T22:18:06Z", "2026-09-07T13:01:06Z", "2026-09-08T08:53:12Z"]

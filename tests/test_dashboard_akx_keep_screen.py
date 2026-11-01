import json
from pathlib import Path
import subprocess

from dashboard import loop_status


def _projected_state(state="fresh"):
    return {"schema": "epyc.autokernel.keep_screen_status.v1",
        "generated_at": "2026-11-01T00:00:00Z", "state": state,
        "freshness": {"state": "fresh", "age_s": 0, "stale_after_s": 300},
        "source": {"kind": "resolved_campaign", "campaign_id": "c1",
            "manifest_path": "/campaign/resolved.json", "manifest_sha256": "a" * 64},
        "workloads": [{"workload_id": "w1", "workload_signature": "1" * 64},
            {"workload_id": "w2", "workload_signature": "2" * 64},
            {"workload_id": "w3", "workload_signature": "3" * 64}],
        "keeps": [{"keep_id": "keep-1", "source_path": "/store/record.json",
            "record_sha256": "b" * 64,
            "freshness": {"state": "fresh", "age_s": 30, "stale_after_s": 300,
                          "detail": "current"},
            "rows": [
                {"workload_id": "w1", "classification": "INERT", "tier": "T0",
                 "verdict": "UNKNOWN", "refusal_remedy": None},
                {"workload_id": "w2", "classification": "INERT", "tier": "T1",
                 "verdict": "UNKNOWN", "refusal_remedy": None},
                {"workload_id": "w3", "classification": "TOUCHED", "tier": None,
                 "verdict": "REGRESSION", "refusal_remedy": {
                     "suggested_form": 1, "discriminator_hint": "<shape & backend>"}}]}]}


def test_panel_preserves_actual_keep_ids_and_fail_closes_stale_or_bad_classes():
    old = {"accumulator": {"keeps": ["actual-keep"]}}
    absent = loop_status.keep_screen_snapshot(old, now=1793500000)
    assert absent["state"] == "absent"
    assert absent["keeps"][0]["keep_id"] == "actual-keep"

    body = {"accumulator": {"keeps": ["keep-1"]}, "keep_screen": _projected_state()}
    fresh = loop_status.keep_screen_snapshot(body, now=1793491200)
    assert [row["classification"] for row in fresh["keeps"][0]["rows"]] == [
        "INERT", "INERT", "TOUCHED"]
    assert fresh["keeps"][0]["rows"][2]["refusal_remedy"]["suggested_form"] == 1

    bad = _projected_state()
    bad["keeps"][0]["rows"][2]["classification"] = "GREEN"
    bad["keeps"][0]["rows"][2]["verdict"] = "PASSED"
    invalid = loop_status.keep_screen_snapshot(
        {"accumulator": {"keeps": ["keep-1"]}, "keep_screen": bad}, now=1793491200)
    assert invalid["keeps"][0]["rows"][2]["classification"] == "UNKNOWN"
    assert "unrecognized" in invalid["keeps"][0]["rows"][2]["unknown_reason"]
    assert invalid["keeps"][0]["rows"][2]["verdict"] == "UNKNOWN"

    stale = loop_status.keep_screen_snapshot(body, now=1793492000)
    assert stale["state"] == "stale"
    assert all(row["classification"] == "UNKNOWN" for row in stale["keeps"][0]["rows"])


def test_missing_manifest_has_no_invented_workloads_but_keeps_real_ids():
    projection = {"schema": "epyc.autokernel.keep_screen_status.v1",
        "generated_at": "2026-11-01T00:00:00Z", "state": "missing_manifest",
        "freshness": {"state": "absent", "age_s": None, "stale_after_s": 300},
        "source": {"kind": "resolved_campaign", "detail": "manifest unavailable"},
        "workloads": [], "keeps": [{"keep_id": "actual-keep", "rows": [],
            "freshness": {"state": "absent", "detail": "workload set unknown"}}]}
    panel = loop_status.keep_screen_snapshot({
        "accumulator": {"keeps": ["actual-keep"]}, "keep_screen": projection},
        now=1793491200)
    assert panel["state"] == "missing_manifest"
    assert panel["workloads"] == []
    assert panel["keeps"][0]["keep_id"] == "actual-keep"
    assert panel["keeps"][0]["rows"] == []


def test_malformed_nested_rows_and_freshness_fail_closed_without_raising():
    for corrupt in ("rows", "freshness"):
        body = {"accumulator": {"keeps": ["keep-1"]},
                "keep_screen": _projected_state()}
        if corrupt == "rows":
            body["keep_screen"]["keeps"][0]["rows"] = 7
        else:
            body["keep_screen"]["keeps"][0]["freshness"] = []
        panel = loop_status.keep_screen_snapshot(body, now=1793491200)
        assert panel["state"] == "malformed"
        assert all(row["classification"] == "UNKNOWN"
                   for keep in panel["keeps"] for row in keep["rows"])


def test_invalid_inert_tier_and_stale_verdict_are_not_projected_as_current():
    for tier in (None, "T2"):
        body = {"accumulator": {"keeps": ["keep-1"]},
                "keep_screen": _projected_state()}
        body["keep_screen"]["keeps"][0]["rows"][0]["tier"] = tier
        panel = loop_status.keep_screen_snapshot(body, now=1793491200)
        invalid = panel["keeps"][0]["rows"][0]
        assert invalid["classification"] == "UNKNOWN"
        assert invalid["verdict"] == "UNKNOWN"

    unsupported = {"accumulator": {"keeps": ["keep-1"]},
                   "keep_screen": _projected_state()}
    unsupported["keep_screen"]["keeps"][0]["rows"][2]["verdict"] = "PASSED"
    panel = loop_status.keep_screen_snapshot(unsupported, now=1793491200)
    assert panel["keeps"][0]["rows"][2]["classification"] == "TOUCHED"
    assert panel["keeps"][0]["rows"][2]["verdict"] == "UNKNOWN"

    body = {"accumulator": {"keeps": ["keep-1"]},
            "keep_screen": _projected_state()}

    stale = loop_status.keep_screen_snapshot(body, now=1793492000)
    stale_row = stale["keeps"][0]["rows"][2]
    assert stale_row["classification"] == "UNKNOWN"
    assert stale_row["verdict"] == "UNKNOWN"
    assert stale_row["refusal_remedy"] is None


def test_future_generated_at_uses_panel_skew_tolerance():
    body = {"accumulator": {"keeps": ["keep-1"]},
            "keep_screen": _projected_state()}
    body["keep_screen"]["generated_at"] = "2026-11-01T00:06:41Z"
    malformed = loop_status.keep_screen_snapshot(body, now=1793491200)
    assert malformed["state"] == "malformed"
    assert all(row["classification"] == "UNKNOWN"
               for keep in malformed["keeps"] for row in keep["rows"])

    body["keep_screen"]["generated_at"] = "2026-11-01T00:04:59Z"
    tolerated = loop_status.keep_screen_snapshot(body, now=1793491200)
    assert tolerated["state"] == "fresh"
    assert tolerated["age_s"] == 0


def test_browser_renderer_shows_matrix_verdict_remedy_and_escapes_untrusted_hint():
    html = (Path(__file__).parents[1] / "dashboard/static/loop.html").read_text()
    start = html.index("function renderKeepScreen(d){")
    end = html.index("\nfunction renderKnowledge", start)
    renderer = html[start:end] + "\nglobalThis.renderKeepScreen = renderKeepScreen;"
    test_js = r"""
const vm=require('vm');
let output='';
const host={set innerHTML(v){output=v;},get innerHTML(){return output;}};
const document={getElementById:()=>host};
const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const age=v=>String(v)+'s';
const context={document,esc,age};
vm.createContext(context);
vm.runInContext(JSON.parse(process.argv[1]),context);
context.renderKeepScreen(JSON.parse(require('fs').readFileSync(0,'utf8')));
process.stdout.write(host.innerHTML);
"""
    test_js = test_js.replace("JSON.parse(process.argv[1])", json.dumps(renderer))
    panel = loop_status.keep_screen_snapshot(
        {"accumulator": {"keeps": ["keep-1"]}, "keep_screen": _projected_state()},
        now=1793491200)
    rendered = subprocess.run(["node", "-e", test_js], input=json.dumps({"keep_screen": panel}),
        text=True, capture_output=True, check=True).stdout
    assert "INERT (T0)" in rendered and "INERT (T1)" in rendered and "TOUCHED" in rendered
    assert "REGRESSION" in rendered and "form 1" in rendered
    assert "&lt;shape &amp; backend&gt;" in rendered

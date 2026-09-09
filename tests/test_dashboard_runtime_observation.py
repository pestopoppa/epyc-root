"""Independent consumer/browser checks for the real runtime projection."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from dashboard import campaign_status as C
from dashboard import loop_status, panels
from tests.test_dashboard_campaign_status import active_worker_v2, body_v3, stamp


def runtime_body(*, age=0, missing=False, active=False, remaining=7200, **changes):
    body = body_v3()
    body["unified"].update(schema=C.UNIFIED_PROJECTION_SCHEMA_V2, worker_timing=None,
        runtime={"status": "not_reported" if missing else "waiting",
          "reason": "owner has not reported" if missing else "discovery_unit:executor_unavailable",
          "reason_truncated": False, "observed_at": None if missing else stamp(age),
          "observation_sequence": 0 if missing else 1, "retry_after_seconds": 0,
          "work_kind": None, "target_revision": None, "transition_id": None,
          "settlement_outcome": None, "installed_work_kinds": ["runtime_comparison"],
          "publication_error": None})
    # Always issue generated_at after observation; exact independent clocks.
    body["generated_at"] = body["producer_heartbeat_at"] = stamp()
    body["unified"]["runtime"].update(changes)
    if active:
        worker = active_worker_v2(started_at=stamp(age), activity_at=stamp(age))
        body.update(active_worker=worker, worker_activity_at=worker["activity_at"],
                    worker_lifecycle_revision=1, observed_state="running", desired_state="running",
                    prerequisite_reason=None, control_revision=1)
        body["unified"]["worker_timing"] = {
            "worker_id": worker["worker_id"], "worker_generation": worker["worker_generation"],
            "lifecycle_revision": 1, "checked_at": body["generated_at"],
            "state": "clock_unavailable" if remaining is None else
                     "within_deadline" if remaining > 0 else "deadline_elapsed",
            "remaining_seconds": remaining}
    return C.validate_snapshot(body)


def hub_snapshot(monkeypatch, body):
    monkeypatch.setattr(C, "read", lambda: {"configured": True, "snapshot": body,
        "content_digest": "a" * 64, "gateway_url": "http://fixture", "hub_origin": "http://hub"})
    monkeypatch.setattr(C, "observe_health", lambda *_a, **_k: {
        "state": "live", "matched": True, "reason": "transport remains healthy",
        "identity": {"allowed_origin": "http://hub"}})
    return C.snapshot(now=time.time())


@pytest.mark.parametrize("age,missing,expected", [(0, True, "unknown"), (3600, False, "stale"),
                                                  (0, False, "current")])
def test_fresh_publisher_does_not_refresh_runtime_observation(monkeypatch, age, missing, expected):
    body = runtime_body(age=age, missing=missing)
    view = hub_snapshot(monkeypatch, body)
    assert view["health"]["state"] == "live" and view["controls"]["available"]
    assert view["runtime_freshness"]["state"] == expected
    assert view["clocks"]["producer_heartbeat_at"]["age_s"] < 1
    assert view["state"] == "degraded"  # disconnected scientific surfaces stay honest too
    observation = loop_status.campaign_observation(view, panels.absent("fixture", "fixture absent"))
    assert observation.timestamp is None
    assert observation.detail == view["runtime_freshness"]["reason"]


@pytest.mark.parametrize("remaining,expected", [(7200, "in_progress"), (0, "stale"), (None, "unknown")])
def test_long_owned_stage_vs_stalled_stage_uses_original_relative_bound(monkeypatch, remaining, expected):
    body = runtime_body(age=3600, active=True, remaining=remaining)
    # A foreign monotonic absolute deadline is deliberately unrelated to epoch time.
    body["active_worker"]["provider_deadline"] = 0.123
    body["active_worker"]["deadline_clock_domain"] = "foreign-epoch:opaque"
    view = hub_snapshot(monkeypatch, C.validate_snapshot(body))
    assert view["runtime_freshness"]["state"] == expected
    assert view["runtime_freshness"]["activity_silent"]
    assert view["runtime_freshness"]["activity_age_s"] >= 3600
    assert view["controls"]["available"]  # observation has no command authority
    if expected != "in_progress":
        assert view["state"] == "degraded"


def test_relative_deadline_ages_without_refresh_and_future_wall_time_stays_unknown():
    body = runtime_body(active=True, remaining=2)
    assert C.runtime_freshness(body, now=time.time() + 3)["state"] == "stale"
    body["generated_at"] = body["producer_heartbeat_at"] = stamp(-3600)
    body["unified"]["worker_timing"]["checked_at"] = body["generated_at"]
    assert C.runtime_freshness(C.validate_snapshot(body), now=time.time())["state"] == "unknown"


def test_first_publication_error_is_explicit_and_undated(monkeypatch):
    body = runtime_body(missing=True, observation_sequence=1, publication_error="OSError: fixture")
    view = hub_snapshot(monkeypatch, body)
    assert view["runtime_freshness"]["state"] == "unknown"
    assert "publication failed" in view["runtime_freshness"]["reason"]
    assert view["campaign"]["unified"]["runtime"]["observed_at"] is None


@pytest.mark.parametrize("mutation", [
    lambda b: b["unified"]["runtime"].update(untrusted_field=True),
    lambda b: b["unified"]["runtime"].update(publication_error="x" * 4097),
    lambda b: b["unified"]["runtime"].update(observed_at=stamp(-3600)),
    lambda b: b["unified"]["runtime"].update(work_kind="calibration_preparation"),
    lambda b: b["unified"].update(schema=C.UNIFIED_PROJECTION_SCHEMA),
    lambda b: b["unified"]["worker_timing"].update(worker_id="foreign"),
    lambda b: b["unified"]["worker_timing"].update(remaining_seconds=True),
])
def test_closed_runtime_and_original_worker_identity_refuse_malformed(mutation):
    body = runtime_body(active=True)
    mutation(body)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body)


def test_observation_ordering_and_incarnation_reset_are_independent_of_heartbeat():
    old = runtime_body(age=30)
    newer = copy.deepcopy(old)
    newer.update(sequence=old["sequence"] + 1, generated_at=stamp(), producer_heartbeat_at=stamp())
    assert C.advance_snapshot(old, newer)["status"] == "accepted"
    for changes in ({"observation_sequence": 0}, {"reason": "different same sequence"},
                    {"observation_sequence": 2, "observed_at": stamp(60)}):
        bad = copy.deepcopy(newer)
        bad["unified"]["runtime"].update(changes)
        with pytest.raises(C.CampaignStatusError):
            C.advance_snapshot(old, bad)
    downgrade = copy.deepcopy(newer)
    downgrade["unified"].pop("runtime")
    downgrade["unified"].pop("worker_timing")
    downgrade["unified"]["schema"] = C.UNIFIED_PROJECTION_SCHEMA
    with pytest.raises(C.CampaignStatusError, match="downgrade runtime"):
        C.advance_snapshot(old, downgrade)
    reset = runtime_body(missing=True)
    reset.update(stream_epoch=old["stream_epoch"] + 1,
                 supervisor_incarnation=old["supervisor_incarnation"] + 1)
    assert C.advance_snapshot(old, reset)["status"] == "accepted"


@pytest.fixture
def actual_runtime_snapshot(tmp_path, monkeypatch):
    configured = os.environ.get("EPYC_INFERENCE_RESEARCH_ROOT")
    research = Path(configured or "/workspace/repos/epyc-inference-research") / "scripts/kernel_rnd"
    helper = research / "autokernel/loop/test_runtime_observation.py"
    if not configured and not helper.is_file():
        pytest.skip("matching optional runtime-aware research checkout is unavailable")
    assert helper.is_file(), "explicit research checkout lacks the matching runtime producer fixture"
    monkeypatch.syspath_prepend(str(research))
    from autokernel.loop.test_runtime_observation import discovery_runtime
    runtime, controller, _declared = discovery_runtime(tmp_path, monkeypatch)
    try:
        runtime.recover()
        result = runtime.tick()
        assert result.status == "waiting" and "discovery_unit:executor_unavailable" in result.reason
        yield controller.publish_snapshot()
    finally:
        runtime.close()
        controller.close()


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_actual_runtime_wait_crosses_both_validators_and_browser_render(actual_runtime_snapshot, tmp_path):
    real = C.validate_snapshot(actual_runtime_snapshot)
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page.read_text(), re.DOTALL))
    source = source.replace("tick();\nsetInterval(tick, 20000);", "")
    runner = r'''
const fs=require('fs');const el=()=>({style:{},classList:{add(){},remove(){},toggle(){}},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el()},querySelectorAll(){return[]}});
const nodes={};const get=id=>nodes[id]||(nodes[id]=el());
global.document={getElementById:get,querySelector:el,querySelectorAll:()=>[],createElement:el,
 createElementNS:el,addEventListener(){},body:el()};
global.window={isSecureContext:true,addEventListener(){},location:{href:''}};
global.setInterval=()=>0;global.setTimeout=()=>0;
const f=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
'''+source+r'''
campaignValidateSnapshot(f.body);campaignAcceptSnapshot(f.body);
const clone=x=>JSON.parse(JSON.stringify(x));const errors=[];
const view={configured:true,state:'degraded',campaign:f.body,clocks:{},controls:{available:false},
 runtime_freshness:{...f.clock,reason:'ACCEPTED_FRESHNESS'}};
renderCampaign({campaign:view});
const bad=clone(f.body);bad.sequence++;bad.unified.runtime.unknown_field=true;
renderCampaign({campaign:{...view,campaign:bad,runtime_freshness:{...f.clock,state:'in_progress',
 reason:'REJECTED_FRESHNESS'}}});
const retainedHTML=nodes.campaign.innerHTML,retainedBadge=nodes['campaign-badgetxt'].textContent;
for(const mutate of [b=>{b.unified.runtime.publication_error='x'.repeat(4097)},
 b=>{b.unified.runtime.reason='changed same sequence'},
 b=>{delete b.unified.runtime;delete b.unified.worker_timing;b.unified.schema='epyc.autokernel.unified_campaign_projection.v1'}]){
 const b=clone(f.body);b.sequence++;mutate(b);try{campaignAcceptSnapshot(b)}catch(e){errors.push(e.message)}
}
const html=campaignRenderUnified(f.body,f.clock);
const reset=clone(f.body);reset.sequence=1;reset.stream_epoch++;reset.supervisor_incarnation++;
reset.unified.runtime={...reset.unified.runtime,status:'not_reported',observed_at:null,observation_sequence:0,retry_after_seconds:0};
campaignAcceptSnapshot(reset);
const failed=clone(reset);failed.sequence++;failed.unified.runtime.observation_sequence++;
failed.unified.runtime.publication_error='first publication failed';campaignAcceptSnapshot(failed);
const unicode=clone(failed);unicode.sequence++;unicode.unified.runtime.observation_sequence++;
unicode.unified.runtime.reason='🚀'.repeat(4096);campaignAcceptSnapshot(unicode);
console.log(JSON.stringify({html,errors,retainedHTML,retainedBadge,undated:failed.unified.runtime.observed_at}));
'''
    fixture = tmp_path / "runtime.json"
    fixture.write_text(json.dumps({"body": real, "clock": C.runtime_freshness(real, now=time.time())}))
    result = json.loads(subprocess.run(["node", "-e", runner, str(fixture)],
        check=True, capture_output=True, text=True, timeout=10).stdout)
    assert len(result["errors"]) == 3 and result["undated"] is None
    assert "ACCEPTED_FRESHNESS" in result["retainedHTML"]
    assert "REJECTED_FRESHNESS" not in result["retainedHTML"]
    assert result["retainedBadge"] == "UNKNOWN / HISTORY"
    assert "discovery_unit:executor_unavailable" in result["html"]
    assert "not publisher heartbeat" in result["html"]
    assert "none inferred; calibration collection is not qualification" in result["html"]
    assert "runtime_comparison" in result["html"]

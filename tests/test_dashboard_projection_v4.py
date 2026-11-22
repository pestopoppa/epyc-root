"""AKU-09g2: hub consumer for unified_campaign_projection.v4 (resource/candidate sections)."""
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
from tests.test_dashboard_campaign_status import stamp
from tests.test_dashboard_runtime_aggregates import aggregate_body
from tests.test_dashboard_runtime_observation import hub_snapshot


def v4_body(*, connected=True, candidate=True):
    """Fixture shape of the research producer's v4 sections; not producer output."""
    body = aggregate_body()
    accounting = body["unified"]["scheduler"]["accounting"]
    body["unified"].update(schema=C.UNIFIED_PROJECTION_SCHEMA_V4, resources={
        "schema": "epyc.autokernel.unified_resource_status.v2",
        "status": "available" if connected else "not_connected",
        "reason": "fixture: recorded grant is not a live grant",
        "requested": {"worker_id": "worker-2", "worker_generation": 2, "request_digest": "a" * 64,
                      "occurred_at": stamp(5), "authorization_remaining_seconds": 40.0,
                      "clock_known": True} if connected else None,
        "granted": {"worker_id": "worker-1", "worker_generation": 1, "grant_id": "grant-7",
                    "grant_generation": 3, "recorded_at": stamp(10)} if connected else None,
        "held": {"lifecycle_event_count": 4, "active_worker_count": 1, "held_receipt_count": 0}
        if connected else None,
        "used": {"receipt_count": accounting["receipt_count"], "held_seconds": 1.5,
                 "physical_region_seconds": 2.0, "memory_byte_seconds": 0.0,
                 "gpu_device_seconds": {"gpu0": 1.0}, "gpu_devices_total": 3,
                 "view_digest": accounting["view_digest"]}},
        candidate={"schema": "epyc.autokernel.unified_candidate_status.v2",
                   "status": "available" if candidate else "not_connected",
                   "reason": "fixture: validated pointer is not validation authority",
                   "accumulated_identity": "b" * 64 if candidate else None,
                   "validated_identity": "c" * 64 if candidate else None,
                   "frozen_production_identity": "d" * 64 if candidate else None,
                   "validation_debt": {"count": 41, "items": [f"batch-{i:03d}" for i in range(16)],
                                       "truncated": True} if candidate else None,
                   "gate_due": True if candidate else None, "pending_phase": "PREPARED" if candidate else None,
                   "projection_lag_events": 2 if candidate else 0, "replay_verified": False})
    return C.validate_snapshot(body)


def v4_mutations():
    r = lambda b: b["unified"]["resources"]  # noqa: E731
    c = lambda b: b["unified"]["candidate"]  # noqa: E731
    return [
        lambda b: r(b).update(extra=None), lambda b: r(b).pop("held"),
        lambda b: r(b).update(schema="epyc.autokernel.unified_resource_status.v1"),
        lambda b: r(b).update(status="unknown"),
        lambda b: r(b).update(status="not_connected"),  # absent owner cannot report grants
        lambda b: r(b).update(held=None), lambda b: r(b).update(used=None),
        lambda b: r(b)["granted"].update(live=True),
        lambda b: r(b)["granted"].update(recorded_at=stamp(-3600)),
        lambda b: r(b)["requested"].update(occurred_at=None),
        lambda b: r(b)["requested"].update(clock_known=False),  # remainder without its clock
        lambda b: r(b)["requested"].update(authorization_remaining_seconds=None),
        lambda b: r(b)["requested"].update(worker_generation=True),
        lambda b: r(b)["used"].update(receipt_count=7),
        lambda b: r(b)["used"].update(view_digest="e" * 64),
        lambda b: r(b)["used"].update(gpu_devices_total=0),
        lambda b: r(b)["used"].update(gpu_device_seconds={f"g{i}": 1.0 for i in range(9)}),
        lambda b: c(b).update(extra=None), lambda b: c(b).pop("gate_due"),
        lambda b: c(b).update(schema="epyc.autokernel.unified_candidate_status.v1"),
        lambda b: c(b).update(status="unknown"),
        lambda b: c(b).update(frozen_production_identity=None),
        lambda b: c(b).update(accumulated_identity="not-a-digest"),
        lambda b: c(b).update(pending_phase="COMMITTED"),
        lambda b: c(b).update(gate_due=1), lambda b: c(b).update(replay_verified=None),
        lambda b: c(b)["validation_debt"].update(truncated=False),
        lambda b: c(b)["validation_debt"].update(count=3),
        lambda b: c(b)["validation_debt"].update(items=[f"b{i}" for i in range(17)], count=17),
        lambda b: c(b)["validation_debt"].update(items=["x" * 129] + ["y"] * 15),
        lambda b: c(b)["validation_debt"].update(items=["\U0001f680" * 128] * 16),  # 8 KiB bound
        lambda b: b["unified"].update(worker_timing="x"),
        lambda b: b["unified"]["evidence"].update(status="bogus"),  # v3 part still checked
    ]


def test_v4_validates_and_v3_and_unknown_versions_are_unchanged():
    body = v4_body()
    assert body["unified"]["schema"] == C.UNIFIED_PROJECTION_SCHEMA_V4
    assert body["execution_authorized"] is False
    legacy = aggregate_body()
    assert legacy["unified"]["schema"] == C.UNIFIED_PROJECTION_SCHEMA_V3  # v3 path unchanged
    absent = v4_body(connected=False, candidate=False)
    assert absent["unified"]["resources"]["used"]["receipt_count"] == 0
    unknown = copy.deepcopy(body)
    unknown["unified"]["schema"] = "epyc.autokernel.unified_campaign_projection.v5"
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(unknown)


@pytest.mark.parametrize("mutation", v4_mutations())
def test_v4_closed_parser_refuses_malformed_sections(mutation):
    body = v4_body()
    mutation(body)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body)


def test_v4_downgrade_and_rollback_refused_restart_resets(monkeypatch):
    old = v4_body()
    newer = copy.deepcopy(old)
    newer.update(sequence=old["sequence"] + 1, generated_at=stamp(), producer_heartbeat_at=stamp())
    assert C.advance_snapshot(old, newer)["status"] == "accepted"
    v3 = copy.deepcopy(newer)
    v3["unified"].update(schema=C.UNIFIED_PROJECTION_SCHEMA_V3, **C._V4_LEGACY_CARRIERS)
    with pytest.raises(C.CampaignStatusError, match="downgrade aggregate"):
        C.advance_snapshot(old, v3)
    v3["sequence"] -= 1
    upgraded = copy.deepcopy(newer)
    assert C.advance_snapshot(C.validate_snapshot(v3), upgraded)["status"] == "accepted"  # v3 -> v4
    rolled = copy.deepcopy(newer)
    rolled["unified"]["resources"]["held"]["lifecycle_event_count"] = 1
    with pytest.raises(C.CampaignStatusError, match="rolled back"):
        C.advance_snapshot(old, rolled)
    rolled.update(stream_epoch=old["stream_epoch"] + 1, supervisor_incarnation=old["supervisor_incarnation"] + 1)
    assert C.advance_snapshot(old, rolled)["status"] == "accepted"
    view = hub_snapshot(monkeypatch, newer)
    assert set(view["aggregate_freshness"]) == {"evidence", "actor", "profile", "calibration"}
    assert view["campaign"]["unified"]["candidate"]["validation_debt"]["count"] == 41


@pytest.fixture
def actual_v4_snapshot(tmp_path, monkeypatch):
    configured = os.environ.get("EPYC_INFERENCE_RESEARCH_ROOT")
    research = Path(configured or "/workspace/repos/epyc-inference-research") / "scripts/kernel_rnd"
    if not (research / "autokernel/loop/test_standalone_runtime.py").is_file():
        pytest.skip("optional research checkout is unavailable")
    monkeypatch.syspath_prepend(str(research))
    from autokernel.loop import campaign_control
    if not hasattr(campaign_control.CampaignController, "connect_aggregate_projection"):
        pytest.skip("research producer predates projection v4 (AKU-09g)")
    from autokernel.loop.test_standalone_runtime import _runtime
    runtime, controller, _lifecycle, _engine = _runtime(tmp_path, monkeypatch)
    try:
        controller.connect_aggregate_projection(runtime)
        assert runtime.recover().status == "recovered" and runtime.tick().status == "settled"
        yield controller.publish_snapshot()
    finally:
        runtime.close()
        controller.close()


def test_actual_research_v4_producer_bytes_validate(actual_v4_snapshot):
    row = C.validate_snapshot(json.loads(json.dumps(actual_v4_snapshot)))
    assert row["unified"]["schema"] == C.UNIFIED_PROJECTION_SCHEMA_V4
    assert row["unified"]["resources"]["used"]["receipt_count"] == 1
    assert row["unified"]["candidate"]["status"] == "not_connected"


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_actual_page_validates_v4_renders_sections_and_keeps_v3(tmp_path):
    body, legacy = v4_body(), aggregate_body()
    malformed = []
    for mutate in v4_mutations():
        row = copy.deepcopy(body)
        mutate(row)
        malformed.append(row)
    unknown = copy.deepcopy(body)
    unknown["unified"]["schema"] = "epyc.autokernel.unified_campaign_projection.v5"
    malformed.append(unknown)
    fixture = tmp_path / "v4.json"
    fixture.write_text(json.dumps({"body": body, "legacy": legacy, "bad": malformed,
        "clocks": C.aggregate_freshness(body, now=time.time())}))
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page.read_text(), re.DOTALL))
    source = source.replace("tick();\nsetInterval(tick, 20000);", "")
    runner = r'''
const fs=require('fs');const el=()=>({style:{},classList:{add(){},remove(){},toggle(){}},addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el()},querySelectorAll(){return[]}});
const nodes={};global.document={getElementById:id=>nodes[id]||(nodes[id]=el()),querySelector:el,querySelectorAll:()=>[],createElement:el,createElementNS:el,addEventListener(){},body:el()};
global.window={isSecureContext:true,addEventListener(){},location:{href:''}};global.setInterval=()=>0;global.setTimeout=()=>0;
const f=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
''' + source + r'''
campaignValidateSnapshot(f.body);campaignValidateSnapshot(f.legacy);const errors=[];
for(const b of f.bad){try{campaignValidateSnapshot(b)}catch(e){errors.push(e.message)}}
const view=b=>({campaign:{configured:true,state:'degraded',campaign:b,clocks:{},controls:{available:false},aggregate_freshness:f.clocks}});
renderCampaign(view(f.body));const html=nodes.campaign.innerHTML;
campaignAccepted=null;campaignAcceptedEnvelope=null;  // fresh page: v3 alone
renderCampaign(view(f.legacy));const legacy=nodes.campaign.innerHTML;
campaignAccepted=f.body;const down=JSON.parse(JSON.stringify(f.legacy));down.sequence=f.body.sequence+1;
let downgrade=null;try{campaignAcceptSnapshot(down)}catch(e){downgrade=e.message}
console.log(JSON.stringify({errors,html,legacy,downgrade}));
'''
    result = json.loads(subprocess.run(["node", "-e", "eval(require('fs').readFileSync(0,'utf8'))", str(fixture)],
        input=runner, check=True, capture_output=True, text=True, timeout=10).stdout)
    assert len(result["errors"]) == len(malformed)
    html = result["html"]
    for phrase in ("granted (recorded, not live)", "grant-7 gen 3", "not a live grant",
                   "requested (pending acquisition intent)", "40 s", "4 / 1 / 0",
                   "(1 shown of 3)", "accumulated tip", "b" * 64,
                   "validated pointer (not validation authority)", "frozen production ref", "d" * 64,
                   "41: batch-000", "(16 shown)", "gate due</dt><dd>true", "PREPARED",
                   "replayer lag (events) / replay verified</dt><dd>2 / false",
                   "cached findings (not total corpus)"):
        assert phrase in html, phrase
    assert "execution authorized" not in html.lower()
    assert "requested / granted / held / used" in result["legacy"]  # v3 rendering unchanged
    assert "granted (recorded, not live)" not in result["legacy"]
    assert result["downgrade"] == "same campaign cannot downgrade aggregate projection"

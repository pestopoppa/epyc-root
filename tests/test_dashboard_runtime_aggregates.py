"""Independent bounded aggregate parser, clocks and actual browser consumer."""
from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from dashboard import campaign_status as C
from tests.test_dashboard_campaign_status import stamp
from tests.test_dashboard_runtime_observation import hub_snapshot, runtime_body


def aggregate_body(age=0):
    body = runtime_body()
    when = stamp(age)
    def row(kind, data):
        return {"schema": f"epyc.autokernel.{kind}_observation.v1", "status": "available",
            "reason": "original owner diagnostic fixture", "observed_at": when, "attempted_at": when,
            "generation": 1, "error": None, "data": data}
    item = {"target_revision": "a" * 64, "profile_digest": "b" * 64, "transition_id": "c" * 64,
        "available_at_planning": True, "settled": True, "remaining_seconds": 7200,
        "clock_known": True, "consumed_request_debt": False}
    budgets = {key: 0 for key in C._AGGREGATE_BUDGETS}
    body["unified"].update(schema=C.UNIFIED_PROJECTION_SCHEMA_V3,
        evidence=row("evidence", {"reader_id": "installed", "epoch": "epoch-1", "owner_state": "ready",
            "ready": True, "readiness": "projected", "source_frontier": 10, "cursor_frontier": 10,
            "projection_frontier": 10, "admission_frontier": 10, "last_admitted_frontier": 10,
            "projection_checksum": "d" * 64, "proof_pending": False, "lag_events": 0,
            "lag_seconds": None, "quarantine_count": 3, "cached_finding_count": 2}),
        actors={"schema": "epyc.autokernel.unified_actor_status.v2", "status": "available",
            "reason": "original settled indexes, not authority",
            "profile": row("profile", {"configured_count": 0, "usable_count": 1, "mechanism_count": 1,
                "debt_count": 0, "planning_observed_at": when, "items": [item], "items_total": 1, "items_truncated": False}),
            "calibration": row("calibration", {"request_count": 4, "pending_count": 1, "collected_count": 1,
                "exhausted_count": 0, "failed_count": 0, "contaminated_count": 1,
                "qualification": "unavailable", "ranking_authorized": False,
                "items": [{"request_digest": "e" * 64, "chunk_digest": "f" * 64, "outcome": "invalid"}],
                "items_total": 4, "items_truncated": True}),
            "actor": row("actor", {"pending_count": 1, "finished_count": 0, "backend_count": 1,
                "event_count": 1, "executor_installed": False, "reserved": budgets, "spent": dict(budgets),
                "items": [{"request_digest": "a" * 64, "target_revision": "b" * 64,
                    "transition_id": "c" * 64, "phase": "pending", "settlement_outcome": None,
                    "retry_remaining_seconds": None, "clock_known": False}], "items_total": 1, "items_truncated": False})})
    body["generated_at"] = body["producer_heartbeat_at"] = stamp()
    return C.validate_snapshot(body)


@pytest.mark.parametrize("age,expected", [(0, "current"), (3600, "historical")])
def test_attempt_and_publisher_do_not_refresh_old_source(monkeypatch, age, expected):
    body = aggregate_body(age)
    body["unified"]["evidence"]["attempted_at"] = stamp()
    body["generated_at"] = body["producer_heartbeat_at"] = stamp()
    view = hub_snapshot(monkeypatch, C.validate_snapshot(body))
    assert view["aggregate_freshness"]["evidence"]["state"] == expected
    assert view["aggregate_freshness"]["evidence"]["attempt_age_s"] < 1
    assert view["controls"]["available"] and view["health"]["state"] == "live"
    assert view["campaign"]["unified"]["evidence"]["data"]["cached_finding_count"] == 2


@pytest.mark.parametrize("clock_known,remaining,expected_expired,expected_unknown", [
    (True, 0, 1, 0), (False, None, 0, 1), (True, 7200, 0, 0)])
def test_profile_expiry_uses_original_relative_remainder_not_new_heartbeat(clock_known, remaining, expected_expired, expected_unknown):
    body = aggregate_body()
    item = body["unified"]["actors"]["profile"]["data"]["items"][0]
    item.update(clock_known=clock_known, remaining_seconds=remaining)
    clocks = C.aggregate_freshness(C.validate_snapshot(body), now=time.time())
    assert clocks["profile"]["expired_sample_count"] == expected_expired
    assert clocks["profile"]["unknown_validity_sample_count"] == expected_unknown
    assert clocks["profile"]["state"] == ("unknown" if expected_expired or expected_unknown else "current")
    assert body["unified"]["actors"]["profile"]["data"]["usable_count"] == 1  # historical planning total


def test_first_failure_and_retained_error_cannot_be_available(monkeypatch):
    body = aggregate_body()
    row = body["unified"]["evidence"]
    row.update(status="unknown", error="attempt failed", attempted_at=stamp())
    body["generated_at"] = body["producer_heartbeat_at"] = stamp()
    assert hub_snapshot(monkeypatch, C.validate_snapshot(body))["aggregate_freshness"]["evidence"]["state"] == "unknown"
    row.update(data=None, observed_at=None, generation=0)
    assert C.validate_snapshot(body)
    row["status"] = "available"
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body)


def mutations():
    return [
        lambda b: b.update(generated_at=[]), lambda b: b.update(generated_at=None),
        lambda b: b.update(generated_at="not-a-date"), lambda b: b.update(active_worker=[]),
        lambda b: b["unified"].update(evidence=[]),
        lambda b: b["unified"]["evidence"].update(data=[]),
        lambda b: b["unified"]["evidence"].update(observed_at=stamp(-3600)),
        lambda b: b["unified"]["evidence"].update(reason="x" * 513),
        lambda b: b["unified"]["evidence"]["data"].update(source_frontier=True),
        lambda b: b["unified"]["evidence"]["data"].update(lag_seconds=0),
        lambda b: b["unified"]["actors"]["profile"]["data"]["items"][0].update(clock_known=False),
        lambda b: b["unified"]["actors"]["calibration"]["data"].update(ranking_authorized=True),
        lambda b: b["unified"]["actors"]["actor"]["data"]["items"][0].update(phase="settled"),
        lambda b: b["unified"]["actors"]["actor"]["data"].update(items=[{}] * 17),
        lambda b: b["unified"]["actors"]["profile"]["data"].update(items_total=0),
    ]


@pytest.mark.parametrize("mutation", mutations())
def test_closed_additive_parser_refuses_malformed_diagnostics(mutation):
    body = aggregate_body()
    mutation(body)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body)


def test_aggregate_downgrade_rollback_and_restart_reset():
    old = aggregate_body(30)
    newer = copy.deepcopy(old)
    newer.update(sequence=old["sequence"] + 1, generated_at=stamp(), producer_heartbeat_at=stamp())
    assert C.advance_snapshot(old, newer)["status"] == "accepted"
    bad = copy.deepcopy(newer)
    bad["unified"]["evidence"]["generation"] = 0
    with pytest.raises(C.CampaignStatusError, match="generation rolled back"):
        C.advance_snapshot(old, bad)
    legacy = runtime_body()
    legacy["sequence"] = newer["sequence"]
    with pytest.raises(C.CampaignStatusError, match="downgrade aggregate"):
        C.advance_snapshot(old, legacy)
    reset = copy.deepcopy(bad)
    reset.update(stream_epoch=old["stream_epoch"] + 1, supervisor_incarnation=old["supervisor_incarnation"] + 1)
    assert C.advance_snapshot(old, reset)["status"] == "accepted"


def test_combined_64_row_and_32kib_utf8_bound():
    body = aggregate_body()
    for kind, count in (("actor", 16), ("profile", 24), ("calibration", 24)):
        data = body["unified"]["actors"][kind]["data"]
        data.update(items=[copy.deepcopy(data["items"][0]) for _ in range(count)],
                    items_total=count, items_truncated=False)
    assert C.validate_snapshot(body)
    for row in C._aggregate_rows(body["unified"]).values():
        row.update(status="unknown", reason="🚀" * 512, error="🚀" * 512)
    body["unified"]["actors"]["status"] = "unknown"
    with pytest.raises(C.CampaignStatusError, match="combined aggregate bound"):
        C.validate_snapshot(body)


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_actual_page_validates_bounds_retains_accepted_envelope_and_renders_debt(tmp_path):
    body = aggregate_body()
    malformed = []
    for mutate in mutations():
        row = copy.deepcopy(body)
        mutate(row)
        malformed.append(row)
    fixture = tmp_path / "aggregate.json"
    fixture.write_text(json.dumps({"body": body, "bad": malformed,
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
campaignValidateSnapshot(f.body);const errors=[];
for(const b of f.bad){try{campaignValidateSnapshot(b)}catch(e){errors.push(e.message)}}
const clocks=JSON.parse(JSON.stringify(f.clocks));clocks.evidence.reason='ACCEPTED_AGGREGATE_CLOCK';
const view={configured:true,state:'degraded',campaign:f.body,clocks:{},controls:{available:false},aggregate_freshness:clocks};
renderCampaign({campaign:view});const bad=JSON.parse(JSON.stringify(f.body));bad.sequence++;bad.unified.evidence.unknown=true;
renderCampaign({campaign:{...view,campaign:bad,aggregate_freshness:{...clocks,evidence:{state:'current',reason:'REJECTED_AGGREGATE_CLOCK'}}}});
console.log(JSON.stringify({errors,html:nodes.campaign.innerHTML}));
'''
    result = json.loads(subprocess.run(["node", "-e", "eval(require('fs').readFileSync(0,'utf8'))", str(fixture)],
        input=runner, check=True, capture_output=True, text=True, timeout=10).stdout)
    assert len(result["errors"]) == len(malformed)
    for phrase in ("ACCEPTED_AGGREGATE_CLOCK", "cached findings (not total corpus)", "FINISH is not settlement",
                   "numeric collection is not qualification", "current usable total", "contaminated attempts"):
        assert phrase in result["html"]
    assert "REJECTED_AGGREGATE_CLOCK" not in result["html"]

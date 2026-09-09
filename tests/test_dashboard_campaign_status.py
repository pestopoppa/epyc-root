from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dashboard import campaign_status as C
from dashboard import loop_status, server

H = "a" * 64


def stamp(age: float = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat().replace(
        "+00:00", "Z")


def body(**changes):
    row = {
        "schema": C.SNAPSHOT_SCHEMA,
        "producer_build": {
            "schema": "epyc.autokernel.loaded_producer_build.v1",
            "scope": "campaign_control_callable_bytecode_and_selected_constants",
            "module": "autokernel.loop.campaign_control",
            "identity_basis": "loaded_callable_bytecode_and_constants_sha256",
            "included_symbols": ["method:CampaignController.snapshot"],
            "excluded_scope": ["campaign_service_transport"],
            "sha256": H,
        },
        "producer_schema": C.SNAPSHOT_SCHEMA,
        "campaign_id": "campaign-1", "config_generation": 1,
        "config_digest": H, "requested_manifest_digest": "b" * 64,
        "supervisor_incarnation": 1, "stream_epoch": 1, "sequence": 1,
        "journal_cursor": 1, "control_revision": 0,
        "generated_at": stamp(), "desired_state": "paused",
        "observed_state": "paused", "command_results": [],
        "active_worker": None, "producer_heartbeat_at": stamp(),
        "last_scientific_result_at": None, "worker_activity_at": None,
        "execution_authorized": False,
        "prerequisite_reason": "explicit resume required",
    }
    row.update(changes)
    return row


def health(snapshot=None, **changes):
    source = snapshot or body()
    row = {"schema": C.HEALTH_SCHEMA, "ok": True,
           "transport": "campaign-control-http", "producer": "running",
           "service_build": {
               "schema": "epyc.autokernel.loaded_producer_build.v1",
               "scope": "campaign_service_loaded_transport_bytecode_and_constants",
               "module": "autokernel.loop.campaign_service",
               "identity_basis": "loaded_callable_bytecode_and_constants_sha256",
               "included_symbols": ["make_handler"],
               "excluded_scope": ["campaign_controller"], "sha256": "c" * 64,
           },
           "campaign_id": source["campaign_id"],
           "config_generation": source["config_generation"],
           "config_digest": source["config_digest"],
           "supervisor_incarnation": source["supervisor_incarnation"],
           "stream_epoch": source["stream_epoch"],
           "allowed_origin": "http://127.0.0.1:8100", "error": None}
    row.update(changes)
    return row


class Response:
    def __init__(self, value, *, url=None):
        self.value = value
        self.url = url
        self.closed = False

    def read(self, amount=-1):
        return json.dumps(self.value).encode()[:amount]

    def close(self):
        self.closed = True

    def geturl(self):
        return self.url or "http://127.0.0.1:9999/health"


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setenv(C.STORE_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(C.CAMPAIGN_ID_ENV, "campaign-1")
    monkeypatch.setenv(C.CONFIG_GENERATION_ENV, "1")
    monkeypatch.setenv(C.CONFIG_DIGEST_ENV, H)
    return tmp_path


def write(root: Path, value) -> None:
    (root / C.SNAPSHOT_FILENAME).write_text(json.dumps(value), encoding="utf-8")


def test_checked_producer_v1_fixture_contract_digest():
    fixture = body(generated_at="2026-09-09T00:00:00Z",
                   producer_heartbeat_at="2026-09-09T00:00:00Z")
    digest = hashlib.sha256(json.dumps(
        fixture, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == "bdfa1d9b472ef649ca64b690da5ce1bf02146d6370dcd5a8628beb1f598555db"
    assert C.validate_snapshot(fixture) == fixture


def test_unconfigured_is_legacy_and_configured_absence_is_not_legacy(monkeypatch, configured):
    monkeypatch.delenv(C.STORE_ROOT_ENV)
    assert C.snapshot()["state"] == "legacy"
    monkeypatch.setenv(C.STORE_ROOT_ENV, str(configured))
    result = C.snapshot()
    assert result["state"] == "absent" and result["campaign"] is None


def test_malformed_or_wrong_identity_never_falls_back(configured):
    write(configured, {"schema": C.SNAPSHOT_SCHEMA})
    assert C.snapshot()["state"] == "malformed"
    write(configured, body(campaign_id="other"))
    result = C.snapshot()
    assert result["state"] == "malformed"
    assert "identity differs" in result["error"]


@pytest.mark.parametrize("field,value", [
    ("sequence", True), ("stream_epoch", 0), ("config_generation", False),
    ("generated_at", "undated"), ("execution_authorized", True),
    ("active_worker", {}),
])
def test_strict_snapshot_rejects_malformed_authority_fields(field, value):
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body(**{field: value}))


@pytest.mark.parametrize("mutation", [
    lambda row: row.update({"desired_state": []}),
    lambda row: row.update({"observed_state": {}}),
    lambda row: row["command_results"].append({
        "request_id": "x", "operation": [], "payload_digest": H,
        "accepted": True, "completed": True, "control_revision": 1,
        "desired_state": "paused", "observed_state": "paused",
        "prerequisite_reason": None}),
    lambda row: row["producer_build"].update({1: "mixed key"}),
])
def test_nested_shape_mutations_are_typed_refusals(mutation):
    row = body(control_revision=1)
    mutation(row)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(row)


def test_validated_snapshot_is_detached_from_mutable_input():
    source = body()
    validated = C.validate_snapshot(source)
    source["producer_build"]["included_symbols"].append("actor mutation")
    source["command_results"].append({})
    assert validated["producer_build"]["included_symbols"] == [
        "method:CampaignController.snapshot"]
    assert validated["command_results"] == []


def test_invalid_utf8_is_malformed_not_legacy(configured):
    (configured / C.SNAPSHOT_FILENAME).write_bytes(b"\xff\xfe")
    result = C.snapshot()
    assert result["configured"] is True and result["state"] == "malformed"


def test_matching_health_makes_paused_or_drained_healthy_without_worker(
        configured, monkeypatch):
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    monkeypatch.setenv(C.HUB_ORIGIN_ENV, "http://127.0.0.1:8100")
    for observed in ("paused", "drained"):
        snapshot = body(desired_state=observed, observed_state=observed,
                        prerequisite_reason=None)
        write(configured, snapshot)
        result = C.snapshot(
            health_opener=lambda *_args, snapshot=snapshot, **_kwargs: Response(
                health(snapshot)))
        assert result["state"] == "live"
        assert result["controls"]["available"] is True
        assert result["campaign"]["active_worker"] is None


@pytest.mark.parametrize("changes", [
    {"transport": "other"}, {"producer": "starting"}, {"producer": []},
    {"ok": False, "producer": "running", "error": "failed"},
    {"ok": True, "producer": "running", "error": "unexpected"},
])
def test_transport_health_contract_is_strict(changes):
    with pytest.raises(C.CampaignStatusError):
        C.validate_health(health(**changes))


def _probe_until_settled(report, opener, cache):
    deadline = time.monotonic() + 1
    while True:
        result = C.observe_health(report, opener=opener, cache=cache)
        if "pending" not in result["reason"]:
            return result
        assert time.monotonic() < deadline
        time.sleep(0.005)


def test_health_probe_is_async_bounded_and_single_owner_under_trickle():
    entered, release = threading.Event(), threading.Event()

    class TrickleResponse(Response):
        def read(self, _amount=-1):
            entered.set()
            release.wait(1)
            raise TimeoutError("trickled response exceeded its read timeout")

    response = TrickleResponse(health())

    def trickle(_request, timeout):
        assert timeout == C.HEALTH_TIMEOUT_S
        return response

    cache = C._HealthProbeCache()
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    started = time.monotonic()
    result = C.observe_health(report, opener=trickle, cache=cache)
    elapsed = time.monotonic() - started
    assert result["state"] == "unknown" and elapsed < 0.15
    assert entered.wait(0.2)
    assert cache._thread.is_alive()
    release.set()
    cache.close()
    assert response.closed is True


def test_health_probe_bounds_body_closes_response_and_refuses_redirect():
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}

    class RawResponse(Response):
        def __init__(self, raw, *, url=None):
            super().__init__({}, url=url)
            self.raw = raw

        def read(self, amount=-1):
            return self.raw[:amount]

    oversized = RawResponse(b"x" * (C.MAX_HEALTH_BODY + 1))
    cache = C._HealthProbeCache()
    result = _probe_until_settled(report, lambda *_args, **_kwargs: oversized, cache)
    cache.close()
    assert result["state"] == "unknown" and "too large" in result["reason"]
    assert oversized.closed is True

    redirected = Response(health(), url="http://unrelated.test/health")
    cache = C._HealthProbeCache()
    result = _probe_until_settled(report, lambda *_args, **_kwargs: redirected, cache)
    cache.close()
    assert result["state"] == "unknown" and "redirect" in result["reason"]
    assert redirected.closed is True


def test_health_probe_timeout_is_unknown_without_trusting_old_response():
    cache = C._HealthProbeCache()
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    result = _probe_until_settled(
        report, lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("slow")),
        cache)
    cache.close()
    assert result["state"] == "unknown" and "slow" in result["reason"]


def test_expired_health_cache_is_unknown_while_single_owner_refreshes():
    cache = C._HealthProbeCache()
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    release = threading.Event()
    blocked = False

    def opener(*_args, **_kwargs):
        if blocked:
            release.wait(1)
            raise TimeoutError("late refresh")
        return Response(health())

    initial = _probe_until_settled(report, opener, cache)
    assert initial["state"] == "live"
    with cache._condition:
        key, _recorded, result = cache._result
        cache._result = (key, time.monotonic() - C.HEALTH_CACHE_TTL_S - 1, result)
    blocked = True
    expired = C.observe_health(report, opener=opener, cache=cache)
    assert expired["state"] == "unknown"
    release.set()
    cache.close()


def test_health_cache_dates_completion_interval_and_has_bounded_idempotent_close():
    class Clock:
        value = 10.0

        def __call__(self):
            return self.value

    clock = Clock()
    cache = C._HealthProbeCache(clock=clock)
    assert cache._thread is None
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}

    def late_response(*_args, **_kwargs):
        clock.value += C.HEALTH_TIMEOUT_S + 1
        return Response(health())

    result = _probe_until_settled(report, late_response, cache)
    assert result["state"] == "unknown" and "too late" in result["reason"]
    for invalid_timeout in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(C.CampaignStatusError, match="finite"):
            C._HealthProbeCache().close(timeout=invalid_timeout)
    assert cache.close() is True and cache.close() is True
    assert C.observe_health(report, opener=late_response, cache=cache)["state"] == "unknown"

    entered, release = threading.Event(), threading.Event()
    blocked_cache = C._HealthProbeCache()

    class BlockedResponse(Response):
        def read(self, _amount=-1):
            entered.set()
            release.wait(1)
            return super().read(_amount)

    C.observe_health(report, opener=lambda *_args, **_kwargs: BlockedResponse(health()),
                     cache=blocked_cache)
    assert entered.wait(0.2)
    assert blocked_cache.close(timeout=0) is False
    assert blocked_cache.close_incomplete is True
    refused = C.observe_health(report, opener=None, cache=blocked_cache)
    assert refused["state"] == "unknown" and "close is incomplete" in refused["reason"]
    release.set()
    assert blocked_cache.close(timeout=1) is True


def test_health_cache_campaign_switch_never_reuses_prior_identity():
    cache = C._HealthProbeCache()
    old = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    new_snapshot = body(campaign_id="campaign-2")
    new = {"snapshot": new_snapshot, "gateway_url": "http://127.0.0.1:9999"}
    old_opener = lambda *_args, **_kwargs: Response(health(old["snapshot"]))
    assert _probe_until_settled(old, old_opener, cache)["identity"]["campaign_id"] == "campaign-1"
    new_opener = lambda *_args, **_kwargs: Response(health(new_snapshot))
    switched = _probe_until_settled(new, new_opener, cache)
    cache.close()
    assert switched["identity"]["campaign_id"] == "campaign-2"


def test_fresh_snapshot_without_live_identity_is_history_not_live(configured):
    write(configured, body())
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
        OSError("no service")))
    assert result["state"] == "history"
    assert result["controls"]["available"] is False


def test_new_server_identity_cannot_freshen_old_snapshot(configured, monkeypatch):
    snapshot = body()
    write(configured, snapshot)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(
        health(snapshot, supervisor_incarnation=2, stream_epoch=2)))
    assert result["state"] == "degraded"
    assert result["health"]["state"] == "mismatch"


def test_stale_heartbeat_and_explicit_transport_failure_are_degraded(
        configured, monkeypatch):
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    stale = body(producer_heartbeat_at=stamp(C.HEARTBEAT_STALE_AFTER_S + 10))
    write(configured, stale)
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(stale)))
    assert result["state"] == "degraded"

    drained = body(desired_state="drained", observed_state="drained",
                   prerequisite_reason=None)
    write(configured, drained)
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(
        health(drained, ok=False, producer="failed", error="publisher failed")))
    assert result["state"] == "degraded"
    assert result["health"]["state"] == "failed"


def test_future_clocks_and_nonfinite_now_never_freshen_campaign(configured, monkeypatch):
    future = stamp(-60)
    snapshot = body(generated_at=future, producer_heartbeat_at=future,
                    worker_activity_at=stamp(100), last_scientific_result_at=stamp(10000))
    write(configured, snapshot)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(snapshot)))
    assert result["state"] == "degraded"
    assert result["clocks"]["producer_heartbeat_at"]["state"] == "future"
    assert result["clocks"]["worker_activity_at"]["state"] == "known"
    assert result["clocks"]["last_scientific_result_at"]["state"] == "known"
    for invalid in (True, float("nan"), float("inf"), "now"):
        with pytest.raises(C.CampaignStatusError, match="finite"):
            C.snapshot(now=invalid)


def test_heartbeat_stage_and_scientific_clocks_are_not_collapsed(configured, monkeypatch):
    snapshot = body(producer_heartbeat_at=stamp(5), worker_activity_at=stamp(90),
                    last_scientific_result_at=stamp(7200))
    write(configured, snapshot)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(snapshot)))
    assert result["state"] == "live"
    clocks = result["clocks"]
    assert clocks["producer_heartbeat_at"]["age_s"] < 30
    assert clocks["worker_activity_at"]["age_s"] > 60
    assert clocks["last_scientific_result_at"]["age_s"] > 7000


def test_snapshot_ordering_duplicate_conflict_rollback_and_explicit_switch():
    first = body(sequence=2, journal_cursor=2)
    assert C.advance_snapshot(first, dict(first))["status"] == "duplicate"
    conflict = dict(first, prerequisite_reason="different historical reason")
    with pytest.raises(C.CampaignStatusError, match="same stream key"):
        C.advance_snapshot(first, conflict)
    assert C.advance_snapshot(first, body(sequence=1))["status"] == "older"
    rollback = body(sequence=3, journal_cursor=1)
    with pytest.raises(C.CampaignStatusError, match="rolls back"):
        C.advance_snapshot(first, rollback)
    switched = body(campaign_id="campaign-2")
    with pytest.raises(C.CampaignStatusError, match="explicit"):
        C.advance_snapshot(first, switched)
    assert C.advance_snapshot(first, switched, allow_campaign_switch=True)["status"] == "switched"


def test_epoch_change_consumes_full_snapshot_and_preserves_revisions():
    first = body(sequence=9, journal_cursor=4, control_revision=2)
    changed = body(stream_epoch=2, sequence=1, supervisor_incarnation=2,
                   journal_cursor=5, control_revision=2)
    result = C.advance_snapshot(first, changed)
    assert result == {"status": "accepted", "snapshot": C.validate_snapshot(changed)}
    with pytest.raises(C.CampaignStatusError, match="incarnation"):
        C.advance_snapshot(first, dict(changed, supervisor_incarnation=1))


def test_command_results_preserve_accepted_separate_from_completed():
    result = {"request_id": "resume-1", "operation": "resume",
              "payload_digest": H, "accepted": True, "completed": False,
              "control_revision": 1, "desired_state": "running",
              "observed_state": "waiting_prerequisite",
              "prerequisite_reason": "authority absent"}
    snapshot = C.validate_snapshot(body(control_revision=1, command_results=[result]))
    assert snapshot["command_results"][0]["accepted"] is True
    assert snapshot["command_results"][0]["completed"] is False


@pytest.mark.parametrize("changes", [
    {"accepted": False}, {"completed": True},
    {"observed_state": "running"}, {"prerequisite_reason": None},
    {"desired_state": "paused"},
])
def test_command_result_contract_refuses_management_contradictions(changes):
    result = {"request_id": "resume-1", "operation": "resume",
              "payload_digest": H, "accepted": True, "completed": False,
              "control_revision": 1, "desired_state": "running",
              "observed_state": "waiting_prerequisite",
              "prerequisite_reason": "authority absent"}
    result.update(changes)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body(control_revision=1, command_results=[result]))


def test_configured_malformed_campaign_cannot_hide_behind_fresh_legacy_loop(
        configured, monkeypatch):
    loop_root = configured / "legacy"
    loop_root.mkdir()
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(loop_root))
    (loop_root / loop_status.STATUS_FILENAME).write_text(json.dumps({
        "schema": loop_status.STATUS_SCHEMA, "generated_at": stamp(),
        "stale_after_s": 1800, "state": "running", "iterations_done": 1,
        "measurements_reached": 0, "champion_head": "c" * 40,
    }), encoding="utf-8")
    write(configured, {"schema": C.SNAPSHOT_SCHEMA})
    with server._watchdog_lock:
        server._watchdog_state.clear()
    payload = server.loop_payload()
    assert payload["freshness_state"] == "fresh"
    assert payload["campaign"]["state"] == "malformed"
    code, health_result = server.loop_data_health()
    assert code == 503 and health_result["status"] == "degraded"
    assert "campaign" in health_result["campaign_attention"]
    envelope = server.panel_envelopes()["autokernel_loop"]
    assert envelope["watchdog"]["state"] == "no_timestamp"


def test_selected_live_campaign_replaces_failed_legacy_health_fields(
        configured, monkeypatch):
    loop_root = configured / "failed-legacy"
    loop_root.mkdir()
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(loop_root))
    (loop_root / loop_status.STATUS_FILENAME).write_text(json.dumps({
        "schema": loop_status.STATUS_SCHEMA, "generated_at": stamp(),
        "stale_after_s": 1800, "state": "failed", "iterations_done": 1,
        "measurements_reached": 0, "champion_head": "c" * 40,
    }), encoding="utf-8")
    campaign = body()
    live = {"configured": True, "state": "live", "campaign": campaign,
            "health": {"state": "live", "matched": True, "reason": "fixture"},
            "clocks": {"producer_heartbeat_at": {"age_s": 1}},
            "evidence": "/selected/campaign-snapshot.json"}
    monkeypatch.setattr(C, "snapshot", lambda **_kwargs: live)
    with server._watchdog_lock:
        server._watchdog_state.clear()
    code, result = server.loop_data_health()
    assert code == 200 and result["status"] == "ok"
    assert result["selected_producer"] == "campaign"
    assert result["freshness_state"] == "live" and result["loop_state"] == "paused"
    assert result["evidence"] == "/selected/campaign-snapshot.json"
    assert result["declared_failure"] is None
    assert result["legacy_history"]["state"] == "failed"


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_command_lost_ack_retries_exact_request_and_stale_refresh_cannot_roll_back(
        tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    scripts = re.findall(r"<script[^>]*>(.*?)</script>",
                         page.read_text(encoding="utf-8"), re.DOTALL)
    source = "\n".join(scripts).replace(
        "tick();\nsetInterval(tick, 20000);", "")
    initial = body(sequence=1, journal_cursor=1)
    fresh = body(sequence=2, journal_cursor=1)
    after = body(sequence=3, journal_cursor=2, control_revision=1)
    view = {"configured": True, "state": "live", "campaign": initial,
            "clocks": {}, "controls": {"available": True,
                "gateway_url": "https://gateway.test", "hub_origin": "https://hub.test",
                "reason": None}}
    script = r'''
const fs=require("fs"), {webcrypto}=require("crypto");
global.crypto=webcrypto; global.TextEncoder=TextEncoder;
const made={}; function el(id){return made[id]||(made[id]={id,style:{},classList:{add(){},remove(){},toggle(){}},
  _html:"",set innerHTML(v){this._html=String(v)},get innerHTML(){return this._html},
  set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
  addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
  createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0; global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8"), fixture=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
let snapshots=[fixture.fresh,fixture.after,fixture.fresh], posts=[], commandCalls=0;
global.fetch=async(url,options={})=>{
  if(url.endsWith("/snapshot")){const value=snapshots.shift();return{ok:true,status:200,json:async()=>value};}
  const posted=JSON.parse(options.body);posts.push(posted);commandCalls++;
  if(commandCalls===1)throw new Error("lost ack");
  return{ok:true,status:200,json:async()=>({request_id:posted.request_id,operation:posted.operation,
    payload_digest:posted.payload_digest,accepted:true,completed:true,control_revision:1,
    desired_state:"paused",observed_state:"paused",prerequisite_reason:null})};
};
eval(page+`;globalThis.hooks={renderCampaign,campaignSend,campaignRefreshAuthenticated,
  campaignAcceptSnapshot,renderFetchFailure,setToken:v=>campaignToken=v,pending:()=>campaignPending,
  accepted:()=>campaignAccepted,streamError:()=>campaignStreamError};`);
(async()=>{hooks.renderCampaign({campaign:fixture.view});hooks.setToken("memory-secret");
  await hooks.campaignSend("pause",fixture.view);const first=hooks.pending();
  hooks.renderFetchFailure("hub down");const afterHubFailure=hooks.pending();
  await hooks.campaignSend("drain",fixture.view);const afterDrain=hooks.pending();
  await hooks.campaignSend("pause",fixture.view,true);const afterRetry=hooks.pending();
  let staleError="";try{await hooks.campaignRefreshAuthenticated(fixture.view)}catch(e){staleError=e.message}
  const retained=hooks.accepted();
  let conflictError="";try{hooks.campaignAcceptSnapshot({...retained,requested_manifest_digest:"d".repeat(64)})}
    catch(e){conflictError=e.message}
  let malformedError="";try{hooks.campaignAcceptSnapshot({...retained,sequence:[]})}
    catch(e){malformedError=e.message}
  const malformedStream=hooks.streamError();
  hooks.renderCampaign({campaign:{...fixture.view,state:"live",campaign:fixture.fresh}});
  const staleRender={html:made.campaign._html,badge:made["campaign-badgetxt"]._text,
    drainDisabled:made["campaign-drain"].disabled};
  console.log(JSON.stringify({posts,first,afterHubFailure,afterDrain,afterRetry,retained,staleError,
    conflictError,malformedError,malformedStream,staleRender,
    streamError:hooks.streamError(),status:made["campaign-command-status"]._text||""}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page_js = tmp_path / "page.js"
    runner = tmp_path / "runner.js"
    fixture = tmp_path / "fixture.json"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(script, encoding="utf-8")
    fixture.write_text(json.dumps({"view": view, "fresh": fresh, "after": after}),
                       encoding="utf-8")
    run = subprocess.run(["node", str(runner), str(page_js), str(fixture)],
                         capture_output=True, text=True, timeout=10, check=True)
    result = json.loads(run.stdout)
    assert len(result["posts"]) == 2
    assert result["posts"][0] == result["posts"][1]
    assert result["posts"][0]["operation"] == "pause"
    expected = hashlib.sha256(json.dumps({
        "config_generation": 1, "campaign_id": "campaign-1",
        "operation": "pause", "payload": {}},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert result["posts"][0]["payload_digest"] == expected
    assert result["first"]["request_id"] == result["posts"][0]["request_id"]
    assert result["afterHubFailure"] == result["first"]
    assert result["afterDrain"] == result["first"]
    assert result["afterRetry"] is None
    assert result["retained"]["sequence"] == 3
    assert "older" in result["staleError"]
    assert "same campaign stream key" in result["conflictError"]
    assert "sequence is malformed" in result["malformedError"]
    assert "sequence is malformed" in result["malformedStream"]
    assert "older" in result["streamError"]
    assert "1:3" in result["staleRender"]["html"]
    assert result["staleRender"]["badge"] == "UNKNOWN / HISTORY"
    assert result["staleRender"]["drainDisabled"] is True
    assert "accepted revision 1; completed" in result["status"]


def test_page_keeps_token_memory_only_and_has_no_hub_control_proxy():
    page = (Path(__file__).resolve().parents[1] / "dashboard/static/loop.html").read_text(
        encoding="utf-8")
    assert "localStorage" not in page and "sessionStorage" not in page
    assert "Bearer ${campaignToken}" in page
    assert "/api/campaign" not in page
    assert "secure browser context" in page
    assert "campaign-retry" in page
    assert "AbortController" in page


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_total_body_deadline_size_and_parse_fail_closed(tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    initial, fresh = body(), body(sequence=2)
    view = {"configured": True, "state": "live", "campaign": initial,
            "clocks": {}, "controls": {"available": True,
                "gateway_url": "https://gateway.test", "reason": None}}
    script = r'''
const fs=require("fs"),{webcrypto}=require("crypto");global.crypto=webcrypto;
global.TextEncoder=TextEncoder;const made={};function el(id){return made[id]||(made[id]={id,
 style:{},classList:{add(){},remove(){},toggle(){}},_html:"",set innerHTML(v){this._html=String(v)},
 get innerHTML(){return this._html},set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
 createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};global.setInterval=()=>0;
let timers=[];global.setTimeout=fn=>{const row={fn,active:true};timers.push(row);return row};
global.clearTimeout=row=>{if(row)row.active=false};const fire=()=>{const row=[...timers].reverse().find(x=>x.active);row.fn()};
const page=fs.readFileSync(process.argv[2],"utf8"),f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
eval(page+`;globalThis.h={campaignFetch,renderCampaign,campaignSend,
 validateAck:campaignValidateAck,validateSnapshot:campaignValidateSnapshot,
 setToken:v=>campaignToken=v,pending:()=>campaignPending,inflight:()=>campaignInFlight};`);
function stalled(signal,mark){let started=false,cancelled=false,aborted=false;
 signal.addEventListener("abort",()=>aborted=true);const reader={read(){started=true;return new Promise(()=>{})},
 cancel(){cancelled=true;return Promise.resolve()}};mark(()=>({started,cancelled,aborted}));
 return{ok:true,status:200,body:{getReader:()=>reader}}}
(async()=>{
 let inspect,readState,snapshotError="";global.fetch=async(_url,o)=>stalled(o.signal,x=>{inspect=x});
 const snapshot=h.campaignFetch("https://gateway.test/snapshot",{},100).catch(e=>snapshotError=e.message);
 while(!inspect||!inspect().started)await new Promise(r=>setImmediate(r));fire();await snapshot;readState=inspect();
 let oversized="";global.fetch=async()=>({ok:true,status:200,text:async()=>"x".repeat(101)});
 await h.campaignFetch("x",{},100).catch(e=>oversized=e.message);
 let malformed="";global.fetch=async()=>({ok:true,status:200,text:async()=>"{"});
 await h.campaignFetch("x",{},100).catch(e=>malformed=e.message);
 let revisionError="";try{h.validateAck({request_id:"r",operation:"pause",payload_digest:"a".repeat(64),
  accepted:true,completed:true,control_revision:2,desired_state:"paused",observed_state:"paused",
  prerequisite_reason:null},{request_id:"r",operation:"pause",payload_digest:"a".repeat(64),
  expected_control_revision:0})}catch(e){revisionError=e.message}
 let clockError="";try{h.validateSnapshot({...f.fresh,producer_heartbeat_at:
  new Date(Date.parse(f.fresh.generated_at)+6000).toISOString()})}catch(e){clockError=e.message}
 h.renderCampaign({campaign:f.view});h.setToken("secret");let calls=0,ackInspect;
 global.fetch=async(_url,o)=>{calls++;if(calls===1)return{ok:true,status:200,json:async()=>f.fresh};
  return stalled(o.signal,x=>{ackInspect=x})};
 const command=h.campaignSend("pause",f.view);
 while(!ackInspect||!ackInspect().started)await new Promise(r=>setImmediate(r));fire();await command;
 console.log(JSON.stringify({snapshotError,readState,oversized,malformed,revisionError,clockError,ack:ackInspect(),
  pending:h.pending(),inflight:h.inflight(),status:made["campaign-command-status"]._text}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page_js, runner, fixture = tmp_path / "page.js", tmp_path / "runner.js", tmp_path / "f.json"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(script, encoding="utf-8")
    fixture.write_text(json.dumps({"view": view, "fresh": fresh}), encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert "timed out" in result["snapshotError"]
    assert result["readState"] == {"started": True, "cancelled": True, "aborted": True}
    assert "oversized" in result["oversized"]
    assert "malformed JSON" in result["malformed"]
    assert "does not match" in result["revisionError"]
    assert "observation window" in result["clockError"]
    assert result["ack"] == {"started": True, "cancelled": True, "aborted": True}
    assert result["pending"]["operation"] == "pause"
    assert result["inflight"] is False
    assert "Retry keeps the same request ID" in result["status"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_serializes_double_click_and_retains_malformed_ack_for_retry(tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    initial = body()
    fresh = body(sequence=2)
    later = body(sequence=3, control_revision=1)
    script = r'''
const fs=require("fs"),{webcrypto}=require("crypto");global.crypto=webcrypto;
global.TextEncoder=TextEncoder;const made={};function el(id){return made[id]||(made[id]={id,
 style:{},classList:{add(){},remove(){},toggle(){}},_html:"",set innerHTML(v){this._html=String(v)},
 get innerHTML(){return this._html},set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
 createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0;global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8"),f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
let snapshots=[f.fresh,f.later],posts=[],release;
global.fetch=async(url,options={})=>{if(url.endsWith("/snapshot"))return{ok:true,status:200,json:async()=>snapshots.shift()};
 const posted=JSON.parse(options.body);posts.push(posted);if(posts.length===1)await new Promise(r=>release=r);
 const valid={request_id:posted.request_id,operation:posted.operation,payload_digest:posted.payload_digest,
  accepted:true,completed:true,control_revision:posted.expected_control_revision+1,
  desired_state:posted.operation==="resume"?"running":posted.operation+"d",
  observed_state:posted.operation==="resume"?"running":posted.operation+"d",prerequisite_reason:null};
 if(posts.length===2)valid.observed_state="waiting_prerequisite";return{ok:true,status:200,json:async()=>valid};};
eval(page+`;globalThis.h={renderCampaign,campaignSend,setToken:v=>campaignToken=v,
 pending:()=>campaignPending};`);
(async()=>{h.renderCampaign({campaign:f.view});h.setToken("secret");
 const first=h.campaignSend("resume",f.view);await Promise.resolve();
 await h.campaignSend("drain",f.view);while(!release)await new Promise(r=>setImmediate(r));release();await first;
 const afterFirst=h.pending();await h.campaignSend("pause",f.view);const retained=h.pending();
 console.log(JSON.stringify({posts,afterFirst,retained,status:made["campaign-command-status"]._text}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page_js, runner, fixture = tmp_path / "page.js", tmp_path / "runner.js", tmp_path / "f.json"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(script, encoding="utf-8")
    fixture.write_text(json.dumps({"view": {"configured": True, "state": "live",
        "campaign": initial, "clocks": {}, "controls": {"available": True,
        "gateway_url": "https://gateway.test", "reason": None}},
        "fresh": fresh, "later": later}), encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert [row["operation"] for row in result["posts"]] == ["resume", "pause"]
    assert result["afterFirst"] is None
    assert result["retained"] == result["posts"][1]
    assert "contradictory" in result["status"]

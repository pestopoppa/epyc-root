"""Original serial projection and actual page control code; no hardware."""
import copy
import importlib
import json
import subprocess

import pytest

from dashboard import loop_status
from tests import test_dashboard_serial_loop as original
from tests.test_dashboard_runtime_js import _page_js, _run

producer = original.producer
sources = original.sources


def _control(sources):
    _canonical, router, _child, active, _routing = sources
    body = json.loads((router / "loop-status.json").read_text())
    module = importlib.import_module("autokernel.loop.serial_control")
    owner = module.SerialControl({"next_batch": 0}, lambda: None, lambda *_: None,
                                 config_digest=body["epoch_sha256"])
    owner.endpoint = "http://127.0.0.1:8911"
    owner.allowed_origin = "http://localhost:8100"
    body["serial_control"] = owner.pump(active)
    (router / "loop-status.json").write_text(json.dumps(body))
    return body, owner


def test_original_control_report_page_and_paused_without_child(sources, tmp_path):
    body, owner = _control(sources)
    wire = loop_status.snapshot()[0]
    assert wire["serial"]["child"]["joined"]
    assert wire["serial"]["control"]["owner_id"] == owner.owner_id
    page = _run(_page_js(), wire, tmp_path, ["render"])
    assert page["threw"] == []
    assert "Pause after batch" in page["by_id"]["serial-controls"]
    assert "Resume" in page["by_id"]["serial-controls"]
    assert "Drain / STOP" in page["by_id"]["serial-controls"]
    assert wire["knowledge"]["attempts"] > 0
    owner.state["control"]["desired_state"] = "paused"
    body["target"] = None
    body["serial_control"] = owner.pump()
    (sources[1] / "loop-status.json").write_text(json.dumps(body))
    paused = loop_status.snapshot()[0]
    assert paused["serial"]["state"] == "paused"
    assert paused["serial"]["child"] is None
    assert paused["knowledge"]["attempts"] == wire["knowledge"]["attempts"]


@pytest.mark.parametrize("fault", ["schema", "owner", "target"])
def test_optional_controls_fault_does_not_hide_original_child(sources, tmp_path, fault):
    body, _owner = _control(sources)
    if fault == "schema":
        body["serial_control"] = []
    elif fault == "owner":
        body["serial_control"]["config_digest"] = "other"
    else:
        body["serial_control"]["active_target"] = "other"
    (sources[1] / "loop-status.json").write_text(json.dumps(body))
    wire = loop_status.snapshot()[0]
    assert wire["serial"]["child"]["joined"]
    assert wire["serial"]["child"]["loop"]["iterations_done"] == 1
    assert wire["serial"]["control"] is None
    assert wire["serial"]["reader_error"] is None
    assert wire["serial"]["control_error"]
    page = _run(_page_js(), wire, tmp_path, ["render"])
    assert page["threw"] == []
    assert "Controls unavailable" in page["by_id"]["serial-controls"]
    assert "Pause after batch" not in page["by_id"]["serial-controls"]


def test_page_binds_owner_target_retries_exact_request_and_recovers_terminal_ack(sources, tmp_path):
    _control(sources)
    payload = loop_status.snapshot()[0]
    script = r'''
const fs=require('fs'),{webcrypto}=require('crypto');global.crypto=webcrypto;
const made={};function el(id){return made[id]||(made[id]={style:{},classList:{add(){},remove(){},toggle(){}},
  innerHTML:'',textContent:'',addEventListener(){},setAttribute(){},removeAttribute(){}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],addEventListener(){}};
global.window={isSecureContext:true,location:{},addEventListener(){}};global.setInterval=()=>0;
const view=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
let current=structuredClone(view.serial.control),posts=[],lost=true,moved=false;
global.fetch=async(url,options={})=>{
  if(url.endsWith('/snapshot'))return{ok:true,status:200,json:async()=>moved?{...current,owner_id:'different'}:current};
  const request=JSON.parse(options.body);posts.push(request);
  if(lost){lost=false;throw new Error('lost acknowledgement');}
  return{ok:true,status:200,json:async()=>({request_id:request.request_id,operation:request.operation,
    revision:request.expected_revision+1,completed:false,outcome:'pending'})};
};
eval(fs.readFileSync(process.argv[2],'utf8')+`;globalThis.h={renderSerialControls,serialSend,renderFetchFailure,
  token:v=>serialToken=v,pending:()=>serialPending,message:()=>serialControlMessage};`);
(async()=>{
  h.renderSerialControls(view);h.token('memory-only-secret');
  await h.serialSend('pause');const pending=structuredClone(h.pending());
  h.renderFetchFailure('hub unavailable');const cleared=made['serial-controls'].innerHTML;
  await h.serialSend('drain');const postCountAfterFailure=posts.length;
  h.renderSerialControls(view);await h.serialSend(null);
  const exact=JSON.stringify(posts[0])===JSON.stringify(posts[1]);
  moved=true;await h.serialSend('resume');const refusal=h.message(),postCountAfterMove=posts.length;
  moved=false;lost=true;await h.serialSend('drain');const drain=h.pending();
  const terminal=structuredClone(view);terminal.serial.control.observed_state='drained';
  terminal.serial.control.commands=[{request:drain,result:{request_id:drain.request_id,
    operation:'drain',revision:drain.expected_revision+1,completed:true,outcome:'completed'}}];
  h.renderSerialControls(terminal);
  const reconciled=h.pending(),message=h.message(),html=made['serial-controls'].innerHTML;
  const stale=structuredClone(view);stale.freshness_state='stale';h.renderSerialControls(stale);
  await h.serialSend('resume');
  const staleMessage=h.message();
  h.renderSerialControls(view);lost=true;await h.serialSend('pause');const oldUncertain=structuredClone(h.pending());
  const restarted=structuredClone(view);restarted.serial.control.owner_id='new-owner';
  current=structuredClone(restarted.serial.control);h.renderSerialControls(restarted);
  const detached=h.pending(),newOwnerHtml=made['serial-controls'].innerHTML;
  await h.serialSend('resume');const newCommand=posts[posts.length-1],newOwnerMessage=h.message();
  console.log(JSON.stringify({pending,cleared,postCountAfterFailure,exact,refusal,postCountAfterMove,
    reconciled,message,html,posts,staleMessage,tokenLeaked:html.includes('memory-only-secret'),
    oldUncertain,detached,newOwnerHtml,newCommand,newOwnerMessage}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page = tmp_path / "page.js"
    page.write_text(_page_js().replace("tick();\nsetInterval(tick, 20000);", ""))
    fixture = tmp_path / "payload.json"
    fixture.write_text(json.dumps(copy.deepcopy(payload)))
    harness = tmp_path / "controls.js"
    harness.write_text(script)
    result = subprocess.run(["node", str(harness), str(page), str(fixture)],
                            capture_output=True, text=True, check=True, timeout=10)
    row = json.loads(result.stdout)
    assert row["pending"]["operation"] == "pause"
    assert row["cleared"] == "" and row["postCountAfterFailure"] == 1
    assert row["exact"] and row["postCountAfterMove"] == 2
    assert "owner/batch/target changed" in row["refusal"]
    assert row["reconciled"] is None and row["message"] == "drain: completed"
    assert "Serial owner is terminal" in row["html"]
    assert len(row["posts"]) == 5 and not row["tokenLeaked"]
    assert "refresh a current serial owner first" in row["staleMessage"]
    assert row["detached"] is None
    assert "outcome uncertain" in row["newOwnerHtml"] and "Not replayed to the new owner" in row["newOwnerHtml"]
    assert '<button id="serial-resume" >Resume</button>' in row["newOwnerHtml"]
    assert row["newCommand"]["owner_id"] == "new-owner"
    assert row["newCommand"]["operation"] == "resume" and row["newOwnerMessage"].startswith("resume: pending")
    assert row["newCommand"]["request_id"] != row["oldUncertain"]["request_id"]
    assert sum(post["request_id"] == row["oldUncertain"]["request_id"] for post in row["posts"]) == 1

#!/usr/bin/env python3
"""Private INF-66 prospective instrument comparison; default mode is model-free self-test.

This diagnostic uses the existing recipe, CPU claim and inference witness. No production
state changes. See PREP_NOT_READY below before use. This file is not a ratified instrument.
"""
import importlib.util, json, os, subprocess, sys, tempfile, time, threading, urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,'/workspace/repos/epyc-inference-research/scripts/kernel_rnd')
sys.path.insert(0,'/workspace/repos/epyc-inference-research/scripts/lib')
import runner_parts as parts
from autokernel.execution import cpu_region_claim as crc, microbench, screening_baseline
from autokernel import schemas
import qwen38_flash_next_recipe as recipe
sys.path.insert(0,'/workspace/repos/epyc-inference-research/scripts/benchmark')
import cpu_prefill_v8_regression_runner as annex_b

BIN={'old':Path('/mnt/raid0/llm/tmp/inf70/agents/champion3/bin-c3'), 'instrument':Path('/mnt/raid0/llm/tmp/inf70/agents/retest1/bin-r1')}
MANIFESTS={'old':(BIN['old'].parent,'binaries.sha256'), 'instrument':(BIN['instrument'],'../binaries.sha256')}
CLIENT=Path('/mnt/raid0/llm/tmp/inf70/agents/harness1/client.py')
PREP_NOT_READY=('Full DSO provenance and continuous Annex B residual-load accounting must be bound before execution; '
                'model-free mock tests do not validate real server behavior.')

class Refusal(Exception): pass

def host_health(uptime_path=Path('/proc/uptime')):
    age=float(uptime_path.read_text().split()[0])
    if age>=7*24*3600: raise Refusal('host uptime at least one week; reboot required')
    return age

def require_claim(adapter):
    result=adapter.attest()
    if result.check.outcome!=schemas.PASS: raise Refusal('CPU claim not verified: '+str(result.check.reasons))
    return result

def witness(previous=None):
    w=screening_baseline.competing_inference_witness(previous_ledger=previous)
    if w.get('competing') is not False: raise Refusal('competing inference or unavailable witness')
    return w

def verify_files():
    for arm,(cwd,name) in MANIFESTS.items():
        subprocess.run(['sha256sum','-c',name],cwd=cwd,check=True,stdout=subprocess.DEVNULL)
    for name,size,digest in recipe.TRUNK_SHARDS:
        p=Path(name)
        if p.stat().st_size!=size or parts.sha256(p)!=digest: raise Refusal('model identity mismatch: '+name)

def rows_ok(path, log):
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    if len(rows)!=24 or len({r.get('id') for r in rows})!=24: raise Refusal('incomplete or duplicate prompt set')
    if any(r.get('verdict')=='HTTP-ERROR' or not r.get('sha') or not r.get('pred_ms') for r in rows): raise Refusal('invalid client record')
    text=log.read_text()
    if 'warmup ok' not in text or 'ARM_DONE ' not in text: raise Refusal('client incomplete')
    return {r['id']:r['sha'] for r in rows}

def stop_owned(p):
    if p is not None: parts.stop_owned(p)

def collect_monitor(pid, stop, samples, errors):
    while not stop.wait(1):
        try: samples.append(annex_b.monitor_snapshot(pid, os.getpgid(pid)))
        except Exception as exc:
            errors.append(repr(exc)); stop.set(); return

def run_one(arm, index, out, plan, sealed, adapter):
    """Run one fresh server; owned children always terminated in finally."""
    label=f'{arm}_{index:02d}'; page=out/(label+'.knob'); server=None; client=None
    stop=threading.Event(); samples=[]; errors=[]; monitor=None
    arm_start=witness(); require_claim(adapter)
    env=os.environ.copy(); env.update(plan['env']);env.pop('GGML_NOHUGEPAGE_PROCESS',None)
    env['LD_LIBRARY_PATH']=str(BIN[arm])+os.pathsep+env.get('LD_LIBRARY_PATH','')
    if arm=='instrument': parts.create_knob_page(page);parts.verify_knob_page(page);env['GGML_KNOB_FILE']=str(page)
    else: env.pop('GGML_KNOB_FILE',None)
    logfile=out/(label+'.server.log')
    try:
        with logfile.open('xb') as f:
            server=subprocess.Popen(plan['cmd'],env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+800
            while time.monotonic()<deadline:
                if server.poll() is not None: raise Refusal('server exited before readiness')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:18497/health',timeout=2) as r:
                        if r.status==200: break
                except OSError: time.sleep(2)
            else: raise Refusal('server readiness timeout')
            parts.verify_runtime(server.pid,BIN[arm],page if arm=='instrument' else None)
            mapped=parts.check_live_dso(server.pid,BIN[arm],sealed)
            monitor=threading.Thread(target=collect_monitor,args=(server.pid,stop,samples,errors),daemon=True);monitor.start()
            with (out/(label+'.client.log')).open('xb') as clientlog:
                client=subprocess.Popen([sys.executable,str(CLIENT),label,'18497'],env={**os.environ,'CLIENT_OUT':str(out)},stdout=clientlog,stderr=subprocess.STDOUT)
                while client.poll() is None:
                    if server.poll() is not None or stop.wait(0.2): raise Refusal('server or accounting failed during client')
                if client.returncode!=0: raise Refusal('client failed')
            stop.set(); monitor.join(timeout=10)
            if monitor.is_alive() or errors: raise Refusal('accounting failed: '+repr(errors))
            (out/(label+'.monitor.json')).write_text(json.dumps(samples,indent=2))
            # Reuse the existing Annex B validator unchanged; no new grading rule.
            result=annex_b.validate_monitor_samples(samples)
            parts.verify_runtime(server.pid,BIN[arm],page if arm=='instrument' else None)
            if parts.check_live_dso(server.pid,BIN[arm],sealed)!=mapped: raise Refusal('loaded DSO set changed')
            if arm=='instrument':
                expected='SCALE_SPLIT=0 SOLO_YIELD_ROWCOL=0 TINY_SOLO_CLAMP=1 GET_ROWS_SOLO=0'
                if expected not in logfile.read_text(): raise Refusal('knob readback missing')
                parts.verify_knob_page(page)
            data=rows_ok(out/(label+'.rows.jsonl'),out/(label+'.client.log'))
            arm_end=witness(arm_start['cpu_ledger']);require_claim(adapter)
            (out/(label+'.witness.json')).write_text(json.dumps({'start':arm_start,'end':arm_end,'dso':mapped,'accounting':result},indent=2,default=str))
            return data
    finally:
        stop.set()
        if monitor is not None: monitor.join(timeout=10)
        stop_owned(client);stop_owned(server)



def campaign(out, plans, sealed, adapter, run_arm=run_one):
    """Fixed 12-pair balanced diagnostic, with exact per-prompt parity as a stop condition."""
    records=[]
    for index in range(1,13):
        order=('old','instrument') if index%2 else ('instrument','old')
        pair={}
        for arm in order:
            require_claim(adapter)
            pair[arm]=run_arm(arm,index,out,plans[arm],sealed[arm],adapter)
            require_claim(adapter)
        if pair['old']!=pair['instrument']:
            (out/'PARITY_FAIL.json').write_text(json.dumps({'pair':index,'old':pair['old'],'instrument':pair['instrument']},indent=2))
            raise Refusal('paired prompt output parity failed')
        records.append({'pair':index,'order':order,'parity':'equal'})
        (out/'completed-pairs.json').write_text(json.dumps(records,indent=2))
    return records


def selftest():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); page=root/'knob'; parts.create_knob_page(page);parts.verify_knob_page(page)
        p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);stop_owned(p)
        assert p.poll() is not None
        uptime=root/'uptime';uptime.write_text('604800 0')
        try: host_health(uptime);raise AssertionError('stale host accepted')
        except Refusal: pass
        fake=type('Fake',(),{'attest':lambda self:type('A',(),{'check':type('C',(),{'outcome':schemas.COULD_NOT_CHECK,'reasons':['unknown']})()})()})()
        try: require_claim(fake);raise AssertionError('unknown claim accepted')
        except Refusal:pass
        bad=root/'rows';bad.write_text('{}\n')
        try: rows_ok(bad,bad);raise AssertionError('incomplete rows accepted')
        except Refusal:pass
    print('PASS: model-free knob lifecycle, owned-child teardown, uptime, claim and row refusals')

def execute():
    # The missing preconditions are not bypassable by command-line, environment or tests.
    host_health()
    raise Refusal(PREP_NOT_READY)

if __name__=='__main__':
    try:
        if sys.argv[1:]==['--selftest']: selftest()
        elif sys.argv[1:]==['--execute']: execute()
        else: raise Refusal('usage: --selftest | --execute')
    except (Refusal, OSError, ValueError, subprocess.SubprocessError) as e:
        print('REFUSED:',e,file=sys.stderr);sys.exit(2)

#!/usr/bin/env python3
"""Candidate SR-8 GPU worker; fail closed on missing runtime evidence.

This file is not a qualified launcher until the model preflight, admission,
process-tree supervision, smoke and writer integration are bound by the row.
"""
import ast, hashlib, json, os, re, signal, subprocess, threading, time, urllib.request
from session_drain import spawn_session, drain_session
from pathlib import Path

BASE=Path(os.environ.get('SR8_ROOT','/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-fresh-edit-20261105'))
ROOT=(BASE/'smoke'/hashlib.sha256(os.environ.get('FILLER_DRYRUN_RESULT_PATH','missing').encode()).hexdigest()[:16] if os.environ.get('FILLER_DRYRUN')=='1' else BASE/'live')
G=Path('/mnt/raid0/llm/kernels/production/gpu')
TARGET='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
DRAFTER='/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'
TEMPLATE='/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja'
PORT=18453
STATS=re.compile(r'statistics\s+(draft-dflash|ngram-simple):\s+#calls\(b,g,a\)\s*=\s*\d+\s+\d+\s+(\d+),\s+#gen drafts\s*=\s*\d+,\s+#acc drafts\s*=\s*\d+,\s+#gen tokens\s*=\s*(\d+),\s+#acc tokens\s*=\s*(\d+)')
class Invalid(RuntimeError): pass

def stop_requested():
    return (Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=int(os.environ['FILLER_DEADLINE']))

def post(path,body,timeout=120):
    req=urllib.request.Request('http://127.0.0.1:'+str(PORT)+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def gpu_evidence(pid):
    maps=Path(f'/proc/{pid}/maps').read_text()
    pre=json.loads((BASE/'preflight.json').read_text())
    exe=Path(f'/proc/{pid}/exe').resolve(strict=True)
    if str(exe)!=pre['kernel'] or hashlib.sha256(exe.read_bytes()).hexdigest()!=pre['kernel_sha256']:
        raise Invalid('running server binary identity mismatch')
    pinned=json.loads((BASE/'store-binding.json').read_text())['files']
    mapped_paths={str(Path(line.split()[-1]).resolve()) for line in maps.splitlines() if len(line.split())>=6 and line.split()[-1].startswith('/')}
    for item in pinned:
        if item['map_required'] and str(Path(item['path']).resolve()) not in mapped_paths:
            raise Invalid('required production library not mapped: '+item['path'])
    actual=Path(G/'libggml-hip.so').resolve(strict=True)
    mapped={Path(line.split()[-1]).resolve() for line in maps.splitlines() if 'libggml-hip' in line and line.split()[-1].startswith('/')}
    st=actual.stat(); hip_pre=pre['hip_stat']
    if (str(actual)!=pre['hip'] or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)!=
            (hip_pre['dev'],hip_pre['ino'],hip_pre['size'],hip_pre['mtime_ns'])):
        raise Invalid('HIP backend identity mismatch')
    mapped_inodes={int(line.split()[4]) for line in maps.splitlines() if 'libggml-hip' in line and len(line.split())>=6}
    if mapped_inodes!={st.st_ino}: raise Invalid('mapped HIP inode mismatch')
    kfd=Path('/sys/class/kfd/kfd/proc')/str(pid)
    vram=sum(int(x.read_text()) for x in kfd.glob('vram_*'))
    if not mapped or mapped!={actual} or vram < int(os.path.getsize(TARGET)*.9):
        raise Invalid('HIP mapping or per-process VRAM insufficient')
    return {'pid':pid,'exe_path':str(exe),'exe_sha256':pre['kernel_sha256'],'hip_path':str(actual),'kfd_vram_bytes':vram,'observed_unix_ns':time.time_ns()}

def stats_from_response_and_log(response, log, arm):
    """Recover exact rounds only if all values in the rounding interval agree."""
    from decimal import Decimal, InvalidOperation
    t=response.get('timings'); slot=response.get('id_slot')
    if not isinstance(t,dict) or type(slot) is not int: raise Invalid('missing native timings or slot identity')
    drafted=t.get('draft_n'); accepted=t.get('draft_n_accepted')
    # The pinned v10 source serializes neither field and emits no acceptance
    # line when this fresh server's sole request generated zero proposals.
    # Never extrapolate this to a partial response, one missing field or a
    # response/log mismatch. The per-round mean is undefined for this case.
    zero_line = re.compile(r'slot print_timing:\s*id\s+' + str(slot) + r'\s*\|\s*task\s+\d+\s*\|\s*draft acceptance\s*=')
    if 'draft_n' not in t and 'draft_n_accepted' not in t:
        if response.get('stop') is not True or response.get('truncated') is not False or zero_line.search(log):
            raise Invalid('zero proposal response incomplete or contradicted by same-slot log')
        return {'draft_rounds':0,'drafted':0,'accepted':0,'mean_len_printed':None,
                'round_candidates':[],'slot_id':slot,'server_task_id':None,
                'derivation':'v10 zero-proposals response and no same-slot acceptance line; proposing-round mean undefined'}
    if type(drafted) is not int or type(accepted) is not int or drafted<1 or not 0<accepted<=drafted:
        raise Invalid('missing or ambiguous native draft/accept counts, including zero accepts')
    rx=re.compile(r'slot print_timing:\s*id\s+(\d+)\s*\|\s*task\s+(\d+)\s*\|\s*draft acceptance\s*=\s*[-+0-9.eE]+\s*\(\s*(\d+)\s+accepted\s*/\s*(\d+)\s+generated\s*\),\s*mean len\s*=\s*([0-9]+\.[0-9]{2})\s*$',re.M)
    matches=[m for m in rx.finditer(log) if int(m.group(1))==slot]
    if len(matches)!=1: raise Invalid('missing or ambiguous per-slot native acceptance line')
    m=matches[0]
    if int(m.group(3))!=accepted or int(m.group(4))!=drafted: raise Invalid('native log/response counter mismatch')
    try: mean=Decimal(m.group(5))
    except InvalidOperation: raise Invalid('malformed printed mean length')
    # Include both rounding endpoints plus a small safety margin. The log line
    # is formatted %.2f; a boundary tie may otherwise conceal another integer.
    epsilon=Decimal('0.005000001')
    candidates=[n for n in range(1,drafted+1) if abs(Decimal(1)+Decimal(accepted)/Decimal(n)-mean)<=epsilon]
    if len(candidates)!=1: raise Invalid('rounded mean does not uniquely identify positive round count')
    return {'draft_rounds':candidates[0], 'drafted':drafted, 'accepted':accepted,
            'mean_len_printed':str(mean), 'round_candidates':candidates,
            'slot_id':slot, 'server_task_id':int(m.group(2)),
            'derivation':'all positive integer rounds <= drafted consistent with inclusive %.2f rounding interval'}

def run_one(block,arm,task):
    if stop_requested(): raise Invalid('STOP or deadline before launch')
    out=ROOT/'out'/f"r{block['rep']}-{task['id']}-{arm}"; out.mkdir(parents=True,exist_ok=False)
    cmd=[str(G/'llama-server'),'-m',TARGET,'--host','127.0.0.1','--port',str(PORT),'-np','4','-c','16384','-ngl','99','-fa','on','-t','8','-tb','8','-b','2048','-ub','2048','-ctk','q8_0','-ctv','q8_0','--verbosity','4','--jinja','--chat-template-file',TEMPLATE]
    if arm=='current_dflash2': cmd+=['-md',DRAFTER,'-ngld','99','--spec-type','draft-dflash','--spec-draft-n-max','7']
    elif arm=='prompt_lookup': cmd+=['--spec-type','ngram-simple']
    elif arm!='plain': raise Invalid('unknown arm')
    cpus=os.environ.get('FILLER_CPUS'); cmd=(['taskset','-c',cpus]+cmd) if cpus else cmd
    (out/'argv.json').write_text(json.dumps(cmd)+'\n')
    log=open(out/'server.log','w'); proc=spawn_session(cmd,stdout=log,stderr=log,env={**os.environ,'LD_LIBRARY_PATH':str(G),'HIP_VISIBLE_DEVICES':os.environ.get('HIP_VISIBLE_DEVICES','0')},cwd=str(ROOT))
    if os.environ.get('FILLER_PIDFILE'):
        with open(os.environ['FILLER_PIDFILE'],'a') as f: f.write(str(proc.pid)+'\n')
    samples=[]; ev=threading.Event(); errors=[]
    def monitor():
        while not ev.wait(.2):
            try: samples.append(gpu_evidence(proc.pid))
            except Exception as e: errors.append(str(e))
    th=None
    try:
        deadline=min(time.time()+600,int(os.environ['FILLER_DEADLINE']))
        while time.time()<deadline:
            if stop_requested() or proc.poll() is not None: raise Invalid('STOP or server exited before ready')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=2) as r:
                    if r.status==200: break
            except Exception: pass
            time.sleep(1)
        else: raise Invalid('server health timeout')
        before=gpu_evidence(proc.pid)
        prompt=task['native_rendered_prompt']
        request={'prompt':prompt,'n_predict':512,'temperature':0.0,'top_k':1,'seed':42,'cache_prompt':False,'return_tokens':True}
        (out/'request.json').write_text(json.dumps(request)+'\n')
        th=threading.Thread(target=monitor,daemon=True); th.start(); start=time.time_ns()
        box={}; completed=threading.Event()
        def invoke():
            try: box['response']=post('/completion',request,timeout=900)
            except Exception as e: box['error']=str(e)
            finally: completed.set()
        req_thread=threading.Thread(target=invoke,daemon=True); req_thread.start()
        while not completed.wait(.2):
            if stop_requested() or proc.poll() is not None: raise Invalid('STOP, deadline or server exit in request')
        end=time.time_ns(); ev.set(); th.join(timeout=5)
        if 'error' in box: raise Invalid('request failed: '+box['error'])
        response=box['response']
        if response.get('stop') is not True or response.get('truncated') is not False or response.get('stop_type') not in ('eos','word'):
            raise Invalid('response incomplete, truncated, or ended at token limit')
        in_window=[x for x in samples if start<=x['observed_unix_ns']<=end]
        (out/'response.json').write_text(json.dumps(response)+'\n'); (out/'residency.json').write_text(json.dumps({'before':before,'window':in_window,'errors':errors,'start_ns':start,'end_ns':end})+'\n')
        if len(in_window)<2 or errors: raise Invalid('fewer than two clean in-request residency samples')
        timings=response.get('timings',{}); speed=timings.get('predicted_per_second')
        if type(speed) not in (int,float) or speed<=0 or not isinstance(response.get('tokens'),list) or not response['tokens']:
            raise Invalid('missing decoded tokens or timings')
        from verifier import verify
        correctness=verify(task,response.get('content'))
        (out/'edit-validity.json').write_text(json.dumps(correctness)+'\n')
        if correctness.get('status') != 'PASS': raise Invalid('synthetic edit verifier failed or unknown')
        result={'rep':block['rep'],'task':task['id'],'arm':arm,'status':'ok','temperature':0,'fresh_server':True,'gpu_residency':True,'decode_tps':speed,'edit_validity':correctness['status'],'native_response_path':str(out/'response.json')}
    finally:
        ev.set()
        if th: th.join(timeout=5)
        try: drain_session(proc,grace_seconds=10)
        finally: log.close()
    result['native_sha256']={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('argv.json','request.json','response.json','residency.json','edit-validity.json','server.log')}
    result['plan_sha256']=hashlib.sha256((BASE/'candidate-plan.json').read_bytes()).hexdigest()
    result['corpus_sha256']=hashlib.sha256((BASE/'corpus.json').read_bytes()).hexdigest()
    result['runtime_manifest_sha256']=hashlib.sha256((BASE/'runtime.sha256').read_bytes()).hexdigest()
    if arm!='plain':
        native_log=(out/'server.log').read_text(errors='replace')
        marker="adding speculative implementation '" + ('draft-dflash' if arm=='current_dflash2' else 'ngram-simple') + "'"
        if marker not in native_log: raise Invalid('requested speculative implementation not proven active')
        result.update(stats_from_response_and_log(response,native_log,arm))
        if os.environ.get('FILLER_DRYRUN')=='1' and (arm!='current_dflash2' or result['drafted']<=0):
            raise Invalid('smoke must capture positive DFlash proposals')
    return result

def main():
    from analysis import analyze_sr8
    plan=json.loads((BASE/'candidate-plan.json').read_text())
    corpus={x['id']:x for x in json.loads((BASE/'corpus.json').read_text())}
    tasks={}
    for p in plan['tasks']:
        t=corpus[p['id']]
        if p['prompt'] != t['prompt'] or p['files'] != t['files']:
            raise Invalid('plan/corpus input mismatch')
        tasks[p['id']]={**t, 'native_rendered_prompt':p['native_rendered_prompt']}
    rows=[]; started=time.time_ns()
    (ROOT/'out').mkdir(parents=True,exist_ok=True)
    try:
        if len(plan['schedule']) != 5 or any(set(b['arms'])!={'plain','current_dflash2','prompt_lookup'} for b in plan['schedule']):
            raise Invalid('invalid predeclared schedule')
        for block in plan['schedule']:
            task=tasks[block['task']]
            for arm in block['arms']:
                result=run_one(block,arm,task)
                rows.append(result)
                with open(ROOT/'out'/'observations.jsonl','a') as f:
                    f.write(json.dumps(result)+'\n'); f.flush(); os.fsync(f.fileno())
                if os.environ.get('FILLER_DRYRUN')=='1':
                    smoke=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
                    smoke.parent.mkdir(parents=True,exist_ok=True)
                    smoke.write_text(json.dumps({'state':'SMOKE_ONE_REQUEST','observation':result})+'\n')
                    while not stop_requested(): time.sleep(.2)
                    return 75
        x=analyze_sr8(rows,plan['schedule'])
        result={'state':'COMPLETE','analysis':x,'started_unix_ns':started,'finished_unix_ns':time.time_ns(),
                'limitations':['edit validity is measured by new synthetic multi-file verifier; not the canonical BEP corpus','native evidence not yet independently authenticated',
                               'native rendered prompt token repetition and formatter are pinned in candidate-plan.json','no automatic route change']}
        (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
        return 0
    except Exception as e:
        (ROOT/'RESULT.json').write_text(json.dumps({'state':'UNKNOWN','error':type(e).__name__+': '+str(e),'completed':len(rows)})+'\n')
        return 1

if __name__=='__main__': raise SystemExit(main())

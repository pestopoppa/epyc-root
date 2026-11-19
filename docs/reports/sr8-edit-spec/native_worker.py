#!/usr/bin/env python3
"""Candidate SR-8 GPU worker; fail closed on missing runtime evidence.

This file is not a qualified launcher until the model preflight, admission,
process-tree supervision, smoke and writer integration are bound by the row.
"""
import ast, hashlib, json, os, re, signal, subprocess, threading, time, urllib.request
from session_drain import spawn_session, drain_session
from pathlib import Path

BASE=Path(os.environ.get('SR8_ROOT','/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-edit-spec'))
ROOT=(BASE/'smoke'/hashlib.sha256(os.environ.get('FILLER_DRYRUN_RESULT_PATH','missing').encode()).hexdigest()[:16] if os.environ.get('FILLER_DRYRUN')=='1' else BASE/'live')
G=Path('/mnt/raid0/llm/kernels/production/gpu')
TARGET='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
DRAFTER='/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'
TEMPLATE='/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja'
PORT=18431
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
    for model in pre['models']:
        m=os.stat(model['path'])
        if (m.st_dev,m.st_ino,m.st_size,m.st_mtime_ns)!=(model['dev'],model['ino'],model['size'],model['mtime_ns']):
            raise Invalid('preflighted model identity changed')
    exe=Path(f'/proc/{pid}/exe').resolve(strict=True)
    if str(exe)!=pre['kernel'] or hashlib.sha256(exe.read_bytes()).hexdigest()!=pre['kernel_sha256']:
        raise Invalid('running server binary identity mismatch')
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

def stats_from_log(log,arm):
    matches=[m for m in STATS.finditer(log) if m.group(1)==('draft-dflash' if arm=='current_dflash2' else 'ngram-simple')]
    if len(matches)!=1: raise Invalid('missing or ambiguous per-request speculation statistics')
    rounds,drafted,accepted=map(int,matches[0].groups()[1:])
    if rounds<1 or accepted>drafted or drafted<rounds: raise Invalid('invalid speculation counts')
    return rounds,drafted,accepted

def check_structure(task_id, content):
    expected={'t2_add_and_use':({'calc.py','main.py'},set()),
              't3_method_and_caller':({'shapes.py','report.py'},set()),
              't4_rename_module':({'utils.py','app.py'},{'helpers.py'}),
              't5_bugfix':({'tax.py'},set())}
    if task_id not in expected or not isinstance(content,str): return {'status':'STRUCTURE_UNKNOWN'}
    files=re.findall(r'<<<FILE:\s*([^>]+?)>>>\s*\n(.*?)\n<<<END>>>',content,re.S)
    deletes=re.findall(r'<<<DELETE:\s*([^>]+?)>>>',content)
    names=[name.strip() for name,_ in files]; deletions=[name.strip() for name in deletes]
    ok=(len(names)==len(set(names)) and len(deletions)==len(set(deletions)) and
        set(names)==expected[task_id][0] and set(deletions)==expected[task_id][1] and
        all(body.strip() for _,body in files))
    return {'status':'STRUCTURE_PASS' if ok else 'STRUCTURE_FAIL','files':names,'deletions':deletions,
            'contents':dict(files) if ok else {},'scope':'expected full-file envelope only'}

def run_fixture(task,structure,out):
    """Inspect source and execute the canonical fixed verifier in one task fixture."""
    if structure['status']!='STRUCTURE_PASS': return {'status':'FAIL','reason':'output structure'}
    files=structure['contents']
    local_modules={Path(p).stem for p in files}
    forbidden=(ast.While,ast.For,ast.AsyncFor,ast.With,ast.AsyncWith,ast.Try,ast.Raise,
               ast.Lambda,ast.Global,ast.Nonlocal,ast.AsyncFunctionDef,ast.Await,ast.Yield,ast.YieldFrom)
    dangerous={'eval','exec','compile','open','__import__','input','breakpoint','globals','locals','vars','getattr','setattr','delattr'}
    try:
        for name,body in files.items():
            if '/' in name or name in ('.','..') or not name.endswith('.py'): raise Invalid('unsafe generated path')
            tree=ast.parse(body,filename=name)
            for node in ast.walk(tree):
                if isinstance(node,forbidden): raise Invalid('disallowed generated control construct')
                if isinstance(node,ast.Import): raise Invalid('generated direct import not admitted')
                if isinstance(node,ast.ImportFrom) and (node.level or node.module not in local_modules): raise Invalid('external import')
                if isinstance(node,ast.Name) and (node.id in dangerous or (node.id.startswith('__') and node.id!='__init__')): raise Invalid('unsafe identifier')
                if isinstance(node,ast.Attribute) and node.attr.startswith('__'): raise Invalid('dunder access')
        fixture=out/'fixture'; fixture.mkdir()
        for name,body in task['files'].items(): (fixture/name).write_text(body)
        for name in structure['deletions']: (fixture/name).unlink(missing_ok=True)
        for name,body in files.items(): (fixture/name).write_text(body)
        env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','HOME':str(fixture),'LANG':'C.UTF-8'}
        with open(out/'verifier.stdout','w') as stdout,open(out/'verifier.stderr','w') as stderr:
            child=spawn_session(['/bin/sh','-c',task['verifier_cmd']],stdout=stdout,stderr=stderr,env=env,cwd=str(fixture))
            try: rc=child.wait(timeout=15)
            except subprocess.TimeoutExpired: rc=None
            finally: drain_session(child,grace_seconds=5)
        return {'status':'PASS' if rc==0 and 'PASS' in (out/'verifier.stdout').read_text() else 'FAIL',
                'rc':rc,'scope':'canonical BEP verifier after source inspection; one isolated task directory'}
    except (SyntaxError,Invalid,OSError,subprocess.SubprocessError) as exc:
        return {'status':'UNKNOWN','reason':str(exc),'scope':'canonical verifier not completed'}

def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def capture_native_record(result,out,grant_path,grant_hash):
    """Write contemporaneous source facts; this is not a graded ClaimTuple."""
    if sha_file(grant_path)!=grant_hash: raise Invalid('grant changed during request')
    plan_path=BASE/'candidate-plan.json'; pre_path=BASE/'preflight.json'
    plan=json.loads(plan_path.read_text()); pre=json.loads(pre_path.read_text())
    paths={k:out/v for k,v in {'request':'request.json','template_request':'template-request.json',
           'response':'response.json','native_stats':'server.log','residency':'residency.json',
           'edit_structure':'edit-structure.json','edit_validity':'edit-validity.json'}.items()}
    artifacts={k:{'path':str(v),'sha256':sha_file(v)} for k,v in paths.items()}
    record={'schema':'epyc.sr8.native-observation.v1','capture_unix_ns':time.time_ns(),
            'mode':'smoke' if os.environ.get('FILLER_DRYRUN')=='1' else 'granted',
            'plan':{'path':str(plan_path),'sha256':sha_file(plan_path),'corpus_sha256':plan['corpus_sha256'],
                    'source_repo_head':plan['source_repo_head'],'rendering_source_sha256':plan['rendering_source_sha256']},
            'preflight':{'path':str(pre_path),'sha256':sha_file(pre_path),'models':pre['models'],
                         'kernel':pre['kernel'],'kernel_sha256':pre['kernel_sha256'],
                         'hip':pre['hip'],'hip_sha256':pre['hip_sha256']},
            'producer':{'path':str(Path(__file__).resolve()),'sha256':sha_file(__file__),
                        'analysis_sha256':sha_file(BASE/'analysis.py'),'drain_sha256':sha_file(BASE/'session_drain.py')},
            'grant':{'path':str(grant_path),'sha256':grant_hash},'native_artifacts':artifacts,
            'metrics':result,'limitations':['native record only; no retrospective measurement warrant or grading',
                  'model hashes taken before grant; model metadata and loaded identities verified during run']}
    path=out/'native-record.json'; temp=out/'.native-record.tmp'
    with open(temp,'w') as f: json.dump(record,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)
    return {'path':str(path),'sha256':sha_file(path)}

def run_one(block,arm,task):
    if stop_requested(): raise Invalid('STOP or deadline before launch')
    grant_path=Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/(os.environ['FILLER_ID']+'.grant')
    if grant_path.is_symlink() or not grant_path.is_file(): raise Invalid('missing regular grant')
    grant_hash=sha_file(grant_path)
    out=ROOT/'out'/f"r{block['rep']}-{task['id']}-{arm}"; out.mkdir(parents=True,exist_ok=False)
    cmd=[str(G/'llama-server'),'-m',TARGET,'--host','127.0.0.1','--port',str(PORT),'-np','4','-c','16384','-ngl','99','-fa','on','-t','8','-tb','8','-b','2048','-ub','2048','-ctk','q8_0','-ctv','q8_0','--jinja','--chat-template-file',TEMPLATE]
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
        template_req={'messages':[{'role':'user','content':task['rendered_prompt']}], 'chat_template_kwargs':{'enable_thinking':True,'reasoning_effort':'medium'}}
        template=post('/apply-template',template_req)
        prompt=template.get('prompt')
        if not isinstance(prompt,str) or not prompt: raise Invalid('missing rendered chat prompt')
        request={'prompt':prompt,'n_predict':512,'temperature':0.0,'top_k':1,'seed':42,'cache_prompt':False,'return_tokens':True}
        (out/'template-request.json').write_text(json.dumps(template_req)+'\n'); (out/'request.json').write_text(json.dumps(request)+'\n')
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
        in_window=[x for x in samples if start<=x['observed_unix_ns']<=end]
        (out/'response.json').write_text(json.dumps(response)+'\n'); (out/'residency.json').write_text(json.dumps({'before':before,'window':in_window,'errors':errors,'start_ns':start,'end_ns':end})+'\n')
        if len(in_window)<2 or errors: raise Invalid('fewer than two clean in-request residency samples')
        timings=response.get('timings',{}); speed=timings.get('predicted_per_second')
        if type(speed) not in (int,float) or speed<=0 or not isinstance(response.get('tokens'),list) or not response['tokens']:
            raise Invalid('missing decoded tokens or timings')
        structure=check_structure(task['id'],response.get('content'))
        (out/'edit-structure.json').write_text(json.dumps(structure)+'\n')
        correctness=run_fixture(task,structure,out)
        (out/'edit-validity.json').write_text(json.dumps(correctness)+'\n')
        result={'rep':block['rep'],'task':task['id'],'arm':arm,'status':'ok','temperature':0,'fresh_server':True,'gpu_residency':True,'decode_tps':speed,'edit_validity':correctness['status'],'native_response_path':str(out/'response.json')}
    finally:
        ev.set()
        if th: th.join(timeout=5)
        try: drain_session(proc,grace_seconds=10)
        finally: log.close()
    if arm!='plain':
        result['draft_rounds'],result['drafted'],result['accepted']=stats_from_log((out/'server.log').read_text(errors='replace'),arm)
    result['native_capture']=capture_native_record(result,out,grant_path,grant_hash)
    return result

def main():
    from analysis import analyze_sr8
    plan=json.loads((BASE/'candidate-plan.json').read_text())
    tasks={x['id']:x for x in plan['tasks']}; rows=[]; started=time.time_ns()
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
        x=analyze_sr8(rows)
        result={'state':'COMPLETE','analysis':x,'started_unix_ns':started,'finished_unix_ns':time.time_ns(),
                'limitations':['edit validity is measured by fixed BEP verifier after conservative source inspection','native evidence not yet independently authenticated',
                               'rendered-token 5-gram fraction not established','no automatic route change']}
        (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
        return 0
    except Exception as e:
        (ROOT/'RESULT.json').write_text(json.dumps({'state':'UNKNOWN','error':type(e).__name__+': '+str(e),'completed':len(rows)})+'\n')
        return 1

if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
"""Same native routes for the disjoint control and frozen paired pilot."""
import argparse, hashlib, json, os, signal, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
import control_driver as c
import split_storage
from paired_journal import create, encoded
from sealed_journal import invoke_cell, DECL, MANIFEST
from natural_qualification import inspect_control, event_qualification
from partial_assessment import assess as assess_partial
from prompt_projection import project
from source_closure import verify as verify_local_source

D=Path(__file__).resolve().parent
ARMS=('production_repl','redel_delegate_wait')
SOURCE=Path('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-prep-20261030/qa_rl.parquet')

def identities():
    verify_local_source()
    for line in (D/'CAMPAIGN-SOURCES.sha256').read_text().splitlines():
        expected,name=line.split('  ',1)
        if c.sha(Path(name))!=expected: raise RuntimeError('source drift: '+name)
    dec=json.loads((D/'PREDECLARATION-FROZEN.json').read_bytes())
    if c.sha(D/'PREDECLARATION-FROZEN.json')!=DECL: raise RuntimeError('declaration drift')
    if str(c.MODEL)!=dec['model_path']: raise RuntimeError('model path mismatch')
    if c.sha(SOURCE)!=dec['source_sha256']: raise RuntimeError('dataset drift')
    if c.sha(c.MODEL)!=dec['model_sha256'] or c.sha(c.BIN)!='2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b': raise RuntimeError('model/kernel drift')
    return dec

def rows(dec,smoke):
    if smoke: return [json.loads((D/'CONTROL-PRIVATE.json').read_bytes())]
    # Source rows were extracted and hash-checked before exposure. Serving
    # requires no dataset reader dependency or access to the Arrow corpus.
    private=json.loads((D/'PILOT-PRIVATE.json').read_bytes())
    if private['source_sha256']!=dec['source_sha256']: raise RuntimeError('dataset identity')
    selected=[]
    for row,entry in zip(private['rows'],dec['pilot'],strict=True):
        if hashlib.sha256(encoded(row)).hexdigest()!=entry['row_sha256']: raise RuntimeError('row drift')
        selected.append(row)
    return selected

def cell_state(journal,row,arm):
    key=hashlib.sha256(encoded({'campaign_sha256':DECL,'id':row['id'],'arm':arm})).hexdigest()
    if (journal/(key+'.end')).exists(): return 'complete'
    return 'unknown' if (journal/(key+'.start')).exists() else 'missing'

def pilot_delegation_verdict(journal, selected):
    matched=0
    for row in selected:
        key=hashlib.sha256(encoded({'campaign_sha256':DECL,'id':row['id'],'arm':'redel_delegate_wait'})).hexdigest()
        rec=json.loads((journal/(key+'.end')).read_bytes())
        identity={'campaign_sha256':DECL,'id':row['id'],'arm':'redel_delegate_wait','prompt_sha256':hashlib.sha256(project(row).encode()).hexdigest()}
        if rec.get('status')!='complete' or rec.get('identity')!=identity or rec.get('start_sha256')!=hashlib.sha256((journal/(key+'.start')).read_bytes()).hexdigest():
            raise ValueError('incomplete pilot journal')
        matched+=bool(event_qualification(rec['native']['native_events']))
    return {'verdict':'INCONCLUSIVE_NO_DELEGATION' if matched==0 else 'DELEGATION_OBSERVED_EVALUATION_PENDING','delegation_positive_cases':matched,'total_cases':len(selected),'step3_gate_passed':False}

def inspect_wire_capture(path):
    files=sorted(path.glob('*.json'))
    if not files:raise ValueError('no captured ReDel request')
    first=json.loads(files[0].read_bytes())
    names=[t.get('function',{}).get('name') for t in first.get('tools',[])]
    if names!=['delegate','wait'] or first.get('tool_choice') not in (None,'auto'):
        raise ValueError('tool serialization missing or forced')
    return {'requests':len(files),'first_tools':names,'tool_choice':first.get('tool_choice'),'first_wire_sha256':hashlib.sha256(files[0].read_bytes()).hexdigest()}

def pilot_completion_allowed(partial, failure, server_drained, assessment):
    return (not partial and failure is None and server_drained is True and isinstance(assessment,dict)
            and assessment.get('verdict') in ('INCONCLUSIVE_NO_DELEGATION','DELEGATION_OBSERVED_EVALUATION_PENDING')
            and assessment.get('step3_gate_passed') is False)

def start_server(cmd,env,log,filecap,*,smoke,output_root,other):
    if not c.headroom(other):raise RuntimeError('split-storage floor before model load')
    if smoke:
        create(D/'CONTROL-EXPOSURE-START.json',{'source_sha256':c.sha(D/'CAMPAIGN-SOURCES.sha256'),'declaration_sha256':DECL,'ram_root':str(output_root),'state':'reserved before model load'})
    return subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=filecap)

def control_output_root(smoke):
    if not smoke:
        root=Path('/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030/pilot');root.mkdir(mode=0o700,exist_ok=True);return root
    root=Path('/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030/control')
    if os.environ.get('EVL34_CONTROL_RAM_ROOT')!=str(root) or not root.is_dir() or root.is_symlink():raise RuntimeError('invalid control RAM root')
    return root

def configure_control_environment(root):
    tmp=root/'tmp';tmp.mkdir(mode=0o700,exist_ok=True)
    os.environ.update(TMPDIR=str(tmp),XDG_CACHE_HOME=str(root/'cache'),HF_HOME=str(root/'hf'))
    tempfile.tempdir=str(tmp)

def server_environment(root,smoke):
    env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(c.BIN.parent),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    env.update(TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),HF_HOME=str(root/'hf'))
    return env

def extra_headroom(smoke):
    value=0 if smoke else int(os.environ.get('EVL34_EXTRA_HEADROOM_BYTES','0'))
    if value<0:raise ValueError('negative reservation')
    return value

def main():
    a=argparse.ArgumentParser(); a.add_argument('--smoke',action='store_true'); args=a.parse_args()
    dec=identities()
    manifest=json.loads((D/'FROZEN-PROMPT-MANIFEST.json').read_bytes())
    if c.sha(D/'FROZEN-PROMPT-MANIFEST.json')!=MANIFEST: raise RuntimeError('manifest drift')
    if not args.smoke:
        from entry_qualification import verify
        try:verify(DECL,c.sha(D/'CAMPAIGN-SOURCES.sha256'))
        except Exception as exc:raise RuntimeError('pilot refused: entry qualification invalid') from exc
    selected=rows(dec,args.smoke)
    original_credentials=c.credential_paths
    c.credential_paths=lambda:original_credentials()+[str(D/'PILOT-PRIVATE.json')]
    other=extra_headroom(args.smoke)
    c.OWN_RESERVE=128*1024**2
    output_root=control_output_root(args.smoke)
    configure_control_environment(output_root)
    c.OUTPUT_STOP=512*1024**2
    if not c.headroom(other): raise RuntimeError('disk floor plus concurrent reservations')
    deadline=time.monotonic()+240 if args.smoke else time.monotonic()+max(0,float(os.environ['FILLER_DEADLINE'])-time.time()-30)
    c.END=deadline
    c.PORT=19987
    if c.PORT!=dec['server_port']: raise RuntimeError('port mismatch')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',c.PORT))
    journal=output_root/('control-journal' if args.smoke else 'pilot-journal')
    # Refuse re-exposure, including an unknown previous control attempt.
    if args.smoke and any(cell_state(journal,row,arm)!='missing' for row in selected for arm in ARMS): raise RuntimeError('control already exposed')
    attempt=output_root/(('campaign-control-' if args.smoke else 'campaign-pilot-')+str(time.time_ns())); attempt.mkdir()
    grant=None if args.smoke else Path('/mnt/raid0/llm/tmp/compute-flags/grants',os.environ['FILLER_ID']+'.grant').read_text()
    create(attempt/'capture.json',{'smoke':args.smoke,'source_sha256':c.sha(D/'CAMPAIGN-SOURCES.sha256'),'declaration_sha256':DECL,'grant':grant,'started_utc':time.time(),'model_sha256':dec['model_sha256']})
    os.environ['EVL34_GPU_WITNESS_LOG']=str(attempt/'gpu-witness.jsonl')
    # Include all retained campaign evidence and the shared server log in the
    # sampled budget checked by each native arm, rather than one cell alone.
    count_bytes=c.output_bytes
    c.output_bytes=lambda _root:count_bytes(output_root) if args.smoke else count_bytes(attempt)+count_bytes(journal)
    env=server_environment(output_root,args.smoke)
    server=None; statuses={}; failure=None; qualification=None; entry_seen=False; repl_entry_seen=False
    try:
        with (attempt/'linkage.log').open('xb') as log:
            subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(c.BIN),str(c.BIN.parent)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=10)
        with (attempt/'server.log').open('xb') as log:
            cpus=sorted(os.sched_getaffinity(0)); threads=len(cpus)
            cmd=[str(c.BIN),'-m',str(c.MODEL),'-a','pinned','--host','127.0.0.1','--port',str(c.PORT),'-c','49152','-np','3','-t',str(threads),'-tb',str(threads),'-ngl','99','--jinja','--chat-template-kwargs','{"enable_thinking":false}']
            def filecap(): c.resource.setrlimit(c.resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
            server=start_server(cmd,env,log,filecap,smoke=args.smoke,output_root=output_root,other=other); birth=c.birth(server.pid)
            create(attempt/'SERVER.json',{'pid':server.pid,'birth_ticks':birth,'argv':cmd,'ld_library_path':env['LD_LIBRARY_PATH']})
            while not c.stopped():
                if server.poll() is not None: raise RuntimeError('server exited')
                if c.listening(server.pid,c.PORT):
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{c.PORT}/health',timeout=1) as response: healthy=json.load(response).get('status')=='ok'
                        if healthy: break
                    except (OSError,ValueError): pass
                time.sleep(.1)
            else: raise TimeoutError('startup cutoff')
            for i,row in enumerate(selected):
                order=ARMS if args.smoke or i%2==0 else ARMS[::-1]
                for arm in order:
                    key=row['id']+'/'+arm; state=cell_state(journal,row,arm)
                    if state=='unknown': statuses[key]='unknown'; continue
                    if state=='missing' and (c.stopped() or time.monotonic()+(0 if args.smoke else 930)>=deadline): statuses[key]='missing'; continue
                    c.END=min(deadline,time.monotonic()+900)
                    verify_local_source()  # Revalidate the pinned readset before each new exposure.
                    cell=attempt/(str(i)+'-'+arm); cell.mkdir()
                    try:
                        invoke_cell(journal,row,arm,'control' if args.smoke else 'pilot',lambda payload:c.run_arm(arm,payload['prompt'],cell,server,birth,other,capture_request=arm=='redel_delegate_wait',milestone=args.smoke))
                        statuses[key]='complete'
                    except Exception as exc:
                        statuses[key]=cell_state(journal,row,arm)
                        if args.smoke and arm=='production_repl' and isinstance(exc,ValueError) and str(exc)=='native result lacks completed route and flat-server bound' and statuses[key]=='unknown':
                            repl_entry_seen=True
                        elif args.smoke and arm=='redel_delegate_wait' and isinstance(exc,ValueError) and str(exc)=='native result lacks completed route and flat-server bound':
                            if statuses[key]!='unknown':raise
                            qualification={'qualified':True,'scope':'entry-only','redel_first_response':True}
                            entry_seen=True
                        else:
                            create(cell/'FAILURE.json',{'reason':type(exc).__name__+': '+str(exc),'state':statuses[key]})
                            if args.smoke: raise
                    c.END=deadline
    except BaseException as exc:
        failure=type(exc).__name__+': '+str(exc)
    finally:
        c.stop_child(server)
        for row in selected:
            for arm in ARMS: statuses.setdefault(row['id']+'/'+arm,cell_state(journal,row,arm))
        partial=any(v!='complete' for v in statuses.values())
        wire=None; pilot_result=None
        if args.smoke and entry_seen and (repl_entry_seen or statuses.get(str(selected[0]['id'])+'/production_repl')=='complete'):
            try:wire=inspect_wire_capture(attempt/'0-redel_delegate_wait/redel_delegate_wait/outbound-requests')
            except Exception as exc:failure='wire_capture: '+type(exc).__name__+': '+str(exc)
        if not args.smoke:
            try: pilot_result=assess_partial(journal,attempt,DECL,selected,manifest['pilot'])
            except Exception as exc: failure='partial_assessment: '+type(exc).__name__+': '+str(exc)
        result={'qualification':qualification,'wire_capture':wire,'pilot_assessment':pilot_result,'schema':'evl34-native-paired/v1','smoke':args.smoke,'partial':partial,'statuses':statuses,'failure':failure,'server_drained':server is None or server.poll() is not None,'source_sha256':c.sha(D/'CAMPAIGN-SOURCES.sha256')}
        create(attempt/'result.json',result)
        if not args.smoke and pilot_completion_allowed(partial,failure,result['server_drained'],pilot_result) and not (D/'PILOT-DONE.json').exists(): create(D/'PILOT-DONE.json',result)
        print(json.dumps({'attempt':str(attempt),**result}),flush=True)
    if args.smoke and entry_seen and (repl_entry_seen or statuses.get(str(selected[0]['id'])+'/production_repl')=='complete') and failure is None and result['server_drained'] and wire:return 0
    if not partial and (failure is not None or not result['server_drained']):return 78
    if not args.smoke and not partial and not pilot_completion_allowed(partial,failure,result['server_drained'],pilot_result):return 78
    if partial and not args.smoke and all(v in ('complete','unknown') for v in statuses.values()): return 78
    return 75 if partial else 0

if __name__=='__main__': sys.exit(main())

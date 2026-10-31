#!/usr/bin/env python3
"""One original-process HIL15b-v2 attempt, with terminal no-redraw accounting."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

D=Path(__file__).resolve().parent
APP='/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator'
ROOT='/mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030'
PY='/workspace/repos/epyc-orchestrator/.venv/bin/python'
MODEL='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
TASK_SHA='0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312'


def atomic(path,data):
    with tempfile.NamedTemporaryFile('w',dir=path.parent,prefix=path.name+'.',delete=False) as f:
        tmp=Path(f.name);json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def account(out,mode,entry_rc,reason,wall_s):
    ledger=out/'native-attempts.jsonl'
    events=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
    ids=[e['run_id'] for e in events if e.get('event')=='intent']
    native_manifest=out/'native/manifest.json'
    m=json.loads(native_manifest.read_text()) if native_manifest.exists() else None
    if mode=='qualification':
        ok=entry_rc==0 and m and m.get('verdict')=='OK' and len(m.get('runs',[]))==1 \
            and m.get('join',{}).get('joined_outcome')==1 and all(v['rc']==0 for v in m.get('replay_verify',{}).values())
        result={'schema':'hil15b_v2_qualification/v1','scope':'noncohort; no HIL15b quality claim',
                'entry_rc':entry_rc,'native_verdict':m.get('verdict') if m else None,
                'first_request_ok':bool(ids),'result_writer_ok':bool(ok),'exit_ok':bool(ok),
                'wall_s':wall_s,'reason':reason,'partial':not bool(ok)}
        atomic(out/'ASSESSMENT.json',result)
        return 0 if ok else 75
    tasks=json.loads((D/'hil15b_v2_tasks.json').read_text())
    expected=[f"{t['task_key']}-r{i}" for i in range(3) for t in tasks]
    if len(expected)!=60 or len(set(expected))!=60 or len(ids)!=len(set(ids)) or any(x not in expected for x in ids):
        raise RuntimeError('frozen attempt identity violation')
    marker=out/'COHORT-EXPOSED.json'
    if marker.exists() and json.loads(marker.read_text())['first_run_id'] not in ids:
        ids=[json.loads(marker.read_text())['first_run_id']]+ids
    ids=list(dict.fromkeys(ids))
    complete=[]
    if m and m.get('verdict')=='OK':
        complete=[r['run_id'] for r in m.get('runs',[])]
        if complete!=expected[:len(complete)] or m.get('join',{}).get('task_runs')!=len(complete) \
           or m.get('join',{}).get('joined_outcome')!=len(complete) \
           or any(m.get('replay_verify',{}).get(r,{}).get('rc')!=0 for r in complete):
            complete=[]
    full=entry_rc==0 and len(complete)==60 and ids==expected
    result={'schema':'hil15b_v2_original_single_process/v1','frozen_taskset_sha256':TASK_SHA,
            'original_attempts':60,'native_driver_sha256':'75abff0842a550051b3a25f3bf079a505044120a9ee57e80cc08ef2661bb4c63',
            'native_entry_rc':entry_rc,'native_verdict':m.get('verdict') if m else None,
            'complete':len(complete),'exposed_incomplete_unknown':len(ids)-len(complete),
            'unexposed':60-len(ids),'partial':not full,'full_original_denominator':full,
            'state':'full_measured' if full else ('terminal_inconclusive_no_redraw' if marker.exists()
                   else 'unexposed_preflight_retryable'),
            'reason':reason,'wall_s':wall_s,'quality_verdict':None,
            'client_scope':'one canonical native main/run_all/live_deps process; no per-slot client reset',
            'exposed_run_ids':ids,'complete_run_ids':complete}
    if full:
        cal={t['task_key'] for t in json.loads((D/'calibration_tasks.json').read_text())}
        held={t['task_key'] for t in json.loads((D/'heldout_tasks.json').read_text())}
        passes={t['task_key']:[] for t in tasks}
        for row in m['runs']:passes[row['task_key']].append(bool(row['pass']))
        def group(keys):
            seq=[v for k in keys for v in passes[k]]
            return {'tasks':len(keys),'attempts':len(seq),'passes':sum(seq),'failures':len(seq)-sum(seq)}
        band=sum(1 for seq in passes.values() if sum(seq) in (1,2))
        result.update(calibration=group(cal),heldout=group(held),total=group(cal|held),
                      per_task={k:{'passes':sum(v),'rate_3':sum(v)/3} for k,v in passes.items()},
                      variance_tasks=band,band_16_to_20=(band>=16),
                      global_auc_table=m.get('auc_table'),
                      quality_verdict='band pass' if band>=16 else 'band miss')
    atomic(out/'ASSESSMENT.json',result)
    return 0 if full else 75


def terminate(proc):
    if proc.poll() is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
    ps=subprocess.run(['ps','-e','-o','pid=,pgid=,stat='],capture_output=True,text=True,check=True)
    live=[int(x[0]) for line in ps.stdout.splitlines() if len(x:=line.split())>=3
          and int(x[1])==proc.pid and not x[2].startswith('Z')]
    if live:
        os.killpg(proc.pid,signal.SIGKILL)
        time.sleep(.2)
        ps=subprocess.run(['ps','-e','-o','pid=,pgid=,stat='],capture_output=True,text=True,check=True)
        live=[int(x[0]) for line in ps.stdout.splitlines() if len(x:=line.split())>=3
              and int(x[1])==proc.pid and not x[2].startswith('Z')]
    if live:raise RuntimeError(f'captured native process group not drained: {live}')


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('full','qualification'))
    p.add_argument('--out-dir',required=True);p.add_argument('--server-url',required=True)
    p.add_argument('--server-pid',type=int,required=True);p.add_argument('--deadline-epoch',type=int,required=True)
    a=p.parse_args();out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    if a.mode=='full' and (out/'COHORT-EXPOSED.json').exists():
        if not (out/'ASSESSMENT.json').exists():account(out,'full',75,'prior exposed call; no redraw',0)
        print('terminal frozen cohort already exposed; no second native call')
        return 0
    if hashlib.sha256((D/'hil15b_v2_tasks.json').read_bytes()).hexdigest()!=TASK_SHA:raise SystemExit('taskset drift')
    source=subprocess.run(['/usr/bin/python3',str(D/'verify_source.py')],capture_output=True,text=True)
    if source.returncode:raise SystemExit('functional APP source drift: '+source.stderr)
    (out/'app-runtime-head.txt').write_text(source.stdout)
    tasks=D/('qualification_tasks.json' if a.mode=='qualification' else 'hil15b_v2_tasks.json')
    cmd=[PY,str(D/'native_driver_entry.py'),a.mode,str(out/'native-attempts.jsonl'),'--',
         '--out-dir',str(out/'native'),'--tasks',str(tasks),'--repeats','1' if a.mode=='qualification' else '3',
         '--max-wall-s','21600' if a.mode=='full' else '240',
         '--min-task-keys','1' if a.mode=='qualification' else '5',
         '--min-dep-task-keys','1' if a.mode=='qualification' else '5',
         '--server-url',a.server_url,'--server-pid',str(a.server_pid),'--served-model',MODEL,
         '--epyc-root',ROOT,'--belief-sidecar','--run-id','hil15b-v2-frozen60' if a.mode=='full' else 'hil15b-v2-qualification']
    (out/'NATIVE-ARGV.json').write_text(json.dumps(cmd,indent=2)+'\n')
    reserve=300 if a.mode=='full' else 10
    start=time.time()
    with (out/'native.log').open('w') as f:
        proc=subprocess.Popen(cmd,cwd=APP,env=dict(os.environ,WINDOW_CONFIRMED='1',PYTHONHASHSEED='0'),
                              stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        (out/'native.pid').write_text(str(proc.pid)+'\n')
        def interrupted(_sig,_frame):raise InterruptedError('supervisor signal')
        signal.signal(signal.SIGTERM,interrupted)
        signal.signal(signal.SIGINT,interrupted)
        try:rc=proc.wait(timeout=max(1,a.deadline_epoch-time.time()-reserve));reason='native exited'
        except subprocess.TimeoutExpired:
            terminate(proc);rc=75;reason='active window cutoff; native process group terminated'
        except BaseException:
            terminate(proc);account(out,a.mode,75,'supervisor interrupted; native process group terminated',time.time()-start)
            raise
    return account(out,a.mode,rc,reason,time.time()-start)


if __name__=='__main__':raise SystemExit(main())

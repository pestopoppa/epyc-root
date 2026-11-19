#!/usr/bin/env python3
"""PF1 grid/receipt controller. No inferred measurement warrant; executor supplies native evidence."""
import argparse, hashlib, json, math, os, statistics, subprocess, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

LENGTHS=(128,256,512,1024,2048)
UBS=(512,2048,4096)
ARMS=('A0','A1','A2','A1-disabled')
# ClaimTuple category labels are measurement identity, not a grade. A0 is the
# incumbent denominator; A1/A2 are GPU treatments. A1-disabled is a diagnostic
# control variant within the candidate GPU build family, not the incumbent.
ARM_CATEGORIES={'A0':'BASELINE','A1':'CANDIDATE','A2':'CANDIDATE','A1-disabled':'CANDIDATE'}

def dump(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj): return hashlib.sha256(dump(obj)).hexdigest()
def write(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.partial-')
    try:
        with os.fdopen(fd,'wb') as f: f.write(dump(obj)+b'\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def grid(lengths=LENGTHS, ubs=UBS, reverse=False):
    # A0/2048 is one intact canonical r=10 invocation per block; all five
    # invocation medians are independent block units, with every sample kept.
    seq=[]
    for rep in range(5):
        for length in lengths:
            arms=list(reversed(ARMS)) if reverse else ARMS
            for arm in arms:
                if arm=='A0':
                    seq.append(dict(arm=arm,L=length,ub=None,rep=rep,n=10 if length==2048 else 1))
                else:
                    for ub in (reversed(ubs) if reverse else ubs):
                        seq.append(dict(arm=arm,L=length,ub=ub,rep=rep,n=1))
    return seq

def check_warrant(w):
    req=('model_shards','cpu_binary_sha256','gpu_binary_sha256','build_line_policy','source_head','build_receipt_sha256','argv_policy','env_policy','protocol','declared_at','manifest_sha256')
    if any(not w.get(k) for k in req): raise ValueError('missing source warrant')
    if len(w['model_shards'])!=3 or w.get('source_head')!='729599d69871181d67af715a4c2f9162d5153a2e' or not w.get('build_line_policy'): raise ValueError('bad artifact/build identity')
    if any(len(x.get('sha256',''))!=64 or not x.get('path') for x in w['model_shards']): raise ValueError('bad model pins')
    body={k:v for k,v in w.items() if k!='manifest_sha256'}
    if digest(body)!=w['manifest_sha256']: raise ValueError('manifest hash mismatch')

def parse_result(data,cell):
    if not isinstance(data,dict) or data.get('status')!='ok': raise ValueError('executor failure')
    vals=data.get('samples_ts')
    if not isinstance(vals,list) or len(vals)!=cell['n'] or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in vals): raise ValueError('truncated or invalid samples_ts')
    evidence=data.get('evidence',{})
    for key in ('raw_output','argv','env','numastat','proc_stat','kfd','vram','placement','build_line'):
        if not evidence.get(key): raise ValueError('missing live evidence: '+key)
    if not str(evidence['build_line']).startswith('build: 729599d') or data.get('build_line')!=evidence['build_line']: raise ValueError('wrong result-emitted C6 build identity')
    if cell['arm'] in ('A1','A2') and not evidence.get('nonzero_vram_during'): raise ValueError('GPU residency unproven')
    if data.get('warnings'): raise ValueError('fallback or execution warning')
    return vals

def run(out,warrant,executor,phase='initial',lengths=LENGTHS,ubs=UBS,initial=None,now=None,session_id=None,admit_cell=None,resume=False):
    check_warrant(warrant)
    if not session_id: raise ValueError('session identity required')
    now=time.time() if now is None else now
    if phase=='holdout':
        if not initial or initial.get('phase')!='initial' or initial.get('status')!='complete': raise ValueError('complete initial receipt required')
        signature=initial.get('self_sha256')
        if not signature or signature != digest({k:v for k,v in initial.items() if k!='self_sha256'}): raise ValueError('initial receipt hash mismatch')
        if initial.get('session_id') == session_id: raise ValueError('holdout requires a distinct session')
        if now-initial['finished_at']<14400: raise ValueError('holdout must be at least four hours later')
        if initial.get('manifest_sha256')!=warrant['manifest_sha256']: raise ValueError('holdout warrant differs')
        if tuple(lengths)!=tuple(initial['holdout_lengths']): raise ValueError('wrong holdout lengths')
    out=Path(out)
    if resume:
        if not out.is_dir(): raise ValueError('resume directory missing')
    else: out.mkdir(parents=True,exist_ok=False)
    cells=grid(lengths,ubs,phase=='holdout'); records=[]
    for i,cell in enumerate(cells):
        record_path=out/f'cell-{i:04d}.json'; intent_path=out/f'intent-{i:04d}.json'
        if intent_path.exists():
            intent=json.loads(intent_path.read_text())
            if intent.get('self_sha256')!=digest({k:v for k,v in intent.items() if k!='self_sha256'}) or intent.get('cell')!=cell or intent.get('manifest_sha256')!=warrant['manifest_sha256'] or intent.get('session_id')!=session_id or intent.get('phase')!=phase: raise ValueError('intent custody mismatch')
        if resume and record_path.exists():
            previous=json.loads(record_path.read_text())
            if previous.get('self_sha256')!=digest({k:v for k,v in previous.items() if k!='self_sha256'}) or previous.get('cell')!=cell or previous.get('manifest_sha256')!=warrant['manifest_sha256'] or previous.get('session_id')!=session_id or previous.get('phase')!=phase: raise ValueError('resume custody mismatch')
            if previous.get('attempted',True):
                if not intent_path.exists(): raise ValueError('attempted cell lacks intent')
                records.append(previous); continue
        status='failed'; reason=''; result={}; values=[]; attempted=False
        try:
            if intent_path.exists(): raise ValueError('interrupted after intent; no redraw')
            if admit_cell is not None and not admit_cell(cell): raise ValueError('deadline, STOP, or grant ended before cell')
            intent={'cell':cell,'manifest_sha256':warrant['manifest_sha256'],'session_id':session_id,'phase':phase,'created_at':time.time()}
            intent['self_sha256']=digest(intent); write(intent_path,intent)
            attempted=True
            result=executor(cell)
            values=parse_result(result,cell); status='ok'
        except Exception as exc: reason=str(exc)
        if intent_path.exists(): attempted=True
        record={'schema':'pf1.native-cell.v1','cell':cell,'attempted':attempted,'status':status,'failure_reason':reason,'samples_ts':values,'executor_output':result,'manifest_sha256':warrant['manifest_sha256'],'phase':phase,'session_id':session_id,'date_epoch':time.time()}
        record['claim_tuple']={'measurement_id':f'pf1:{session_id}:{phase}:{i}',
            'metric':'prompt_throughput','value':statistics.median(values) if values else None,
            'date':datetime.now(timezone.utc).date().isoformat(),'category':ARM_CATEGORIES[cell['arm']],
            'claim':'Per-invocation prompt throughput observation' if values else 'Failed or unattempted invocation',
            'metric_direction':'higher_better','protocol_id':'','reps':len(values),
            'reps_basis':'inner samples of one invocation; independent unit is invocation',
            'unit':'tokens/s','attestation_locator':str(out/f'cell-{i:04d}.json'),
            'source_kind':'pf1-prefill-crossover',
            'extra':{'manifest_sha256':warrant['manifest_sha256'],
                     'artifact_sha256':[x['sha256'] for x in warrant['model_shards']],
                     'binary_sha256':warrant['cpu_binary_sha256' if cell['arm']=='A0' else 'gpu_binary_sha256'],
                     'build_line':result.get('evidence',{}).get('build_line'),'failure_reason':reason,
                     'vram_during_witness':result.get('evidence',{}).get('vram')}}
        record['self_sha256']=digest(record); write(record_path,record); records.append(record)
    result={'schema':'pf1.run.v1','phase':phase,'session_id':session_id,'status':'complete' if all(x['status']=='ok' for x in records) else 'partial','planned':len(cells),'completed':sum(x['status']=='ok' for x in records),'failed':sum(x['status']!='ok' for x in records),'manifest_sha256':warrant['manifest_sha256'],'started_at':now,'finished_at':time.time(),'holdout_lengths':[8192,32768], 'verdict':'incomplete'}
    # A decision requires an explicitly predeclared, validated CI method and
    # a matching independent later-window replicate; no inference here.
    if phase=='initial' and tuple(lengths)==LENGTHS:
        analysis=assess(records); result['analysis']=analysis
        if analysis['status']=='provisional': result['holdout_lengths']=analysis['holdout_lengths']
    result['self_sha256']=digest(result); write(out/'receipt.json',result)
    return result

def median_ci(values):
    """Predeclared percentile bootstrap median CI, 10,000 resamples, seed 34."""
    import random
    if len(values)<5: raise ValueError('insufficient independent samples')
    rnd=random.Random(34); n=len(values)
    samples=sorted(statistics.median(rnd.choices(values,k=n)) for _ in range(10000))
    return statistics.median(values),samples[249],samples[9749]

def assess(records):
    grouped={}
    for r in records:
        if r['status']!='ok': return {'status':'incomplete','reason':'failed or missing cell'}
        c=r['cell']; key=(c['L'],c['arm'],c['ub']); grouped.setdefault(key,[]).extend([statistics.median(r['samples_ts'])] if c['arm']=='A0' and c['L']==2048 else r['samples_ts'])
    by_length={}
    for length in LENGTHS:
        try:
            base=median_ci(grouped[(length,'A0',None)])
            options=[]
            for arm in ('A1','A2'):
                for ub in UBS:
                    m,lo,hi=median_ci(grouped[(length,arm,ub)])
                    options.append((m,lo,hi,arm,ub))
            qualifying=[x for x in options if x[0]>=1.1*base[0] and x[1]>base[2]]
            winner=max(qualifying or options)
            by_length[length]={'cpu':base,'gpu':winner,'qualifies':bool(qualifying)}
        except (KeyError,ValueError): return {'status':'incomplete','reason':f'missing samples at {length}'}
    qualifying=[x for x in LENGTHS if by_length[x]['qualifies']]
    if qualifying:
        chosen=qualifying[0]; idx=LENGTHS.index(chosen); bracket=[LENGTHS[max(0,idx-1)],chosen]
        if bracket[0]==bracket[1]: bracket=[chosen,LENGTHS[1]]
    else: chosen=None; bracket=[8192,32768]
    return {'status':'provisional','L_star':chosen,'holdout_lengths':bracket,'by_length':by_length}

def validate_records(records, expected, receipt):
    if len(records)!=len(expected): raise ValueError('incomplete denominator')
    for record,cell in zip(records,expected):
        claimed=record.get('self_sha256'); actual=digest({k:v for k,v in record.items() if k!='self_sha256'})
        if claimed!=actual or record.get('cell')!=cell or record.get('status')!='ok' or record.get('manifest_sha256')!=receipt['manifest_sha256'] or record.get('phase')!=receipt['phase'] or record.get('session_id')!=receipt['session_id']: raise ValueError('invalid, missing or failed cell')

def final_verdict(initial,holdout,initial_records,holdout_records):
    """Only a fully retained, complete pair may reach a positive/negative finding."""
    for receipt in (initial,holdout):
        if receipt.get('self_sha256')!=digest({k:v for k,v in receipt.items() if k!='self_sha256'}): raise ValueError('invalid receipt')
    if initial['phase']!='initial' or holdout['phase']!='holdout' or initial['session_id']==holdout['session_id']: raise ValueError('invalid sessions')
    if holdout.get('started_at',0)-initial['finished_at']<14400: raise ValueError('holdout too early')
    if initial['manifest_sha256']!=holdout['manifest_sha256']: raise ValueError('manifest mismatch')
    validate_records(initial_records,grid(),initial)
    lengths=tuple(initial['holdout_lengths']); validate_records(holdout_records,grid(lengths,UBS,True),holdout)
    analysis=assess(initial_records)
    if analysis['status']!='provisional' or tuple(analysis['holdout_lengths'])!=lengths: raise ValueError('initial decision mismatch')
    grouped={}
    for r in holdout_records:
        cell=r['cell']; grouped.setdefault((cell['L'],cell['arm'],cell['ub']),[]).extend([statistics.median(r['samples_ts'])] if cell['arm']=='A0' and cell['L']==2048 else r['samples_ts'])
    def qualifies(length,arm,ub):
        baseline=median_ci(grouped[(length,'A0',None)]); measured=median_ci(grouped[(length,arm,ub)])
        return measured[0]>=1.1*baseline[0] and measured[1]>baseline[2]
    star=analysis['L_star']
    if star is None:
        agree=all(not qualifies(l,a,u) for l in lengths for a in ('A1','A2') for u in UBS)
        return {'verdict':'no_crossover' if agree else 'inconclusive','L_star':None,'scope':'diagnostic_only','reason':'GPU llama-bench lacks P-GPU-1 fresh-server evidence; no adoption or closure gate'}
    _,_,_,arm,ub=analysis['by_length'][star]['gpu']
    agree=qualifies(star,arm,ub)
    return {'verdict':'crossover' if agree else 'inconclusive','L_star':star if agree else None,'arm':arm,'ub':ub,'scope':'diagnostic_only','reason':'GPU llama-bench lacks P-GPU-1 fresh-server evidence; no adoption or closure gate'}

def execute_fixture_process(argv, timeout_s=2):
    """Run ONLY a tiny fixture process; never use this as the live executor.

    Results here are synthetic and have no P-BENCH/P-GPU warrant.
    """
    import signal
    proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        stdout,stderr=proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGTERM)
        try: stdout,stderr=proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL); stdout,stderr=proc.communicate()
        raise ValueError('fixture process timed out and was reaped')
    if proc.returncode: raise ValueError('fixture process failed')
    if len(stdout)>1024*1024: raise ValueError('fixture result too large')
    try: return json.loads(stdout)
    except (ValueError,UnicodeError) as exc: raise ValueError('truncated or malformed JSON') from exc

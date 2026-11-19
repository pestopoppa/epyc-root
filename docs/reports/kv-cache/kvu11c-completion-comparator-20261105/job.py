#!/usr/bin/env python3
"""Model-free retained-result reconciliation; no imports or execution of original job."""
import ast,hashlib,json,os,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
ID='kvu11c-retained-result-reconcile-r1-20261105'
STOP=False
def flag(*_):
    global STOP
    STOP=True
signal.signal(signal.SIGTERM,flag); signal.signal(signal.SIGINT,flag)
def limit():
    if STOP or (D/'STOP').exists(): raise RuntimeError('STOP')
    if os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists(): raise RuntimeError('STOP')
    if time.time()>=int(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))): raise RuntimeError('deadline')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,r):
    limit(); p.parent.mkdir(exist_ok=True); q=p.with_suffix('.tmp'); q.write_text(json.dumps(r,sort_keys=True)+'\n'); limit(); os.replace(q,p)
def reconcile():
    seal=json.loads((D/'custody.json').read_text())
    for name,want in seal['files'].items():
        if digest(D/name)!=want: raise RuntimeError('custody drift '+name)
    r=json.loads((D/'original-result.json').read_text()); tree=ast.parse((D/'original-job.py').read_text())
    ns={'r':r,'signal':signal,'all':all,'any':any,'str':str}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            key=n.targets[0].id
            if key in {'TALKER','CODEC'}: ns[key]=ast.literal_eval(n.value.args[0])
            elif key in {'TEXT','VOICE','MODEL_SHA256','MODEL_RECEIPT_BODY_SHA256','MODEL_STAT_SNAPSHOT'}:
                exec(compile(ast.Module(body=[n],type_ignores=[]),'<sealed constants>','exec'),ns)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='complete')
    predicates=[]
    for n in fn.body:
        if isinstance(n,ast.Assert):
            passed=bool(eval(compile(ast.Expression(n.test),'<sealed predicate>','eval'),ns))
            predicates.append({'line':n.lineno,'expression':ast.unparse(n.test),'pass':passed})
    end=(D/'original-ended.txt').read_text()
    source=(D/'original-runner.sh').read_text(); job=(D/'original-job.py').read_text()
    # Explicit native result and receipt predicates supplement every original assertion.
    predicates += [ {'expression':'original grant rc75 partial-native-incomplete','pass':end.splitlines()[0].startswith('rc=75 ') and 'reason=partial-native-incomplete' in end.splitlines()[0]}, {'expression':'original receipt exact job_id','pass':'job_id=kvu11c-gpu-mechanics-smoke-r2-20261105' in end.splitlines()}, {'expression':'original complete calls limit function requiring STOPFILE','pass':"os.environ['FILLER_STOPFILE']" in job and isinstance(fn.body[0],ast.Expr) and ast.unparse(fn.body[0])=='check_run_limits()'}, {'expression':'runner completion suppresses diagnostics','pass':'bash -c "$COMPLETE_CMD" ) >/dev/null 2>&1' in source} ]
    return {'id':ID,'schema':'kvu11c.retained-reconciliation.v1','status':'reconciled_inconclusive' if all(x['pass'] for x in predicates) else 'predicate_mismatch','predicates':predicates,'original_verdict':'inconclusive','custody':seal,'historical_environment':'not retained; actual KeyError conditional on absent inherited FILLER_STOPFILE','source_finding':'runner supplies FILLER_STOPFILE in inner only; outer completion does not establish it; FILLER_ID not used by original job','no_replay':True,'independent_execution_custody':False,'children_spawned':0,'cleanup':'no children created; own process only'}
def complete():
    if os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1':
        r=json.loads(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).read_text())
        if r.get('id')!=ID or r.get('status')!='synthetic_smoke_pass' or r.get('synthetic') is not True or r.get('children_spawned')!=0 or r.get('progress')!=1:
            raise RuntimeError('synthetic smoke incomplete')
        return
    # Literal ID: never depends on missing outer FILLER_ID or inherited run environment.
    r=json.loads((D/'out/RESULT.json').read_text())
    if r.get('id')!=ID or r.get('schema')!='kvu11c.retained-reconciliation.v1' or r.get('status')!='reconciled_inconclusive': raise RuntimeError('incomplete')
    if r.get('independent_execution_custody') is not False or r.get('original_verdict')!='inconclusive' or not r.get('no_replay'): raise RuntimeError('verdict scope drift')
    if not all(x['pass'] for x in r['predicates']): raise RuntimeError('predicate failure')
    if r['custody']!=json.loads((D/'custody.json').read_text()): raise RuntimeError('custody changed')
    for name,want in r['custody']['files'].items():
        if digest(D/name)!=want: raise RuntimeError('source changed')
if __name__=='__main__':
    if sys.argv[1:] == ['--complete']: complete()
    elif os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1':
        limit()
        if len(os.sched_getaffinity(0))!=4: raise RuntimeError('synthetic smoke requires four granted CPUs')
        # Synthetic local fixture only; does not inspect original result or models.
        payload={'id':ID,'status':'synthetic_smoke_pass','progress':1,'synthetic':True,'children_spawned':0}
        atomic(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),payload)
    else:
        limit(); p=D/'out/RESULT.json'
        if p.exists(): raise RuntimeError('single-use reconciliation already has result')
        result=reconcile(); atomic(p,result)
        if result['status']!='reconciled_inconclusive': raise SystemExit(1)

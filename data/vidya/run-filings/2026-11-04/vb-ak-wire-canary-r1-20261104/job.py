#!/usr/bin/env python3
"""One model-free native-ingest / real loop_beliefs.prepare canary; no backend calls."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.dont_write_bytecode = True
D = Path('/mnt/raid0/llm/tmp/vb-ak-wire-canary-r1-20261104')
CODE = D/'code'
PIN = '45562789c80416804ea71df118b6a9e8ceb0ac48'
RID = 'vb-ak-wire-canary-r1-20261104'
EVIDENCE = D/'evidence'
CANONICAL = Path('/mnt/raid0/llm/state/vidya/ledger.jsonl')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if os.environ.get('FILLER_ID') != RID: raise SystemExit('row identity mismatch')
if subprocess.check_output(['git','-C',str(CODE),'rev-parse','HEAD'],text=True).strip()!=PIN: raise SystemExit('source pin mismatch')
if subprocess.check_output(['git','-C',str(CODE),'status','--porcelain','--untracked-files=no'],text=True).strip(): raise SystemExit('tracked source dirty')
if subprocess.run(['git','-C',str(CODE),'symbolic-ref','-q','HEAD'],capture_output=True).returncode == 0: raise SystemExit('source must be detached')
DRY = os.environ.get('FILLER_DRYRUN') == '1'
OUT = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if DRY else D/'RESULT.json'
W = OUT.parent/'canary-state' if DRY else D/'state'
W.mkdir(exist_ok=True)
if OUT.exists(): raise SystemExit('result exists; no in-run retry')
ledger = W/'ledger.jsonl'
if ledger.exists(): raise SystemExit('scratch ledger exists; no in-run retry')
before = sha(CANONICAL)
shutil.copyfile(CANONICAL, ledger)
marker = Path(str(CANONICAL)+'.sync.json')
if marker.exists(): shutil.copyfile(marker,Path(str(ledger)+'.sync.json'))
(W/'alarm.yaml').write_text('schema_version: alarm_channel.config.v1\nenabled: false\nbackend: ntfy\n')
(W/'tmp').mkdir(exist_ok=True)
os.environ['TMPDIR']=str(W/'tmp'); tempfile.tempdir=str(W/'tmp')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
# Audit forbids every network call, subprocess, and write outside scratch after source checks.
def audit(event,args):
    if event in ('socket.connect','socket.bind','subprocess.Popen','os.system'): raise PermissionError('model-free canary forbids '+event)
    if event=='open':
        path,mode,flags=args
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and not isinstance(path,int):
            resolved=Path(path).resolve()
            if resolved != OUT.resolve() and not resolved.is_relative_to(D) and not resolved.is_relative_to(W.resolve()): raise PermissionError('write outside scratch')
sys.addaudithook(audit)
sys.path.insert(0,str(CODE/'scripts/vidya'))
result={'schema':'epyc.vb.akwire.planning_canary.v1','measurement':False,'code_sha':PIN,'model_backend_calls':0,'canonical_before':before,'status':'UNKNOWN'}
try:
    import ingest_sources, loop_beliefs
    from ledger import Ledger
    from adapters.autokernel_actor_wire import _matrix_proposition
    stamp=datetime.now(timezone.utc).isoformat()
    native=json.loads((EVIDENCE/'actor-wire-final.json').read_text())
    proposition=_matrix_proposition(native)
    report=ingest_sources.ingest(Ledger(ledger),'ak-actor-wire',[EVIDENCE],as_of=stamp)
    (W/'ingest.json').write_text(json.dumps(report,indent=2))
    # Actual Q38FN planner target from committed canary A; no actor-wire scope is invented.
    target={'model_path':'/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf','quant':'UD-IQ4_XS','backend':'cpu','surface':'serving:q38fn-802bf9ac6-cpu-t48-mtp-d4'}
    prepared=loop_beliefs.prepare('autokernel.planner',target,ledger=ledger,index_path=CODE/'research/intake_index.yaml',as_of=datetime.now(timezone.utc).isoformat(),known_good=W/'known-good.json',alarm_state=W/'alarm.json',alarm_config=W/'alarm.yaml',read_log=W/'reads.jsonl',source_memo_dir=W/'source-memo')
    (W/'prepared.json').write_text(json.dumps(prepared,indent=2))
    section=(prepared.get('evidence') or {}).get('section','')
    (W/'planner-belief-section.txt').write_text(section)
    visible=proposition in section
    refused=len(report['refused'])
    result.update(ingest_refused=refused,rows_projected=report['rows_projected'],expected_proposition=proposition,proposition_visible=visible,prepare_status=prepared.get('status'),target=target,evidence=prepared.get('evidence'),native_final_sha256=sha(EVIDENCE/'actor-wire-final.json'))
    result['status']='UNKNOWN' if prepared.get('status')!='ready' else ('PASS' if refused==0 and report['rows_projected']>0 and visible else 'FAIL')
    result['reason']='native proposition visible' if result['status']=='PASS' else 'native proposition omitted or ingest refused; native applicability preserved' if result['status']=='FAIL' else 'prepare refused'
except Exception as exc:
    result.update(status='UNKNOWN',reason=f'{type(exc).__name__}: {exc}')
result['canonical_after']=sha(CANONICAL)
result['canonical_unchanged']=result['canonical_after']==before
if not result['canonical_unchanged']: result.update(status='UNKNOWN',reason='protected canonical state changed')
with OUT.open('x') as f: json.dump(result,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())

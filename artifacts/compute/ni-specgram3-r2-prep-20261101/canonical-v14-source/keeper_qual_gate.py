#!/usr/bin/env python3
"""Fail closed READY gate for ws58 keeper v8; no grant writes here."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import time
import fcntl
import glob
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_launcher as q

ROOT = Path('/mnt/raid0/llm/tmp/compute-flags')

def refusal(message: str) -> tuple[str, str]: return ('bad', message)

def grant_status(path: Path, horizon_s: int = 0) -> tuple[str, str]:
    """Classify a writer grant by its actual window, not file presence."""
    if not path.exists(): return ('absent','')
    try:
        line=path.read_text().splitlines()[0]
        match=re.fullmatch(r'regions=([^ ]+) start=(\d{4}-\d\d-\d\dT\d\d:\d\dZ) end=(\d{4}-\d\d-\d\dT\d\d:\d\dZ)',line)
        if not match:return ('malformed','')
        regions,start,end=match.groups()
        start=dt.datetime.strptime(start,'%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp()
        end=dt.datetime.strptime(end,'%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp()
        if start>=end:return ('malformed',regions)
        now=time.time()
        if end<=now:return ('expired',regions)
        if start>now+horizon_s:return ('future',regions)
        return ('active' if start<=now else 'booked',regions)
    except (OSError,ValueError,IndexError):return ('malformed','')

def classify(manifest: Path, flags: Path, *, fingerprint: bool = True) -> tuple[str, str]:
    try:
        m = q.load_manifest(manifest)
        if m['production'] is not True: return refusal('fixture is not production')
        if m.get('hold') is not None: return refusal('hold=' + str(m['hold']))
        breaker=read_json(flags/'ws58-keeper-state/qual-failure-breakers.json') or {}
        if breaker.get('owners',{}).get(m['owner'],{}).get('active'):
            return refusal('worker-breaker active for '+m['owner'])
        if (flags / 'grants' / (m['id']+'.ended')).exists(): return refusal('ended id cannot be reused')
        if (flags / 'grants' / (m['id']+'.complete')).exists(): return refusal('already complete')
        grant_state,_=grant_status(flags/'grants'/(m['id']+'.grant'))
        if grant_state!='absent': return refusal('grant file '+grant_state+'; id cannot be reused')
        if q.disk_wait(manifest): return ('wait-disk', 'free - output - 2 GiB below 150 GiB')
        q.verify(manifest, flags, fingerprint)
        return ('ok', 'keeper-issued qualification valid')
    except (q.Refused, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return refusal('qual:' + str(exc))

def booked_candidate(rid: str, flags: Path) -> bool:
    sys.path.insert(0,str(flags))
    try: import grant_ok_launcher as gate
    except ImportError:return False
    paths=[flags/'ws58-gpu.queue',*flags.glob('ws58-quarters-*.queue')]
    for path in paths:
        try: lines=path.read_text().splitlines()
        except OSError:continue
        for line in lines:
            fields=line.split('|')
            if len(fields)<2 or fields[0]!=rid:continue
            try:
                pid=int(fields[1])
                if gate.alive('/proc',pid) and gate.find_launcher('/proc',pid,rid)[0]:return True
            except (ValueError,OSError,AttributeError,gate.Refuse):continue
    return False

def conflict(manifest: Path, flags: Path) -> tuple[str, str]:
    """Only actual live holders or valid booked reservations can conflict."""
    m = q.load_manifest(manifest)
    horizon=int(m.get('qual_timeout_s',300))+90
    my_ports=set(m['ports']);my_shared=set(m['shared_state']);my_excl=m['exclusive_class']
    armed={p.stem:p for p in (flags/'ready'/'armed').glob('*.json')}
    for grant in (flags/'grants').glob('*.grant'):
        if grant.stem==m['id']:continue
        if (flags/'grants'/(grant.stem+'.ended')).exists() or (flags/'grants'/(grant.stem+'.complete')).exists():continue
        state,_=grant_status(grant,horizon_s=horizon)
        if state in ('expired','future'):continue
        if state=='malformed':return ('wait-conflict','malformed active grant '+grant.stem)
        if grant.stem not in armed:return ('wait-conflict','unknown active grant '+grant.stem)
    for rid,p in sorted(armed.items()):
        if rid==m['id']:continue
        if (flags/'grants'/(rid+'.ended')).exists() or (flags/'grants'/(rid+'.complete')).exists():continue
        state,_=grant_status(flags/'grants'/(rid+'.grant'),horizon_s=horizon)
        live=state=='active'
        if state=='malformed':return ('wait-conflict','malformed active grant '+rid)
        eligible_booked=False
        if not live:
            if state!='booked' and not booked_candidate(rid,flags):continue
            eligible_booked=True
        other=read_json(p)
        if not other:return ('wait-conflict','active/valid booked manifest unparseable '+rid)
        if eligible_booked:
            if other.get('schema')!='epyc.ready.v2':continue
            try:q.verify(p,flags,True)
            except (q.Refused,OSError,ValueError,KeyError,subprocess.TimeoutExpired):continue
        if not all(k in other for k in ('ports','exclusive_class','shared_state')):
            return ('wait-conflict','active/eligible declaration unknown:'+rid)
        if my_ports & set(other['ports']):return ('wait-conflict','port-overlap:'+rid)
        if my_excl and other['exclusive_class']==my_excl:return ('wait-conflict','exclusive-class:'+my_excl)
        if my_shared & set(other['shared_state']):return ('wait-conflict','shared-state:'+rid)
    return ('ok','no declared live/eligible conflict')

def parse_status(text: str) -> set[str]:
    free = set()
    for line in text.splitlines():
        bits = line.split()
        if len(bits) > 1 and bits[1] == 'free': free.add(bits[0])
    return free

def qual_pair(m: dict, flags: Path, rl: Path) -> str | None:
    # R11 uses two SMT threads under a family mutex. A correctness quarter
    # may be held; no CPU quarter region-lock claim is taken for qualification.
    gpu = 'mi210_0' in str(m.get('regions', ''))
    if any(flags.glob('HOLD_*')): return None
    if gpu:
        status = subprocess.run([str(rl), 'status'], text=True, capture_output=True, timeout=15)
        if status.returncode or 'gpu-quiet' not in parse_status(status.stdout): return None
    from dryrun_check import grant_cpus
    rows = {}
    for line in (flags/'FILLERS.md').read_text().splitlines():
        cells = [v.strip() for v in line.strip().strip('|').split('|')]
        if len(cells) == 18: rows[cells[0]] = cells[8]
    live = []
    for path in (flags / 'grants').glob('*.grant'):
        try:
            if (flags/'grants'/(path.stem+'.ended')).exists() or (flags/'grants'/(path.stem+'.complete')).exists():
                continue
            state,reg=grant_status(path,horizon_s=int(m.get('qual_timeout_s',300))+90)
            if state in ('expired','future'):continue
            if state=='malformed':return None
            if gpu and 'mi210_0' in reg: return None
            kind = rows.get(path.stem)
            if not kind: return None
            live.append((kind, grant_cpus(reg)))
        except (OSError, ValueError, AttributeError, q.Refused): return None
        except Exception: return None  # unknown native grant parser failure waits
    for base in (26,32,36,50,56,74,80):
        pair = {base+96, base+97}
        physical = {base,base+1}
        if any(pair & given or ('timing' in kind and (physical & {x%96 for x in given} or
                    set(range(96)) <= {x%96 for x in given})) for kind,given in live):continue
        return f'{base+96}-{base+97}'
    return None

def qualify_pending(manifest: Path, flags: Path, rl: Path, timeout: int, dry: bool = False) -> tuple[str, str]:
    try:
        m = q.load_manifest(manifest)
        if m['production'] is not True: return refusal('fixture cannot qualify production')
        if m.get('hold') not in (None, 'breaker'): return refusal('held')
        if (flags / 'grants' / (m['id']+'.ended')).exists(): return refusal('ended id cannot be reused')
        if q.disk_wait(manifest): return ('wait-disk', 'free - output - 2 GiB below floor')
        try:
            q.verify(manifest, flags, True)
            return ('qualified', 'already valid')
        except (q.Refused, OSError, ValueError, KeyError, json.JSONDecodeError): pass
        if Path(m['qualification']['receipt']).exists():
            return refusal('stale qualification receipt; republish under a new id')
        pair = qual_pair(m, flags, rl)
        if not pair: return ('wait-resource', 'no admitted R11 SMT pair/GPU resource')
        if dry: return ('would-qualify', pair)
        base=int(pair.split('-')[0])-96
        lock_path=flags/'prep-locks'/f'{base}-{base+1}.lock'
        lock_path.parent.mkdir(parents=True,exist_ok=True)
        with lock_path.open('a+') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: return ('wait-resource','R11 family mutex busy')
            if qual_pair(m,flags,rl)!=pair: return ('wait-resource','R11 grant/GPU status changed')
            nonce = q.issue(manifest, flags)
            gpu='mi210_0' in str(m['regions'])
            timeout=int(m.get('qual_timeout_s',timeout))
            if timeout not in (300,600):return refusal('qual_timeout_s must be 300 or 600')
            child=['taskset','-c',pair,'/usr/bin/env',
                   'WS58_QUAL_GPU_HELD=' + ('1' if gpu else '0'),
                   sys.executable,'-I',str(Path(q.__file__)),'run','--manifest',str(manifest),
                   '--flags',str(flags),'--nonce',nonce,'--timeout',str(timeout)]
            # GPU first requests must run inside an actual exclusive quiet
            # claim. CPU qualification holds only the R11 pair mutex.
            args=([str(rl),'run','--gpu-quiet','exclusive','--role','build',
                   '--timeout-s',str(timeout+45),'--tag','qual-'+m['id'],'--']+child) if gpu else child
            env=dict(os.environ,WS58_QUAL_CPUS=pair,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
            out=flags/'ready'/(m['id']+'.qual.out')
            with out.open('a') as f:
                cp=subprocess.run(args,cwd=str(flags),env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout+90)
        if cp.returncode: return refusal(f'qual-run-rc={cp.returncode}; see {out}')
        q.verify(manifest, flags, True)
        return ('qualified', str(m['qualification']['receipt']))
    except (q.Refused, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return refusal('qual:' + str(exc))

def reconcile_failures(flags: Path, dry: bool = False) -> list[str]:
    """Three new failed grant attempts in 24h trip only that owner's breaker."""
    rows = {}
    for line in (flags/'FILLERS.md').read_text().splitlines():
        cells = [v.strip() for v in line.strip().strip('|').split('|')]
        if len(cells) == 18: rows[cells[0]] = cells[1]
    state_path = flags/'ws58-keeper-state/qual-failure-breakers.json'
    try: state = json.loads(state_path.read_text())
    except (OSError,ValueError): state = {'owners':{},'alerted':{}}
    now = time.time(); failures = {}; actions = []
    for ended in sorted((flags/'grants').glob('*.ended')):
        try:
            first = ended.read_text().splitlines()[0]
            rc = int(first.split(' ',1)[0].removeprefix('rc='))
            stamp = ended.stat().st_mtime
        except (OSError,ValueError,IndexError): continue
        if rc in (0,75) or now-stamp > 86400 or stamp > now+60: continue
        owner = rows.get(ended.stem)
        if not owner: continue
        failures.setdefault(owner,[]).append((ended.stem,stamp,rc))
        key=ended.stem+':'+str(stamp)+':'+str(rc)
        if key not in state['alerted']:
            actions.append('run-failed '+owner+' '+ended.stem+' rc='+str(rc))
            if not dry:
                alert={'kind':'run-failed','id':ended.stem,'owner':owner,'rc':rc,
                       'at':dt.datetime.now(dt.timezone.utc).isoformat()}
                with (flags/'ws58-keeper-alerts.jsonl').open('a') as f:f.write(json.dumps(alert,sort_keys=True)+'\n')
                state['alerted'][key]=now
    for owner in set(failures) | set(state['owners']):
        attempts=failures.get(owner,[])
        rec=state['owners'].get(owner,{'active':False,'reset_at':0})
        new=[x for x in attempts if x[1]>rec.get('reset_at',0)]
        if len(new)>=3 and not rec.get('active'):
            rec={'active':True,'tripped_at':now,'reset_at':rec.get('reset_at',0),
                 'failed_ids':[x[0] for x in new]}
            state['owners'][owner]=rec;actions.append('worker-breaker '+owner)
            if not dry:
                with (flags/'ws58-keeper-alerts.jsonl').open('a') as f:
                    f.write(json.dumps({'kind':'worker-breaker','owner':owner,'failed_ids':rec['failed_ids'],
                        'at':dt.datetime.now(dt.timezone.utc).isoformat()},sort_keys=True)+'\n')
        if rec.get('active'):
            # Fresh keeper-issued qualification after the breaker releases the
            # owner. A free-form smoke or old receipt cannot release it.
            for path in (flags/'ready').glob('*.json'):
                m=read_json(path)
                if not m or m.get('schema')!='epyc.ready.v2' or m.get('owner')!=owner: continue
                try: proof=q.verify(path,flags,True)
                except (q.Refused,OSError,ValueError,KeyError,subprocess.TimeoutExpired): continue
                age=dt.datetime.fromisoformat(proof['ran_at'].replace('Z','+00:00')).timestamp()
                if age>rec['tripped_at']:
                    rec.update(active=False,reset_at=now,released_by=m['id'])
                    actions.append('worker-breaker-released '+owner+' by '+m['id']);break
        state['owners'][owner]=rec
    state['alerted']={k:v for k,v in state['alerted'].items() if now-v<172800}
    if not dry:q.atomic_json(state_path,state)
    return actions

def read_json(path: Path) -> dict | None:
    try:
        value=json.loads(path.read_text())
        return value if isinstance(value,dict) else None
    except (OSError,ValueError):return None

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=('check', 'conflict', 'qualify-pending', 'reconcile-failures'))
    p.add_argument('--manifest', type=Path)
    p.add_argument('--flags', type=Path, default=ROOT)
    p.add_argument('--region-lock', type=Path, default=Path('/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock'))
    p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--dry', action='store_true')
    a = p.parse_args()
    if a.command == 'reconcile-failures':
        print('\n'.join(reconcile_failures(a.flags,a.dry))); return 0
    if not a.manifest: raise SystemExit('REFUSED: --manifest required')
    if a.command == 'check': state, reason = classify(a.manifest, a.flags)
    elif a.command == 'conflict': state, reason = conflict(a.manifest, a.flags)
    else: state, reason = qualify_pending(a.manifest, a.flags, a.region_lock, a.timeout, a.dry)
    print(state + '\t' + reason.replace('\n', ' ')[:240])
    return 0 if state in ('ok', 'qualified', 'would-qualify') else 2

if __name__ == '__main__': raise SystemExit(main())

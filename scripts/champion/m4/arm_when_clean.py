#!/usr/bin/env python3
"""One-shot r6 owner watcher: arm a qualified row only after two clean samples.

It creates no grant, touches no peer process and exits if row state changes.
The M4 native entry independently refuses other llama workloads at each launch.
"""
import fcntl, hashlib, json, os, subprocess, sys, time
from pathlib import Path
flags='/mnt/raid0/llm/tmp/compute-flags';rid='inf22-m4-aa-np4-r6-20261102'
root=Path('/mnt/raid0/llm/tmp/inf22-m4-aa-np4-r6-20261102')
sys.path.insert(0,str(root/'scripts/coordination/rowflow'))
import rowflow


def clean_sample():
    p=subprocess.run(['ps','-eo','pid=,comm=,args='],check=True,capture_output=True,text=True,timeout=10)
    rows=[]
    for line in p.stdout.splitlines():
        fields=line.strip().split(None,2)
        if len(fields)!=3 or not fields[0].isdigit(): raise RuntimeError('unreadable process census')
        rows.append((int(fields[0]),fields[1],fields[2]))
    if not any(pid==os.getpid() for pid,_,_ in rows):raise RuntimeError('process census omitted watcher')
    blockers=[]
    for pid,comm,args in rows:
        if comm in {'llama-server','llama-bench','llama-cli'}:
            blockers.append(('llama',pid));continue
        words=args.split()
        if any(words[i:i+2]==['uvicorn','src.api:app'] for i in range(len(words)-1)):
            try: env=Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
            except FileNotFoundError: continue
            except OSError as exc: raise RuntimeError(f'dispatch {pid} environ unavailable') from exc
            value=next((e.split(b'=',1)[1].decode().strip().lower() for e in env if e.startswith(b'ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=')), '')
            if value not in ('1','true','yes','on'):blockers.append(('unflagged-dispatch',pid))
    return blockers


def main():
    lock=(root/'run/arm-watcher.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    held=Path(flags)/'dryrun'/rid/'OWNER-CLEAN-WAIT.row.json'
    ready=Path(flags)/'ready'/f'{rid}.json'
    expected='2899f50a8bb31a9c3dfa205070356ae0edf157ee67cd74109f034169fb77d828'
    clean=0
    while True:
        if ready.exists() or not held.is_file():
            print('EXIT ownership changed',flush=True);return 1
        if (Path(flags)/'grants'/f'{rid}.grant').exists():
            print('EXIT unexpected grant',flush=True);return 1
        if hashlib.sha256(held.read_bytes()).hexdigest()!=expected:
            print('EXIT held row changed',flush=True);return 1
        row=json.loads(held.read_text())
        passed=rowflow.load_json(rowflow.pass_path(flags,rid))
        launcher=row['launcher']['path']
        if not passed or passed.get('launcher_sha256')!=row['launcher']['sha256'] or rowflow.sha256(launcher)!=row['launcher']['sha256']:
            print('EXIT qualification or launcher changed',flush=True);return 1
        try:
            busy=clean_sample()
        except (OSError,subprocess.SubprocessError,RuntimeError) as exc:
            clean=0;print('WAIT census-unavailable',str(exc),flush=True)
        else:
            if busy:
                if clean: print('RESET peer server appeared',flush=True)
                clean=0
            else:
                clean+=1
                if clean>=2:
                    # Link is atomic and exclusive; until this point the keeper
                    # cannot see the row. Only the keeper arms and grants it.
                    os.link(held,ready)
                    held.unlink()
                    print('RELEASED row to deterministic keeper',flush=True);return 0
        time.sleep(10)

if __name__=='__main__':raise SystemExit(main())

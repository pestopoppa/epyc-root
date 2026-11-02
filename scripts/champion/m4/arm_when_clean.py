#!/usr/bin/env python3
"""One-shot r6 owner watcher: arm a qualified row only after two clean samples.

It creates no grant, touches no peer process and exits if row state changes.
The M4 native entry independently refuses other llama workloads at each launch.
"""
import fcntl, json, os, subprocess, sys, time
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
    clean=0
    while True:
        rows=rowflow.rows(flags);row=rows.get(rid)
        if not row:
            print('EXIT row absent',flush=True);return 1
        state=rowflow.status(flags,rid,rows)['state']
        if state!='grantable':
            print('EXIT row state',state,flush=True);return 0 if state in ('armed','running','done') else 1
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
                    # status revalidates the current PASS and launcher digest;
                    # no grant is written here.
                    if rowflow.status(flags,rid,rows)['state']!='grantable':continue
                    pid,msg=rowflow.arm_one(flags,rid,row)
                    print('ARM',pid,msg,flush=True);return 0 if pid else 1
        time.sleep(10)

if __name__=='__main__':raise SystemExit(main())

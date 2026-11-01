#!/usr/bin/env python3
"""Unpublished, fail-closed KVU-12.5 producer skeleton. Does not launch inference."""
import json, os, pathlib, tempfile, time
D=pathlib.Path(__file__).resolve().parent

def mode(env):
    raw=env.get('FILLER_DRYRUN')
    if raw not in ('0','1'): raise ValueError('explicit FILLER_DRYRUN=0|1 required')
    return 'control' if raw=='1' else 'target'

def check_claim(env):
    if env.get('FILLER_CPUS') not in ('72-95','72-95,168-191'): raise ValueError('q3 CPU grant required')
    if env.get('FILLER_THREADS')!='24': raise ValueError('24 physical threads required')
    if env.get('FILLER_NEEDGPU')!='0': raise ValueError('CPU quarter grant required')
    stop=env.get('FILLER_STOPFILE'); deadline=env.get('FILLER_DEADLINE')
    if not stop or not deadline: raise ValueError('stop and deadline required')
    if pathlib.Path(stop).exists() or int(deadline)<=int(time.time()): raise ValueError('stop/deadline reached')

def append_native(path,record):
    if record.get('mode') not in ('control','target') or record.get('native_record_complete') is not True:
        raise ValueError('only completed native control/arm records may be appended')
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(record,allow_nan=False,separators=(',',':'))+'\n'
    with path.open('a') as f:
        f.write(payload);f.flush();os.fsync(f.fileno())

def main():
    # This scaffold cannot trigger the target or emit synthetic qualification records.
    mode(os.environ);check_claim(os.environ)
    raise RuntimeError('NOT READY: producer, output, per-arm GPU quiet sampling and cleanup integration are incomplete')
if __name__=='__main__':main()

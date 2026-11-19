#!/usr/bin/env python3
"""Invoked by driver only inside its separately acquired 0-95 region claim."""
import json, os, sys, time
from pathlib import Path
import controller, native_executor

def main(manifest_path,output):
    if os.environ.get('FILLER_PREFLIGHT')=='1' or os.environ.get('FILLER_NEEDGPU')!='1': raise ValueError('not a live CPU+GPU grant')
    if time.time()>=int(os.environ['FILLER_DEADLINE']) or Path(os.environ['FILLER_STOPFILE']).exists(): raise ValueError('STOP or deadline')
    w=json.loads(Path(manifest_path).read_text()); controller.check_warrant(w)
    mon=native_executor.cpu_monitor(w)
    before=mon.host_snapshot(); mon.require_clean_host(before,'before cache preparation')
    records=mon.prepare_pair([Path(x['path']) for x in w['model_shards']])
    after=mon.host_snapshot(); mon.require_clean_host(after,'after cache preparation')
    value={'manifest_sha256':w['manifest_sha256'],'before':before,'preparation':records,'after':after,'finished_at':time.time()}
    value['self_sha256']=controller.digest(value); controller.write(output,value)

if __name__=='__main__':
    try: main(sys.argv[1],sys.argv[2])
    except Exception as exc: print(f'cache preparation refused: {exc}',file=sys.stderr); sys.exit(2)

#!/usr/bin/env python3
"""Capture a current replay, preserving refusals without manufacturing observations."""
import argparse
import base64
import hashlib
import sys
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapters import nemo_range_join as n

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def checkpoint_partial(output, record):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=output.parent, delete=False) as stream:
        json.dump(record, stream, sort_keys=True, indent=2); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno()); temporary=stream.name
    os.replace(temporary, output.parent / 'replay.partial.json')

def main():
    p=argparse.ArgumentParser(); p.add_argument('run_dir',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
    started=now(); mode='publisher_smoke' if os.environ.get('FILLER_DRYRUN')=='1' else 'official'; record={'schema':'nemo.range.replay.refusal.v1','status':'unknown','started_at':started}
    try:
        grant={k:os.environ[v] for k,v in [('id','FILLER_ID'),('deadline','FILLER_DEADLINE'),('stopfile','FILLER_STOPFILE')]}
        grant_path=Path(os.environ['NEMO_GRANT_PATH']); raw=grant_path.read_bytes()
        copy=a.output.parent/'grant.copy'; copy.write_bytes(raw)
        record.update(grant=grant)
        grant.update(path=str(grant_path.resolve()),bytes_b64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest(),copy='grant.copy')
        cpus=sorted(os.sched_getaffinity(0)); record['cpus']=cpus
        if len(cpus)!=4 or time.time()>=int(grant['deadline']) or Path(grant['stopfile']).exists(): raise ValueError('grant, deadline, stop or affinity')
        n.grant_check(grant, cpus, started, started, a.output.parent)
        audit=n.load_audit()
        files={'audit':n.AUDIT,'original_receipt':audit.SOURCE/'RESULT.json',
               'marker_adapter':audit.SOURCE/'nemo-marker-csv-adapter-20261105/marker_csv.py',
               'clock_join':audit.SOURCE/'nemo-fixture-clock-join-20261105/fixture_clock_join.py',
               'writer':Path(__file__).resolve(),'adapter':Path(n.__file__).resolve(),'fixture_manifest':n.FIXTURE_MANIFEST}
        pins={role:n.sha(path) for role,path in files.items()}
        record['source_pins']=pins
        if [pins[k] for k in ('original_receipt','marker_adapter','clock_join')] != ['7d6db4dea6dfed738f1fc2f223a9d9333630e86d4ec4f2bb486da781971fff1e','3630ad137abe4b0574554d103d724fa7b45bce6c46871d389bcda4f4c6979ff4','a44ca3cc0a22b9d24e3597fccafe0aafc031168b148f92c38c167b125cd5e4b3']: raise ValueError('external source drift')
        receipt=json.loads(files['original_receipt'].read_bytes(),object_pairs_hook=n.unique)
        if receipt.get('status')!='COMPLETE' or receipt.get('unit_count')!=80 or len(receipt.get('rows',[]))!=80: raise ValueError('receipt census')
        n.verify_fixture_inputs(a.run_dir)
        dirs=sorted(a.run_dir.glob('*-sdk'),key=lambda x:int(x.name.split('-')[0]))
        if [d.name for d in dirs]!=[f'{i}-sdk' for i in range(80)]: raise ValueError('run census')
        results={}; record['result']=results
        for i,d in enumerate(dirs):
            if time.time()>=int(grant['deadline']) or Path(grant['stopfile']).exists(): raise ValueError('deadline or stop')
            r=audit.audit(d); row=receipt['rows'][i]; arms=[x for x in row['arms'] if x['arm']=='sdk']
            if row['pair']!=i or len(arms)!=1: raise ValueError('receipt pair')
            arm=arms[0]; files0=arm['marker_files']
            if arm['status']!='PASS' or len(files0)!=1 or files0[0]['sha256']!=r['input_sha256']['fixture-trace/'+audit.NAMES[0]] or arm['fixture_pids']!=[str(r['fixture_pid'])] or arm['graph_ids']!=[j['graph_correlation_id'] for j in r['joins']]: raise ValueError('receipt identity')
            results[d.name]=r
            checkpoint_partial(a.output,record)
        n.verify_fixture_inputs(a.run_dir)
        if pins!={role:n.sha(path) for role,path in files.items()}: raise ValueError('source drift')
        if grant_path.read_bytes()!=raw: raise ValueError('grant changed')
        n.grant_check(grant, cpus, started, now(), a.output.parent)
        record={'schema':'nemo.range.replay.v1','status':'complete','mode':mode,'started_at':started,'ended_at':now(),'grant':grant,'cpus':cpus,'run_dir':str(a.run_dir.resolve(strict=True)),'source_pins':pins,'result':results,'limits':n.LIMIT}
    except (OSError,ValueError,KeyError,TypeError,ImportError) as exc:
        record.update(ended_at=now(),refusal=str(exc))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=a.output.parent,delete=False) as f:
        json.dump(record,f,sort_keys=True,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno()); tmp=f.name
    try: os.link(tmp,a.output)
    finally: os.unlink(tmp)
    return 0 if record['status']=='complete' else 1
if __name__=='__main__': raise SystemExit(main())

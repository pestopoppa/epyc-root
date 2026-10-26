#!/usr/bin/env python3
"""PROPOSED engine state mutation adapter under common publication lease."""
import argparse
from pathlib import Path
import re
import time
import gap_serialization_v1 as serial
import gap_runtime_v1 as runtime

def mutate(flags,row_id,rc,reason,complete=False,now=None,overrun=None):
    flags=Path(flags)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',row_id): raise runtime.Refuse('unsafe-id')
    now=now or runtime.utc()
    with serial.PublicationLease(flags, timeout=5, deadline_epoch=time.time()+10) as lease:
        if complete:
            serial.replace_bytes(lease,flags/'grants'/(row_id+'.complete'),f'complete time={now} id={row_id}\n'.encode())
            rows=flags/'FILLERS.md'
            if rows.exists():
                data=runtime.read_record(rows)[1].decode()
                lines=data.splitlines(keepends=True)
                for i,line in enumerate(lines):
                    if line.startswith('| '+row_id+' |'):
                        lines[i]=line.replace('ARMED','COMPLETE')
                serial.replace_bytes(lease,rows,''.join(lines).encode())
        receipt=f"rc={rc} time={now} reason={reason}\n"
        if overrun is not None:
            started,owner,estimate,regions=overrun
            receipt+=f"job_id={row_id}\nowner={owner}\nstep=job-run\nestimated_wall_s={estimate}\nstarted={started}\nregions={regions}\n"
        serial.replace_bytes(lease,flags/"grants"/(row_id+".ended"),receipt.encode())
        lease.assert_held()
        try: (flags/'grants'/(row_id+'.grant')).unlink()
        except FileNotFoundError: pass

def main():
    p=argparse.ArgumentParser(); p.add_argument('--flags',required=True);p.add_argument('--id',required=True)
    p.add_argument('--rc',type=int,required=True);p.add_argument('--reason',required=True);p.add_argument('--complete',action='store_true')
    p.add_argument("--overrun-started");p.add_argument("--overrun-owner");p.add_argument("--overrun-est");p.add_argument("--overrun-regions")
    a=p.parse_args()
    values=(a.overrun_started,a.overrun_owner,a.overrun_est,a.overrun_regions)
    overrun=values if a.overrun_started and a.overrun_est else None
    mutate(a.flags,a.id,a.rc,a.reason,a.complete,overrun=overrun)
if __name__=='__main__': main()

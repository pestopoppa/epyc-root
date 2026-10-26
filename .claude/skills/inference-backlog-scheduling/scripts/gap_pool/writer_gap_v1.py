#!/usr/bin/env python3
"""PROPOSED owner publication adapter. Default false; exact absolute grant end."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import gap_runtime_v1 as runtime
import gap_serialization_v1 as serial

def live_owned_group(pgid):
    p=subprocess.run(['ps','-eo','pgid=,stat='],capture_output=True,text=True,check=True)
    return any(fields[0]==str(pgid) and not fields[1].startswith('Z')
               for line in p.stdout.splitlines() if len(fields:=line.split())>=2)

def stop_owned(proc):
    """Only self-captured Popen group. Verify using ps, never kill0/name patterns."""
    if live_owned_group(proc.pid):
        os.killpg(proc.pid,signal.SIGTERM)
        until=time.monotonic()+2
        while time.monotonic()<until and live_owned_group(proc.pid):time.sleep(.05)
        if live_owned_group(proc.pid):os.killpg(proc.pid,signal.SIGKILL)
    try:proc.wait(timeout=2)
    except subprocess.TimeoutExpired:raise runtime.Refuse('owned-admission-child-death-unproven')
    if live_owned_group(proc.pid):raise runtime.Refuse('owned-admission-group-death-unproven')

def run_normal(normal,absolute_end):
    remaining=absolute_end-time.time()
    if remaining<=0:raise runtime.Refuse('admission-deadline-expired-before-callback')
    proc=subprocess.Popen(normal,start_new_session=True)
    try:
        proc.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        stop_owned(proc)
        raise runtime.Refuse('admission-callback-deadline-expired-owned-group-dead')
    except BaseException:
        stop_owned(proc)
        raise
    if live_owned_group(proc.pid):
        stop_owned(proc)
        raise runtime.Refuse('admission-callback-left-owned-descendants')
    if proc.returncode:raise runtime.Refuse('normal-admission-rc='+str(proc.returncode))
    if time.time()>=absolute_end:raise runtime.Refuse('admission-deadline-expired-after-callback')

def main():
    def interrupted(signum, frame):
        raise runtime.Refuse("normal-admission-signalled")
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    p=argparse.ArgumentParser();p.add_argument('--flags',required=True);p.add_argument('--id',required=True)
    p.add_argument('--plan',required=True);p.add_argument('normal',nargs=argparse.REMAINDER)
    a=p.parse_args();normal=a.normal[1:] if a.normal[:1]==['--'] else a.normal
    if not normal:raise runtime.Refuse('normal-admission-command-required')
    plan=runtime.read_record(a.plan)
    absolute_end=runtime.gap_policy.epoch(runtime.parse_grant(plan[1])['end'])
    if os.environ.get('FILLER_END'):absolute_end=min(absolute_end,int(os.environ['FILLER_END']))
    def admission():
        run_normal(normal,absolute_end)
        if plan!=runtime.read_record(a.plan):raise runtime.Refuse('final-plan-changed')
    with serial.PublicationLease(a.flags,deadline_epoch=absolute_end) as lease:
        runtime.publish_under_owner_lease(a.flags,a.id,plan[1],admission,lease=lease,
            adopted=runtime.OWNER_ADOPTED and serial.ALL_PRODUCERS_BOUND)
if __name__=='__main__':
    try:main()
    except (runtime.Refuse,OSError,ValueError) as error:
        print('refuse: '+str(error),file=sys.stderr);sys.exit(6)

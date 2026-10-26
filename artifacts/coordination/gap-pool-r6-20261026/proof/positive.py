#!/usr/bin/env python3
"""ONLY inside reviewed official full-quarter grant. Private HOLD/claim fixtures."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

def stop_signal(signum, frame):
    raise SystemExit(143)
signal.signal(signal.SIGTERM, stop_signal)
signal.signal(signal.SIGINT, stop_signal)
def real_guard():
    assert not list(Path("/mnt/raid0/llm/tmp/compute-flags").glob("HOLD_*")), "canonical HOLD appeared"
    assert not Path("/mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024").exists()
    assert not Path(os.environ["FILLER_STOPFILE"]).exists()
    assert int(time.time()) < int(os.environ["FILLER_DEADLINE"])-30
from positive_row import build_positive_row, assert_canonical_affinity
PAYLOAD=Path(__file__).resolve().parent.parent/'scripts/coordination'
OUT=Path(__file__).resolve().parent/'results'
OUT.mkdir(exist_ok=True)
now=int(time.time())
outer_end=int(os.environ['FILLER_END'])
assert int(os.environ['FILLER_DEADLINE']) < outer_end
assert now+690 < int(os.environ['FILLER_DEADLINE']), 'insufficient real grant reserve'
cpus=sorted(os.sched_getaffinity(0));physical={c%96 for c in cpus}
canonical_region=os.environ["POSITIVE_CANONICAL_REGION"]
assert_canonical_affinity(cpus,canonical_region)
assert len(physical)==24 and len({c//24 for c in physical})==1, 'actual affinity not one full quarter'
q='q'+str(min(physical)//24)
assert os.environ.get('FILLER_ID')=='gap-pool-consolidated-positive-20261026'

private=OUT/'private';private.mkdir(exist_ok=False)
for name in ('gap_runtime_v1.py','gap_policy.py','validate_fillers.py','gap_serialization_v1.py','engine_state_v2_consolidation_PROPOSED.py','filler_run11.sh','filler_lib.sh'):
    shutil.copy2(PAYLOAD/name,private/name)
for name,old,new in (('gap_runtime_v1.py','OWNER_ADOPTED = False','OWNER_ADOPTED = True'),('gap_serialization_v1.py','ALL_PRODUCERS_BOUND = False','ALL_PRODUCERS_BOUND = True')):
    p=private/name;text=p.read_text();assert text.count(old)==1
    p.chmod(0o600);p.write_text(text.replace(old,new))
sys.path.insert(0,str(private))
import gap_runtime_v1 as runtime
import gap_serialization_v1 as serial
flags=private/'flags';flags.mkdir();(flags/'grants').mkdir()
row_id='fixture-positive-full-quarter'
trace=private/'callbacks.trace'
row=build_positive_row(row_id,private,q,os.getpid())
(flags/'FILLERS.md').write_text('| '+' | '.join(runtime.validator.COLUMNS)+' |\n| '+' | '.join(row)+' |\n')
start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now))
end=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now+600))
quiet=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now+900))
actual=f'regions={q} start={start} end={end}\n'.encode()
with serial.PublicationLease(flags) as lease:
    serial.hold_write(lease,'HOLD_SYNTHETIC_PRIVATE',b'by=fixture\n',quiet)
    runtime.publish_under_owner_lease(flags,row_id,actual,lambda:trace.write_text('writer-callback\n'),
        lease=lease,adopted=True,legacy=private/'absent-legacy')
rl=private/'fake-claim.sh';rl.write_text('#!/bin/bash\nwhile [ "$1" != -- ]; do shift; done\nshift\nexec "$@"\n');rl.chmod(0o700)
child=private/'child.py';child.write_text('import json,os,time\nfrom pathlib import Path\np=Path(__file__).parent\na=sorted(os.sched_getaffinity(0))\nassert len({c%96 for c in a})==24\n(p/"child.json").write_text(json.dumps({"pid":os.getpid(),"cpus":a}))\ntime.sleep(120)\n')
env={k:v for k,v in os.environ.items() if not k.startswith('FILLER_')}
env.update(FILLER_FLAGS_DIR=str(flags),FILLER_GRANTS_DIR=str(flags/'grants'),FILLERS_MD=str(flags/'FILLERS.md'),FILLER_STATE_DIR=str(private/'state'),FILLER_RL=str(rl),FILLER_POLL='1')
log=(OUT/'engine-positive.log').open('w')
proc=subprocess.Popen(['/bin/bash',str(private/'filler_run11.sh'),'--id',row_id,'--class','cpu','--min-window','300','--stop',str(private/'STOP'),'--workdir',str(private),'--precond-cmd',f'echo precondition-callback >> {trace}','--complete-cmd','false','--cmd',f'exec /usr/bin/python3 -B {child}'],env=env,stdout=log,stderr=log)
captured=None
try:
    until=time.monotonic()+15
    while not (private/'child.json').exists() and time.monotonic()<until:
        real_guard()
        assert int(time.time()) < int(os.environ['FILLER_DEADLINE'])-30
        if proc.poll() is not None: raise AssertionError('private engine exited before positive body')
        time.sleep(.05)
    receipt=json.loads((private/'child.json').read_text());captured=receipt['pid']
    assert {c%96 for c in receipt['cpus']}==physical
    assert 'precondition-callback' in trace.read_text()
    with serial.PublicationLease(flags) as lease:
        serial.hold_write(lease,'HOLD_ADDED_LEGACY_PRIVATE',b'legacy\n')
    until=time.monotonic()+30
    while proc.poll() is None and time.monotonic()<until:
        real_guard();time.sleep(.1)
    assert proc.poll() is not None, "private engine stop timed out"
    ended=(flags/'grants'/(row_id+'.ended')).read_text()
    assert 'rc=6' in ended and 'hold-admission-changed' in ended
    ended_lines=ended.splitlines()
    assert len(ended_lines)==7, "combined EVL native seven-line receipt missing"
    native_fields=dict(line.split("=",1) for line in ended_lines[1:])
    assert native_fields["job_id"]==row_id and native_fields["owner"]=="fixture-owner"
    assert native_fields["step"]=="job-run" and float(native_fields["estimated_wall_s"])==600
    assert native_fields["regions"]==q and runtime.gap_policy.epoch(native_fields["started"])>=now
    source_hashes={name:hashlib.sha256((PAYLOAD/name).read_bytes()).hexdigest() for name in ("filler_run11.sh","engine_state_v2_consolidation_PROPOSED.py","gap_runtime_v1.py","gap_policy.py","gap_serialization_v1.py","filler_lib.sh","validate_fillers.py")}
    private_source_hashes={name:hashlib.sha256((private/name).read_bytes()).hexdigest() for name in source_hashes}
    proof=subprocess.run(['ps','-o','stat=','-p',str(captured)],capture_output=True,text=True)
    assert not proof.stdout.strip(), 'owned captured child still visible'
    (OUT/'VERDICT.json').write_text(json.dumps({'verdict':'PASS','decided_proposition':'Captured combined current9+EVL10+GAP source satisfies private canonical-quarter affinity, HOLD refusal and owned-child drain with native EVL ended fields','synthetic':True,'combined_candidate':True,'baseline_live9_sha256':'dedaccb7d7874dd2c709c7e9eacd734fb62740a914ac72c982bfc9135107e1cb','baseline_evl10_commit':'058714567e2fcb0dc8f6eaac9fae4a1afc277aed','source_hashes':source_hashes,'private_source_hashes':private_source_hashes,'native_ended_fields':native_fields,'native_first_line':ended_lines[0],'canonical_region':canonical_region,'quarter':q,'outer_id':os.environ['FILLER_ID'],'actual_affinity':cpus,'child_affinity':receipt['cpus'],'captured_child':captured,'ps_stdout':proof.stdout,'private_engine_rc':proc.returncode,'private_hold_only':True,'canonical_adoption':False,'outer_end':outer_end,'finished':int(time.time())},indent=2)+'\n')
finally:
    if proc.poll() is None:
        proc.terminate()
        try:proc.wait(timeout=20)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    if captured is not None:
        proof=subprocess.run(['ps','-o','stat=','-p',str(captured)],capture_output=True,text=True)
        if proof.stdout.strip(): raise AssertionError('owned child drain not proven')
    log.close()

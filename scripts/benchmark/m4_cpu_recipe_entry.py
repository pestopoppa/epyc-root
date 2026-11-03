#!/usr/bin/env python3
"""Guarded entry for the narrowly scoped M4 Q38FN recipe diagnostic."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import shutil
import time

ROOT=Path(__file__).resolve().parents[2]
OWNERSHIP=ROOT/'scripts/benchmark/m4_cpu_ownership'
sys.path.insert(0,str(OWNERSHIP)); sys.path.insert(0,str(Path(__file__).resolve().parent))
import entry
import watch


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def check_plan(plan_path: Path, expected_sha: str, output: Path | None) -> dict:
    """The seal is the plan digest; the plan itself seals the image manifests (compare.verify).

    The harness never hashes its own source and needs no per-revision tree copy."""
    if _sha(plan_path)!=expected_sha: raise ValueError('plan digest mismatch')
    plan=json.loads(plan_path.read_bytes())
    if not isinstance(plan,dict): raise ValueError('plan must be an object')
    if output is not None and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('output must be an existing empty directory')
    return plan


def qualification_worker() -> int:
    """One synthetic unit inside the actual watcher; never emits a measurement."""
    if (os.environ.get('FILLER_DRYRUN') != '1' or os.environ.get('FILLER_SMOKE') != '1'
            or not os.environ.get('M4_OWNED_CGROUP')):
        raise ValueError('fixture worker requires guarded smoke')
    dd=Path(os.environ['FILLER_DRYRUN_DIR']).resolve(strict=True)
    result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    if (not result.is_absolute() or result.name != 'native-result.json'
            or result.parent.parent != dd/'native-attempts' or not result.parent.name.startswith('attempt-')
            or result.parent.resolve(strict=True) != result.parent):
        raise ValueError('invalid qualification nonce path')
    with result.open('x') as f:
        json.dump({'schema':'epyc.m4.cpu.recipe.qualification.v1','qualification_only':True,
                   'measurement':False},f);f.write('\n');f.flush();os.fsync(f.fileno())
    while True: time.sleep(.1)


def qualification(a, row: str) -> int:
    """Exercise the real ownership watcher with a rowflow-only fixture."""
    if os.environ.get('FILLER_SMOKE') != '1': raise ValueError('fixture only allowed during smoke')
    dd=Path(os.environ['FILLER_DRYRUN_DIR']).resolve(strict=True)
    # Dry-run only: the smoke's STOP must be the one the smoke harness touches.
    if str(a.stop) != os.environ['FILLER_STOPFILE'] or int(a.deadline) != int(os.environ['FILLER_DEADLINE']):
        raise ValueError('qualification STOP or deadline mismatch')
    cpus=os.environ['FILLER_CPUS']
    entry._grant(a.grant,cpus,a.deadline,allow_dryrun=True,expected_row_id=row)
    result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    if (result.name != 'native-result.json' or result.parent.parent != dd/'native-attempts'
            or not result.parent.name.startswith('attempt-') or result.parent.resolve(strict=True) != result.parent):
        raise ValueError('invalid qualification attempt path')
    output=result.parent/'watch';output.mkdir()
    plan=result.parent/'fixture-plan.json'
    payload={'schema':'epyc.m4.cpu_entry_fixture.v1','mode':'fixture','row_id':row,
             'region':cpus,'fixture':str(Path(__file__).resolve()),'fixture_sha256':_sha(Path(__file__))}
    with plan.open('x') as f: json.dump(payload,f,sort_keys=True)
    argv=sys.argv
    try:
        sys.argv=['entry.py','--plan',str(plan),'--plan-sha256',_sha(plan),'--grant',str(a.grant),
                  '--stop',str(a.stop),'--hold',str(a.hold),'--output',str(output),
                  '--deadline',str(a.deadline)]
        os.environ['M4_QUALIFICATION_WORKER']='1'
        rc=entry.main()
        watch_result=json.loads((output/'watch-result.json').read_bytes())
        if (a.stop.exists() and watch_result.get('status') == 'closed'
                and watch_result.get('containment_empty') is True and watch_result.get('reason') == 'STOP'
                and Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).is_file()):
            return 75
        return rc
    finally:
        sys.argv=argv;os.environ.pop('M4_QUALIFICATION_WORKER',None)


def main() -> int:
    if os.environ.get('M4_QUALIFICATION_WORKER') == '1':
        return qualification_worker()
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','grant','stop','hold','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--plan-sha256',required=True);p.add_argument('--deadline',type=float,required=True)
    a=p.parse_args()
    try:
        if os.environ.get('FILLER_DRYRUN') == '1':
            return qualification(a,entry._row_id(os.environ.get('FILLER_ID')))
        plan=check_plan(a.plan,a.plan_sha256,a.output)
        row=entry._row_id(plan.get('row_id'))
        if os.environ.get('FILLER_ID') not in (None,'',row): raise ValueError('FILLER_ID differs from the plan row')
        if plan.get('status')!='REVIEWED_DIAGNOSTIC':
            raise ValueError('diagnostic plan not reviewed')
        if not a.hold.is_dir() or a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('STOP or HOLD before entry')
        resource=plan.get('resource')
        if not isinstance(resource,dict): raise ValueError('resource envelope missing')
        needed,reserve,output_bytes,minimum=(resource.get(k) for k in ('max_ram_bytes','memory_reserve_bytes','estimated_output_bytes','min_remaining_s'))
        if any(type(v) is not int for v in (needed,reserve,output_bytes,minimum)) or needed<=0 or reserve<0 or output_bytes<0 or minimum<300:
            raise ValueError('invalid resource envelope')
        mem=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line)
        if int(mem['MemAvailable'].split()[0])*1024 < needed+reserve: raise ValueError('insufficient available RAM')
        if shutil.disk_usage('/mnt/raid0/llm').free-output_bytes < 150*1024**3: raise ValueError('insufficient disk headroom')
        if a.deadline-time.time()<minimum: raise ValueError('insufficient remaining grant')
        entry._grant(a.grant,'0-95',a.deadline,require_host_holds=True)
        original=_sha(a.grant)
        # The caller's `region-lock run --regions q0,q1,q2,q3` holds the lease (the kernel
        # releases its flock on exit); the workload runs on the physical cores it covers.
        os.sched_setaffinity(0,set(range(96)))
        if time.time()>=a.deadline: raise ValueError('deadline expired')
        env=dict(os.environ,M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup',FILLER_ID=row)
        command=[sys.executable,'-B',str(ROOT/'scripts/benchmark/m4_cpu_recipe_compare.py'),
                 '--plan',str(a.plan),'--plan-sha256',a.plan_sha256,'--output',str(a.output/'capture'),
                 '--grant',str(a.grant),'--stop',str(a.stop),'--hold',str(a.hold),'--deadline',str(a.deadline),'--execute']
        rc=watch.run(command,a.grant,a.stop,a.hold,a.deadline,a.output,env)
        entry._grant(a.grant,'0-95',a.deadline,require_host_holds=True)
        if rc or _sha(a.grant)!=original or a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('diagnostic interrupted or final grant changed')
        return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        print(f'REFUSED: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())

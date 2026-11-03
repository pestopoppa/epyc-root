#!/usr/bin/env python3
"""Guarded entry for the narrowly scoped M4 Q38FN recipe diagnostic."""
from __future__ import annotations
import argparse
import fcntl
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
import m4_cpu_recipe_enrollment as enrollment


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def check_enrollment(plan_path: Path, expected_sha: str, row_id: str, output: Path | None) -> None:
    if not enrollment.ENABLED or not enrollment.SOURCE_SEALS:
        raise ValueError('reviewed diagnostic enrollment absent')
    if (str(plan_path.resolve(strict=True))!=enrollment.PLAN_PATH or expected_sha!=enrollment.PLAN_SHA256
            or row_id!=enrollment.ROW_ID or _sha(plan_path)!=expected_sha):
        raise ValueError('diagnostic plan or row enrollment mismatch')
    if output is not None:
        root=Path(enrollment.OUTPUT_ROOT).resolve(strict=True)
        if output.resolve(strict=True).parent!=root or any(output.iterdir()):
            raise ValueError('diagnostic output must be a fresh enrolled child')
    producer=ROOT/'scripts/benchmark/m4_cpu_producer'
    required={str(Path(__file__).resolve()),str((ROOT/'scripts/benchmark/m4_cpu_recipe_compare.py').resolve()),
              *(str((OWNERSHIP/name).resolve()) for name in ('entry.py','watch.py','lease_owner.py','m4_cgroup_guard.py','owned.py')),
              *(str((producer/name).resolve()) for name in ('capture.py','native/k35_stack_context_matrix_runner.py','native/compare_v9_promotion_arms.py'))}
    if not required.issubset(enrollment.SOURCE_SEALS): raise ValueError('diagnostic source seals incomplete')
    for source,digest in enrollment.SOURCE_SEALS.items():
        path=Path(source)
        if not path.is_absolute() or not path.is_file() or _sha(path)!=digest:
            raise ValueError(f'diagnostic source changed: {source}')


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
    # Exercise the REAL ownership spawn path with the exact wrapper shape of a cell's server_argv
    # (env assignments -> numactl -> taskset -> absolute binary), so an argv the gate refuses fails the smoke, not the
    # full-host run (inf22 r1, 2026-11-03: 'unbound bare executable' only surfaced 7 s into the real run).
    import owned as m4_owned, subprocess
    cpus=os.environ['FILLER_CPUS']
    argv=['env','LD_LIBRARY_PATH='+str(dd),'GGML_FA_SPLIT_KV=0','GGML_FUSED_DECODE_OFF=1','GGML_NOHUGEPAGE_PROCESS=1',
          'GGML_IQK=1','ROCR_VISIBLE_DEVICES=-1','HIP_VISIBLE_DEVICES=-1','CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=1',
          'numactl','--interleave=all','--','taskset','-c',cpus,sys.executable,'-B','-c','pass']
    child,fd,_birth=m4_owned.spawn(argv,env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        if child.wait(timeout=60)!=0: raise ValueError('wrapped spawn smoke exited non-zero')
    finally:
        os.close(fd)
    with result.open('x') as f:
        json.dump({'schema':'epyc.m4.cpu.recipe.qualification.v1','qualification_only':True,
                   'measurement':False,'spawn_path_exercised':True},f);f.write('\n');f.flush();os.fsync(f.fileno())
    while True: time.sleep(.1)


def qualification(a, row: str) -> int:
    """Exercise the real ownership watcher with a rowflow-only fixture."""
    if os.environ.get('FILLER_SMOKE') != '1': raise ValueError('fixture only allowed during smoke')
    check_enrollment(a.plan,a.plan_sha256,row,None)
    dd=Path(os.environ['FILLER_DRYRUN_DIR']).resolve(strict=True)
    if (a.grant != dd/'grants'/(row+'.grant') or a.stop != dd/'stop'
            or a.hold != Path(os.environ['FILLER_FLAGS_DIR']) or str(a.stop) != os.environ['FILLER_STOPFILE']
            or int(a.deadline) != int(os.environ['FILLER_DEADLINE'])):
        raise ValueError('qualification grant or control path mismatch')
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
                  '--deadline',str(a.deadline),'--owner-pid',str(a.owner_pid),'--owner-birth',str(a.owner_birth)]
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
    p.add_argument('--owner-pid',type=int,required=True);p.add_argument('--owner-birth',type=int,required=True)
    a=p.parse_args()
    try:
        row=entry._row_id(os.environ.get('FILLER_ID'))
        if a.owner_pid!=os.getppid() or watch.m4_cgroup_guard.birth(a.owner_pid)!=a.owner_birth:
            raise ValueError('outer lease owner mismatch')
        if os.environ.get('FILLER_DRYRUN') == '1':
            return qualification(a,row)
        check_enrollment(a.plan,a.plan_sha256,row,a.output)
        sys.path.insert(0,str(ROOT/'scripts/vidya'))
        from adapters import m4_cpu_speed as reader
        reader_config=reader._trusted_config_for(a.output/'capture'/'future'/'process-captures'/'future.json')
        if (reader_config.producer_root != ROOT/'scripts/benchmark/m4_cpu_producer'
                or reader_config.diagnostic_plan_sha256 != a.plan_sha256):
            raise ValueError('diagnostic reader enrollment mismatch')
        plan=json.loads(a.plan.read_bytes())
        if plan.get('row_id')!=row or plan.get('status')!='REVIEWED_DIAGNOSTIC':
            raise ValueError('diagnostic plan not reviewed for this row')
        if a.grant!=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(row+'.grant'):
            raise ValueError('wrong canonical grant path')
        if (a.hold!=Path('/mnt/raid0/llm/tmp/compute-flags') or not a.hold.is_dir()
                or str(a.stop)!=os.environ.get('FILLER_STOPFILE') or a.stop.exists()
                or any(a.hold.glob('HOLD_*'))): raise ValueError('unbound STOP or HOLD')
        if int(a.deadline) != int(os.environ.get('FILLER_DEADLINE','0')):
            raise ValueError('deadline differs from admitted row')
        resource=plan.get('resource')
        if not isinstance(resource,dict): raise ValueError('resource envelope missing')
        needed,reserve,output_bytes,minimum=(resource.get(k) for k in ('max_ram_bytes','memory_reserve_bytes','estimated_output_bytes','min_remaining_s'))
        if any(type(v) is not int for v in (needed,reserve,output_bytes,minimum)) or needed<=0 or reserve<0 or output_bytes<0 or minimum<300:
            raise ValueError('invalid resource envelope')
        mem=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line)
        if int(mem['MemAvailable'].split()[0])*1024 < needed+reserve: raise ValueError('insufficient available RAM')
        if shutil.disk_usage('/mnt/raid0/llm').free-output_bytes < 150*1024**3: raise ValueError('insufficient disk headroom')
        if a.deadline-time.time()<minimum: raise ValueError('insufficient remaining grant')
        # Operator co-residency policy 2026-10-22: strict GPU-quiet only for decision-grade champion baselines and AK
        # keep windows. This descriptive diagnostic may share the host with a GPU job (lease 'shared'); the mode and
        # the grant's holds are recorded in HOST-COTENANCY.json beside the capture, never assumed.
        quiet_mode=os.environ.get('M4_GPU_QUIET_MODE')
        if quiet_mode not in ('shared','exclusive'): raise ValueError('GPU-quiet lease mode missing or invalid')
        if sorted(os.sched_getaffinity(0))!=list(range(96)): raise ValueError('full physical-host affinity required')
        entry._grant(a.grant,'0-95',a.deadline,require_host_holds=True)
        original=_sha(a.grant)
        fds=[int(x) for x in os.environ.get('M4_LEASE_FDS','').split(',') if x]
        expected={f'cpu_region.GLOBAL.q{i}.lock' for i in range(4)}|{'gpu_quiet.lock'}; found={}
        for fd in fds:
            path=Path(os.readlink(f'/proc/self/fd/{fd}'))
            if path.parent==Path('/mnt/raid0/llm/tmp') and path.name in expected:
                if path.name in found: raise ValueError('duplicate lease descriptor')
                target=os.stat(path);actual=os.fstat(fd)
                if (target.st_dev,target.st_ino)!=(actual.st_dev,actual.st_ino): raise ValueError('lease inode changed')
                found[path.name]=fd
        if set(found)!=expected: raise ValueError('full exclusive lease descriptors missing')
        for name,fd in found.items():
            operation=fcntl.LOCK_SH if name=='gpu_quiet.lock' and quiet_mode=='shared' else fcntl.LOCK_EX
            fcntl.flock(fd,operation|fcntl.LOCK_NB)
        if time.time()>=a.deadline: raise ValueError('deadline expired')
        env=dict(os.environ,M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup',
                 M4_OUTER_OWNER_PID=str(a.owner_pid),M4_OUTER_OWNER_BIRTH=str(a.owner_birth))
        command=[sys.executable,'-B',str(ROOT/'scripts/benchmark/m4_cpu_recipe_compare.py'),
                 '--plan',str(a.plan),'--plan-sha256',a.plan_sha256,'--output',str(a.output/'capture'),'--execute']
        holds=dict(f.split('=',1) for f in a.grant.read_text().split()).get('holds','').split(',')
        gpu_quiet_held=quiet_mode=='exclusive' and 'gpu-quiet' in holds
        with (a.output/'HOST-COTENANCY.json').open('x') as f:
            json.dump({'schema':'epyc.m4.q38.host-cotenancy.v1','gpu_quiet_lease':quiet_mode,'grant_holds':sorted(holds),
                       'gpu_quiet_held':gpu_quiet_held,'evidence_grade':'gpu-quiet held (still descriptive only)' if gpu_quiet_held else
                       'indicative: shares host with GPU job (operator co-residency policy 2026-10-22)'},f,sort_keys=True)
            f.write('\n');f.flush();os.fsync(f.fileno())
        rc=watch.run(command,a.grant,a.stop,a.hold,a.deadline,a.output,env)
        entry._grant(a.grant,'0-95',a.deadline,require_host_holds=True)
        if reader._trusted_config_for(a.output/'capture'/'future'/'process-captures'/'future.json') != reader_config:
            raise ValueError('diagnostic reader enrollment changed during work')
        if rc or _sha(a.grant)!=original or a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('diagnostic interrupted or final grant changed')
        return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        print(f'REFUSED: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())

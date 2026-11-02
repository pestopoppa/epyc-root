#!/usr/bin/env python3
"""Qualify one M4 GPU row, retaining only captured-birth/cgroup cleanup.

Run as a child of region-lock holding physical q3 and gpu-quiet exclusive. This
adapts only this invocation of rowflow: its row-name orphan scan is disabled
because a matching argv does not establish ownership. The engine and watcher
still drain their captured descendants, and PASS is withheld until every
started watch cgroup reports empty and each recorded PID/birth is absent.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'scripts/coordination/rowflow'))
import publish_row as pub


def parent_claim():
    raw=Path(f'/proc/{os.getppid()}/cmdline').read_bytes().split(b'\0')
    args=[x.decode(errors='replace') for x in raw if x]
    if ('src.runtime.region_lock_cli' not in ' '.join(args) or '--cpu-list' not in args
            or args[args.index('--cpu-list')+1] != '72-95' or '--gpu-quiet' not in args
            or args[args.index('--gpu-quiet')+1] != 'exclusive'):
        raise RuntimeError('outer q3 and exclusive GPU claim required')


def audit_watches(plan):
    started=0
    for cell in plan['cells'].values():
        watch=Path(cell['watch_result_path']); directory=watch.parent
        if not directory.exists(): continue
        started+=1
        value=json.loads(watch.read_bytes())
        if (value.get('status')!='closed' or value.get('containment_empty') is not True
                or value.get('cleanup_error')):
            raise RuntimeError('watcher did not prove cgroup drain')
        registry=directory/'server-pids.txt'
        for line in registry.read_text().splitlines():
            pid,birth=line.split()
            if not (pid.isdecimal() and birth.isdecimal()): raise RuntimeError('invalid captured process identity')
            try:
                fields=Path('/proc',pid,'stat').read_text().rsplit(')',1)[1].split()
            except FileNotFoundError:
                continue
            if fields[0] != 'Z' and fields[19]==birth:
                raise RuntimeError('captured server still alive')
    if not started: raise RuntimeError('no watcher was started')
    return started


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id',required=True);parser.add_argument('--flags',default='/mnt/raid0/llm/tmp/compute-flags')
    args=parser.parse_args();rid=args.id
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]+',rid):raise ValueError('invalid row id')
    parent_claim()
    flags=args.flags
    ready=Path(pub.rf.ready_path(flags,rid));unpublished=Path(pub.unpublished_path(flags,rid));queued=Path(pub.queued_path(flags,rid))
    if ready.exists() or not unpublished.is_file() or not queued.is_file():
        raise RuntimeError('expected owned queued state missing')
    sys.path.insert(0,str(HERE));import launch_gpu_aa as launch
    trust,aa,native,spec,digest,qual=launch.load()
    if qual or aa['row']['id'] != rid:raise RuntimeError('real row binding mismatch')
    old=os.environ.get('FILLER_DRYRUN');os.environ['FILLER_DRYRUN']='1'
    try:
        dry_trust,dry_aa,dry_native,_,_,dry=launch.load()
    finally:
        if old is None:os.environ.pop('FILLER_DRYRUN',None)
        else:os.environ['FILLER_DRYRUN']=old
    if not dry or dry_aa['row']['id'] != rid:raise RuntimeError('qualification row mismatch')
    # SOURCE_SEALS include this wrapper and the rowflow source itself.
    seals={str(p.resolve()):h for p,h in trust.sources}
    import hashlib
    for path in (Path(__file__).resolve(),Path(pub.__file__).resolve(),Path(pub.rf.__file__).resolve()):
        if seals.get(str(path)) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise RuntimeError('smoke source not enrolled')
    # No result from a previous attempt is reusable.
    for cell in dry_native['cells'].values():
        if Path(cell['watch_result_path']).parent.exists():raise RuntimeError('qualification attempt already used')
    os.replace(unpublished,ready)
    prior_scan=pub.rf.row_dir_procs;prior_atomic=pub.rf.atomic_json;pending=[]
    pass_path=pub.rf.pass_path(flags,rid)
    def defer_pass(path,data):
        if str(path)==str(pass_path):pending.append((path,data))
        else:prior_atomic(path,data)
    # The generic scan can signal unrelated parents whose argv contains rid.
    # Only the harness's birth-captured descendants and watch cgroups are owned.
    pub.rf.row_dir_procs=lambda _rid,_dirs:{}
    pub.rf.atomic_json=defer_pass
    verdict='FAIL'
    try:
        verdict,msg=pub.run_smoke(flags,rid,'mi210_0,184-191',300)
        if verdict=='PASS':
            audit_watches(dry_native)
            if len(pending)!=1:raise RuntimeError('expected one deferred PASS receipt')
            prior_atomic(*pending[0])
        print('TARGETED_SMOKE',verdict,msg,flush=True)
        return 0 if verdict=='PASS' else 1
    except BaseException:
        pub.unpublish(flags,rid)
        raise
    finally:
        pub.rf.row_dir_procs=prior_scan;pub.rf.atomic_json=prior_atomic
        if queued.exists():queued.unlink()

if __name__=='__main__':raise SystemExit(main())

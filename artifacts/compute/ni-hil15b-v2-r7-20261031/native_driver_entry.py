#!/usr/bin/env python3
"""Run the unchanged canonical HIL15a main/run_all; observe graph calls only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
APP = Path('/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator')
DRIVER = APP/'scripts/trace/hil15a_flagon_run.py'
SHA = '75abff0842a550051b3a25f3bf079a505044120a9ee57e80cc08ef2661bb4c63'


def append_sync(path, row):
    with path.open('a') as f:
        f.write(json.dumps(row, sort_keys=True)+'\n')
        f.flush()
        os.fsync(f.fileno())


def main():
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest() != SHA:
        raise SystemExit('canonical driver source drift')
    if len(sys.argv) < 4 or sys.argv[1] not in ('full','qualification'):
        raise SystemExit('usage: native_driver_entry.py full|qualification LEDGER -- native CLI args')
    mode, ledger = sys.argv[1], Path(sys.argv[2])
    args = sys.argv[4:] if sys.argv[3] == '--' else sys.argv[3:]
    sys.path.insert(0,str(APP))
    from src.graph import graph
    original = graph.run_task
    exposed = ledger.parent/'COHORT-EXPOSED.json'

    async def observed(*a, **kw):
        state = a[0] if a else kw.get('state')
        rid = str(state.task_id)
        if mode == 'full' and not exposed.exists():
            temp=exposed.with_suffix('.json.tmp')
            temp.write_text(json.dumps({'scope':'frozen20x3','first_run_id':rid,
                 'taskset_sha256':'0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312',
                 'at_epoch':time.time()},indent=2)+'\n')
            os.replace(temp,exposed)
        append_sync(ledger,{'event':'intent','run_id':rid,'at_epoch':time.time()})
        try:
            result=await original(*a,**kw)
        except BaseException as exc:
            append_sync(ledger,{'event':'exception','run_id':rid,'type':type(exc).__name__,
                                'at_epoch':time.time()})
            raise
        append_sync(ledger,{'event':'returned','run_id':rid,'at_epoch':time.time()})
        return result

    graph.run_task=observed
    spec=importlib.util.spec_from_file_location('hil15a_canonical',DRIVER)
    native=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=native
    spec.loader.exec_module(native)
    return native.main(args)


if __name__=='__main__':
    raise SystemExit(main())

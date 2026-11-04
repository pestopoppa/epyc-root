#!/usr/bin/env python3
"""Claim-scoped, fake-upstream OpenCode diagnostic; STOP drains owned container."""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from scripts.benchmark.opencode_fake_upstream_probe import run_probe

ROOT = Path('/mnt/raid0/llm/tmp/evl46-opencode-schema-20261102')
IMAGE = 'sha256:e8c7d0023b96514a4c94b07bb978139f4d186552b40e5fc54cd90196fe4757a7'


class StopRequested(Exception):
    pass


def stop(_signal, _frame):
    raise StopRequested()


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    stop_path = Path(os.environ['FILLER_STOPFILE'])
    cpus = os.environ['FILLER_CPUS']
    if stop_path.exists() or int(os.environ['FILLER_DEADLINE']) - time.time() < 100:
        return 75
    finished = threading.Event()
    def watch_stop():
        while not finished.wait(0.25):
            if stop_path.exists() or time.time() >= int(os.environ['FILLER_DEADLINE']):
                os.kill(os.getpid(), signal.SIGTERM)
                return
    watcher = threading.Thread(target=watch_stop, daemon=True)
    watcher.start()
    try:
        result = run_probe(IMAGE, cpus, str(ROOT))
        if (result.get('version') != '1.18.31' or result.get('binary_sha256') !=
                'f9dab32248695e9ebd56b16a1921798fd85112cf5a69c7dfd0cabc1e17be4a11'):
            raise RuntimeError('OpenCode binary content or version mismatch')
        subprocess.run(['sha256sum', '-c', str(ROOT / 'runtime.sha256')], cwd=ROOT,
                       stdout=subprocess.DEVNULL, check=True)
        result.update({'row_id': os.environ['FILLER_ID'],
                       'dry_run': os.environ.get('FILLER_DRYRUN') == '1',
                       'execution_scope': 'actual OpenCode; fake model endpoint; no inference',
                       'cpuset': cpus})
        destination = Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH') or ROOT / 'RESULT.json')
        temp = destination.with_name(destination.name + '.tmp')
        temp.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps(result, sort_keys=True) + '\n')
        temp.replace(destination)
        return 0
    except StopRequested:
        return 75
    finally:
        finished.set()
        watcher.join(2)


if __name__ == '__main__':
    sys.exit(main())

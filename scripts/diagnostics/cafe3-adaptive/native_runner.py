#!/usr/bin/env python3
"""Grant-only native server supervisor; process capture is never a P9 verdict."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import launch_context as context


def reap(child):
    """Terminate only the child captured by this invocation and prove reaping."""
    if child.poll() is None:
        child.terminate()
    try:
        return child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        return child.wait(timeout=5)


def run(manifest_path, digest, argv, log_path, result_path):
    # Validate before creating outputs or starting a process. In particular this
    # refuses the row publisher's smoke mode; it must never load models in smoke.
    plan = context.validate_launch_context(manifest_path, digest, argv)
    stop = Path(os.environ['FILLER_STOPFILE'])
    deadline = int(os.environ['FILLER_DEADLINE'])
    grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (os.environ['FILLER_ID'] + '.grant')
    child = None
    started = time.time()
    cutoff = None
    samples = []
    # Exclusive outputs prevent accidental overwrite of a retained capture.
    with Path(result_path).open('x') as result, Path(log_path).open('x') as log:
        try:
            # Recheck the live boundary after potentially expensive validation.
            if stop.exists() or time.time() >= deadline:
                raise ValueError('STOP/deadline before spawn')
            if grant.with_suffix('.ended').exists() or grant.with_suffix('.complete').exists():
                raise ValueError('grant ended before spawn')
            child = subprocess.Popen(plan['argv'], env=plan['env'], stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, close_fds=True)
            try:
                while child.poll() is None:
                    # Samples overlap child execution. These are raw mappings,
                    # not a claim of GPU residency or complete backend coverage.
                    if len(samples) < 2:
                        try:
                            maps = Path(f'/proc/{child.pid}/maps').read_text()
                            if 'libggml' in maps:
                                samples.append(dict(at=time.time(), maps=maps))
                        except FileNotFoundError:
                            pass  # exit race; never infer absence from it
                    if stop.exists():
                        cutoff = 'STOP'
                    elif time.time() >= deadline:
                        cutoff = 'deadline'
                    elif grant.with_suffix('.ended').exists() or grant.with_suffix('.complete').exists():
                        cutoff = 'grant-ended'
                    if cutoff:
                        break
                    try:
                        child.wait(timeout=min(.25, max(.001, deadline - time.time())))
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                rc = reap(child)
            record = dict(schema='epyc.cafe3.process-capture.v1', status='UNASSESSED',
                          context_sha256=digest, argv=plan['argv'], env=plan['env'],
                          pid=child.pid, started=started, ended=time.time(), rc=rc,
                          cutoff=cutoff, child_reaped=child.poll() is not None,
                          mapping_samples=samples, log=str(Path(log_path).resolve()))
            json.dump(record, result, indent=2, allow_nan=False)
            result.write('\n')
            result.flush()
            os.fsync(result.fileno())
        except BaseException:
            if child is not None and child.poll() is None:
                reap(child)
            raise
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('sha256')
    parser.add_argument('argv_json')
    parser.add_argument('log')
    parser.add_argument('result')
    args = parser.parse_args()
    record = run(args.manifest, args.sha256, context.load(args.argv_json), args.log, args.result)
    # A clean process exit still says nothing about identity or P9.
    return 75 if record['cutoff'] else (0 if record['rc'] == 0 else 1)


if __name__ == '__main__':
    raise SystemExit(main())

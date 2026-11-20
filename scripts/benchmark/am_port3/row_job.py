"""Keeper-only entry point; seal smoke/refusal separately from model findings."""
import argparse
import json
import os
from pathlib import Path
import signal
import time

import pipeline


def request_stop(signum, _frame):
    # Unwind Executor's finally block, which terminates/reaps its own child.
    raise RuntimeError(f'keeper termination signal {signum}')


def run(plan_path, root, smoke):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    attempt = root / str(time.time_ns())
    result = dict(schema='epyc.am.row-result.v1', smoke=smoke, ok=False,
                  attempt=str(attempt), plan_sha256=pipeline.digest(plan_path))
    try:
        if smoke:
            plan = json.loads(Path(plan_path).read_text())
            tokens, _ = pipeline.validate(plan)
            attempt.mkdir()
            bindir = Path(plan['builds']['patched_hip']).parent / 'build/bin'
            config = attempt / 'control.json'
            pipeline.save(config, dict(mode='control', model=plan['model'],
                model_identity=plan['model_identity'], source_commit=plan['source_commit'],
                prefix_tokens=tokens['prefix_tokens'][:20],
                warmup_tokens=tokens['warmup_tokens'][:1],
                probe_tokens=tokens['probe_tokens'][:2], n_ctx=512,
                threads=plan['threads'], n_gpu_layers=plan['n_gpu_layers'],
                out=str(attempt / 'control')))
            executor = pipeline.Executor(attempt / 'execution', bindir, gpu=True,
                device=plan['device_vram_path'], timeout_s=180)
            pipeline.controls.run(bindir / 'am-control', config, bindir, execute=executor)
            # Catch changes during native execution as in the full pipeline.
            pipeline.validate(plan)
            if pipeline.digest(plan_path) != result['plan_sha256']:
                raise ValueError('plan changed during smoke')
            result.update(ok=True, status='SMOKE_PASS',
                          scope='patched HIP startup/control only; no fitted-cache quality verdict')
        else:
            measured = pipeline.run(plan_path, attempt)
            if measured.get('status') != 'MEASURED':
                raise ValueError('pipeline did not produce a measured terminal result')
            result.update(ok=True, status='MEASURED', stopped_at=measured['stopped_at'],
                          measured_result_sha256=pipeline.digest(attempt / 'RESULT.json'))
    except Exception as exc:
        result.update(status='REFUSED', error=f'{type(exc).__name__}: {exc}')
    (root / 'RESULT.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return 0 if result['ok'] else 3


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args(argv)
    smoke = bool(os.environ.get('FILLER_SMOKE') or os.environ.get('FILLER_SMOKE_T0'))
    previous = signal.signal(signal.SIGTERM, request_stop)
    try:
        return run(a.plan, Path(a.out) / ('smoke' if smoke else 'native'), smoke)
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    raise SystemExit(main())

"""Prospective matrix runner; invoke only through an admitted compute row.

The native worker accepts --plan, --cell-id and --output and writes JSON with
status plus the capture telemetry. No model preparation or hashing occurs here.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('precision_capture_runner', Path(__file__).with_name('capture.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def run_matrix(plan_path, output_dir):
    plan_path = Path(plan_path).absolute()
    plan, _ = capture._read(plan_path)
    capture._plan(plan)
    worker = plan['runner']
    argv, timeout = worker['argv'], worker['timeout_s']
    if (not isinstance(argv, list) or not argv
            or any(not isinstance(v, str) or not v for v in argv)
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('invalid native worker argv or timeout')
    directory = Path(output_dir).absolute()
    directory.mkdir(parents=True, exist_ok=False)
    opened_path = directory / 'opened.json'
    opened = capture.open_capture(plan_path, opened_path)
    # Use the sealed copy, never an unbound plan reread, for actual execution.
    plan = opened['plan']
    if plan['runner'] != worker:
        raise ValueError('runner changed before opening')
    cells = []
    for index, case in enumerate(plan['cells']):
        raw = directory / f'{index}.raw.json'
        out, err = directory / f'{index}.stdout', directory / f'{index}.stderr'
        command = argv + ['--plan', str(plan_path), '--cell-id', case['cell_id'], '--output', str(raw)]
        error = None
        rc = None
        with out.open('xb') as stdout, err.open('xb') as stderr:
            try:
                rc = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=timeout, check=False).returncode
                if rc:
                    error = f'native worker rc={rc}'
            except (OSError, subprocess.TimeoutExpired) as exc:
                error = str(exc)
        native = dict(run_id=plan['run_id'], plan_sha256=opened['plan_file']['sha256'],
                      cell_id=case['cell_id'], case=case,
                      settings={key: plan[key] for key in capture.SHARED},
                      status='failed', error=error, raw_output_path=None, raw_output_sha256=None,
                      execution={'argv': command, 'rc': rc}, native_artifacts=[])
        # Keep stdout/stderr and malformed/failed outputs, including zero bytes.
        from scripts.vidya.qwen4exp_quality_capture import stable_bytes_identity
        for path in (out, err, raw):
            if path.exists():
                _, receipt = stable_bytes_identity(path)
                native['native_artifacts'].append(receipt)
        try:
            telemetry, receipt = capture._read(raw)
            native.update(raw_output_path=str(raw), raw_output_sha256=receipt['sha256'])
            if error is None:
                status = telemetry.get('status')
                if status not in ('ok', 'failed', 'invalid', 'abstained'):
                    raise ValueError('native status missing or unknown')
                native['status'] = status
                if status == 'ok':
                    for key in ('positions', 'accepted', 'drafted', 'numerical_divergence'):
                        native[key] = telemetry[key]
                    native.pop('error')
                else:
                    native['error'] = telemetry.get('error') or 'native worker supplied no failure reason'
        except (ValueError, OSError, KeyError) as exc:
            native.update(status='invalid' if error is None else 'failed', error=error or str(exc),
                          raw_output_path=None, raw_output_sha256=None)
        path = directory / f'{index}.cell.json'
        capture._exclusive(path, native)
        cells.append(path)
    return capture.finalize_precision(opened_path, cells, directory / 'final.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('output_dir')
    args = parser.parse_args()
    run_matrix(args.plan, args.output_dir)

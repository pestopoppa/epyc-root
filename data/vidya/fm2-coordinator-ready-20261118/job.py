"""Run the FM-2 coordinator planning entry against one filed original judgment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PACKET = ROOT.parent / 'packet'
REPLAY = ROOT / 'source'
PYTHON = '/mnt/raid0/llm/epyc-inference-research/.venv/bin/python3'
ROW = 'vb-fm2-coordinator-context-20261118'
UNIT = 'claude-e950eb03f48fcba8'
NATIVE = PACKET / 'out' / 'units' / UNIT / 'receipt.json'
NATIVE_SHA = '5e6848d42bb8ad0c9b500aafd3d1adc190a839f666c23176705e7484ec8ff4fa'
ENTRY = 'scripts/vidya/coordinator_fm2_context.py'
SCHEMA = 'epyc.fm2.coordinator_context_row.v1'


def sha(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('expected a regular pinned file')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_pins(pins, digest):
    if sha(ROOT / 'source-pins.json') != digest:
        raise ValueError('source pins changed')
    for root, files in ((REPLAY, pins['code']), (PACKET, pins['original'])):
        for name, expected in files.items():
            path = root / name
            if not path.resolve(strict=True).is_relative_to(root) or sha(path) != expected:
                raise ValueError(f'pinned input changed: {name}')
    if sha(NATIVE) != NATIVE_SHA or sha(PACKET/'out/results.jsonl') != NATIVE_SHA:
        raise ValueError('filed result identity changed')


def write(path, report):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode='w') as stream:
        staged = Path(stream.name)
        try:
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
            os.link(staged, path)
        finally:
            staged.unlink()


def stopped(_signal, _frame):
    raise ValueError('row stopped')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'complete'))
    parser.add_argument('--pins-sha256', required=True)
    args = parser.parse_args()
    smoke = os.environ.get('FILLER_DRYRUN') == '1'
    if smoke and not os.environ.get('FILLER_DRYRUN_RESULT_PATH'):
        return 1
    output = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else ROOT/'official/RESULT.json'
    mode = 'publisher_smoke' if smoke else 'official'
    expected = {'schema': SCHEMA, 'id': ROW, 'mode': mode, 'pins_sha256': args.pins_sha256,
                'native_receipt_sha256': NATIVE_SHA}
    if args.action == 'complete':
        try:
            report = json.loads(output.read_bytes())
            return int(any(report.get(key) != value for key, value in expected.items())
                       or report.get('selected_count') != 1 or report.get('refusal_count') != 0
                       or report.get('reliance_count') != 0)
        except (OSError, ValueError):
            return 1

    report = dict(expected, selected_count=0, refusal_count=1, reliance_count=0, status='unknown')
    stage = 'grant'
    run_dir = None
    try:
        if os.environ.get('FILLER_ID') != ROW:
            raise ValueError('missing row grant')
        cutoff = min(time.time() + 300, int(os.environ['FILLER_DEADLINE']))
        stop = Path(os.environ['FILLER_STOPFILE'])
        signal.signal(signal.SIGTERM, stopped)
        signal.signal(signal.SIGALRM, stopped)

        def remaining():
            seconds = cutoff - time.time()
            if stop.exists() or seconds <= 0:
                raise ValueError('STOP or deadline')
            return seconds

        signal.setitimer(signal.ITIMER_REAL, remaining())
        cpus = sorted(os.sched_getaffinity(0))[:4]
        if len(cpus) != 4:
            raise ValueError('four granted CPUs required')
        os.sched_setaffinity(0, cpus)
        report['cpus'] = sorted(os.sched_getaffinity(0))
        stage = 'source verification'
        pins = json.loads((ROOT/'source-pins.json').read_bytes())
        check_pins(pins, args.pins_sha256)
        role = (REPLAY/'agents/coordinator-agent.md').read_text()
        if f'python3 -B /mnt/raid0/llm/views/epyc-root-main/{ENTRY}' not in role:
            raise ValueError('coordinator role entry mismatch')
        stage = 'coordinator canary'
        run_dir = Path(tempfile.mkdtemp(prefix=f'{mode}-', dir=ROOT))
        command = [PYTHON, '-E', '-B', str(REPLAY/'scripts/experiments/fm2-adamast/belief_canary.py'),
                   '--receipt', str(NATIVE), '--scratch', str(run_dir)]
        completed = subprocess.run(command, capture_output=True, check=True, text=True,
                                   timeout=remaining())
        stage = 'canary result verification'
        receipt_path = Path(completed.stdout.strip()).resolve(strict=True)
        if not receipt_path.is_relative_to(run_dir):
            raise ValueError('receipt escaped isolated run')
        receipt = json.loads(receipt_path.read_bytes())
        required = {'status': 'passed', 'consumer': 'coordination.fm2', 'entrypoint': ENTRY,
                    'entrypoint_sha256': pins['code'][ENTRY], 'native_receipt_sha256': NATIVE_SHA,
                    'claim_id': f'clm_fm2-adamast:{NATIVE_SHA}', 'grade': 'Judged/Located',
                    'tier': 'harness', 'reliance_eligible': False, 'unrelated_consumer_excluded': True}
        if (any(receipt.get(key) != value for key, value in required.items())
                or sha(receipt_path.with_name('planner-context.txt')) != receipt['section_sha256']):
            raise ValueError('unexpected coordinator planning context')
        stage = 'final source verification'
        check_pins(pins, args.pins_sha256)
        remaining()
        report.update(status='passed', selected_count=1, refusal_count=0, canary=receipt)
        signal.setitimer(signal.ITIMER_REAL, 0)
        write(output, report)
        print('One original FM-2 diagnosis reached the coordinator context as a harness observation')
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        reason = {'stage': stage, 'exception': type(exc).__name__, 'detail': str(exc)[:1000]}
        if run_dir is not None:
            for stream_name in ('stdout', 'stderr'):
                stream = getattr(exc, stream_name, None)
                if stream is not None:
                    path = run_dir / f'canary.{stream_name}'
                    path.write_bytes(stream.encode() if isinstance(stream, str) else stream)
                    reason[f'{stream_name}_path'] = str(path)
        report.update(status='unknown', selected_count=0, refusal_count=1, refusal=reason)
        write(output.with_suffix('.partial.json'), report)
        print(f"FM-2 coordinator context refused at {stage}: {reason['exception']}: {reason['detail']}")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

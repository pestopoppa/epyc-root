#!/usr/bin/env python3
"""Scheduled live matched CRM pair and source-bound fixture dry-run."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

D = Path('/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/live-pair-20261104')
ROOT = Path('/mnt/raid0/llm/worktrees/codex-evl46-live-source')
ID = 'tu-dtap-2-live-crm-pair-20261104'
PYTHON = Path('/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python')


def main():
    if os.environ.get('FILLER_DRYRUN') == '1':
        env = dict(os.environ)
        os.execve(str(PYTHON), [str(PYTHON), str(ROOT / 'scripts/autopilot/evals/dtap/tools/crm_row_fixture.py')], env)
    if os.environ.get('FILLER_ID') != ID:
        raise SystemExit('unexpected provider row id')
    cpus = os.environ['FILLER_CPUS']
    if cpus not in ('0-23', '24-47', '48-71', '72-95'):
        raise SystemExit('live pair requires one full CPU quarter')
    deadline = int(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    if stop.exists() or deadline - int(time.time()) < 240:
        raise SystemExit('STOP set or insufficient remaining claim window')
    for path in (D / 'source.json', D / 'input.json'):
        if not path.is_file():
            raise SystemExit(f'missing owner-prepared manifest: {path}')
    subprocess.run([str(PYTHON), str(D / 'check_prep.py')], check=True)

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / 'scripts/autopilot/evals/dtap'))
    from harness.crm_source_manifest import verify_manifest
    from src.runtime.region_claim_receipt import verify

    source = json.loads((D / 'source.json').read_bytes())
    verify_manifest(D / 'source.json', 'ec063054d2d7e2e801b130d124fec18683a96a15', source['source_tree_sha256'])
    run = D / 'run'
    run.mkdir(mode=0o700, exist_ok=False)
    prefix = run / 'claim'
    grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (ID + '.grant')
    cfg = {
        'input_manifest': str(D / 'input.json'), 'source_manifest': str(D / 'source.json'),
        'claim_prefix': str(prefix),
        'seed_file': str(ROOT / 'scripts/autopilot/evals/dtap/fixtures/crm_pair/upstream-seed.sql'),
        'crm_source': str(D / 'crm.py'),
        'slack_source': str(D / 'slack.py'),
        'verify_linkage': '/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',
        'port': 19186, 'journal': str(run / 'journal.jsonl'), 'seal': str(run / 'pair-seal.json'),
        'lifecycle_journal': str(run / 'lifecycle.jsonl'),
        'runtime_observation': str(run / 'runtime-observation.json'), 'server_log': str(run / 'server.log')}
    config = run / 'config.json'
    config.write_text(json.dumps(cfg, sort_keys=True) + '\n')
    os.chmod(config, 0o600)
    env = dict(os.environ,
        PYTHONPATH=str(ROOT / 'scripts/autopilot/evals/dtap') + ':' + str(ROOT),
        ORCHESTRATOR_TMP_DIR='/mnt/raid0/llm/tmp',
        ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT='1', CRM_JOB_CONFIG=str(config))
    cmd = [str(PYTHON), '-m', 'src.runtime.region_lock_cli', 'run', '--cpu-list', cpus,
        '--role', 'build', '--timeout-s', str(max(1, deadline - int(time.time()) - 90)),
        '--tag', ID, '--claim-receipt-prefix', str(prefix), '--claim-grant-file', str(grant), '--',
        'taskset', '-c', cpus, str(PYTHON),
        str(ROOT / 'scripts/autopilot/evals/dtap/tools/crm_live_worker.py')]
    child = subprocess.Popen(cmd, env=env)
    interrupted = False
    def forward(sig, _frame):
        nonlocal interrupted
        interrupted = True
        if child.poll() is None:
            child.send_signal(sig)
    previous = {sig: signal.signal(sig, forward) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        while child.poll() is None:
            if (stop.exists() or time.time() >= deadline) and not interrupted:
                forward(signal.SIGTERM, None)
            try:
                child.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if child.poll() is None:
        child.kill()
        child.wait(timeout=15)
        raise RuntimeError('provider process failed to drain after kill')
    if child.returncode != 0 or interrupted:
        raise SystemExit(75 if interrupted else (child.returncode or 1))

    files = source['files']
    opened, closed = verify(Path(str(prefix) + '.open.json'), Path(str(prefix) + '.close.json'),
        provider_sha256=files['src/runtime/region_lock_cli.py'],
        lock_sha256=files['src/runtime/cpu_region_lock.py'],
        receipt_sha256=files['src/runtime/region_claim_receipt.py'],
        expected_lock_root='/mnt/raid0/llm/tmp')
    verify_manifest(D / 'source.json', 'ec063054d2d7e2e801b130d124fec18683a96a15', source['source_tree_sha256'])
    if closed.get('child_rc') != 0:
        raise RuntimeError('provider close receipt reports nonzero child status')
    seal = json.loads((run / 'pair-seal.json').read_bytes())
    if seal.get('capture_kind') != 'live' or set(seal.get('arms', {})) != {'control', 'attack'} or any(
            arm.get('status') != 'complete' for arm in seal['arms'].values()):
        raise RuntimeError('live matched pair seal invalid or incomplete')
    outcome = {arm: seal['arms'][arm].get('delivery') for arm in ('control', 'attack')}
    (run / 'complete.json').write_text(json.dumps({
        'schema': 'dtap.crm_live_pair_completion.v1', 'complete': True,
        'scope': 'matched diagnostic only; no general security claim',
        'delivery_outcome': outcome, 'claim_id': opened['claim_id'], 'grant_id': opened['grant_id'],
        'claim_open': str(prefix) + '.open.json', 'claim_close': str(prefix) + '.close.json',
        'seal': str(run / 'pair-seal.json')}, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

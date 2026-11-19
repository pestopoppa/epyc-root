"""Prepare immutable source and reuse the prior verified model receipt once."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cf-plan-boundary')
SOURCE_REF = '12afe2858f9dbd4691447926d6cf1864de64348c'
HARNESS_REF = 'ed0496bf38d9228bd8420f5b8c3fde238097de9f'
RECEIPT_SHA = '3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff'
PYTHON = '/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python'


def prepare():
    ROOT.mkdir(parents=True, exist_ok=True)
    packet = ROOT / 'packet'
    if packet.exists():
        raise ValueError('immutable packet already exists; do not overwrite an attempted lineage')
    subprocess.run(['git', '-C', '/mnt/raid0/llm/epyc-orchestrator', 'worktree', 'add', '--detach',
                    str(ROOT / 'source'), SOURCE_REF], check=True, capture_output=True)
    packet.mkdir()
    for name in ('runner.py', 'prepare.py', 'launcher.sh', 'spec.json', 'test_pricing.py'):
        shutil.copy2(HERE / name, packet / name)
    shutil.copy2(HERE.parents[2] / 'docs/design/cf-plan-boundary-protocol-20261118.md', packet / 'protocol.md')
    for name, original in (('cmp4_runner.py', 'runner.py'), ('analysis.py', 'analysis.py')):
        (packet / name).write_bytes(subprocess.check_output([
            'git', '-C', str(HERE), 'show', f'{HARNESS_REF}:scripts/experiments/toc-cmp-4-live/{original}']))
    sys.path.insert(0, str(packet))
    import cmp4_runner as live
    receipt = (ROOT.parent / 'cmp4-r2/packet/inputs.json').read_bytes()
    if hashlib.sha256(receipt).hexdigest() != RECEIPT_SHA:
        raise ValueError('retained verified receipt digest changed')
    previous = json.loads(receipt)
    if previous['model_stat'] != live.file_identity(live.MODEL):
        raise ValueError('model stat differs from retained weight proof')
    (packet / 'prior-model-receipt.json').write_bytes(receipt)
    manifest = {k: previous[k] for k in ('model_path', 'model_sha256', 'model_stat',
                                       'template_sha256', 'build_sha256')}
    manifest.update(source=SOURCE_REF, harness_ref=HARNESS_REF,
                    prior_receipt_sha256=RECEIPT_SHA,
                    packet_sha256={p.name: live.digest(p) for p in packet.iterdir() if p.is_file()})
    live.atomic_json(packet / 'inputs.json', manifest)
    subprocess.run([PYTHON, '-I', '-B', str(packet / 'runner.py'), 'verify'], check=True)
    return packet / 'spec.json'


if __name__ == '__main__':
    print(prepare())

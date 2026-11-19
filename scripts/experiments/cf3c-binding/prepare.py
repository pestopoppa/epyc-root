#!/usr/bin/env python3
"""Seal a separate binding diagnostic without changing the source-pool schedule."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-binding-profile')
SOURCE = SCRATCH.parent / 'cf3c-binding/source'
COHORT = SCRATCH.parent / 'cf3c-binding/cohort.json'
BASE = '12afe2858f9dbd4691447926d6cf1864de64348c'
HARNESS_REF = 'ed0496bf38d9228bd8420f5b8c3fde238097de9f'
COHORT_SHA = '14c79e10bade5909a5406b86ea72d91e44b66f830859044639b0c9c622cb5cc3'
RECEIPT = SCRATCH.parent / 'cmp4-r2/packet/inputs.json'
RECEIPT_SHA = '3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff'
LINKAGE = Path('/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh')
LINKAGE_SHA = '57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
PYTHON = Path('/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python')
ROW = 'cf3c-binding-20261119'
PORT = 19387
MAX_TURNS = 18
MAX_COMPLETION_TOKENS = 384
CONTEXT_TOKENS = 16384
TASK_S = 420
WINDOW_S = 10800
ARMS = ('A0', 'A1-k4', 'A1-k8', 'A1-k12', 'A2', 'A3')
COVERAGE_CASES = tuple(f'binding_{kind}_v1' for kind in ('head', 'deep', 'paired', 'revision'))
BINDING_PROFILE = True
SERVING = ('model_path', 'model_sha256', 'model_stat', 'template_sha256', 'build_sha256')
FILES = ('prepare.py', 'runner.py', 'graph_trial.py', 'binding.py', 'launcher.sh',
         'spec.json', 'protocol.md', 'cmp4_runner.py', 'cmp4_graph_trial.py', 'analysis.py',
         'cases.json', 'inventory.json', 'schedule.json')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def cohort():
    value = read_json(COHORT)
    payload = {k: v for k, v in value.items() if k != 'cohort_sha256'}
    actual = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if value['cohort_sha256'] != COHORT_SHA or actual != COHORT_SHA:
        raise ValueError('prospectively fixed binding cohort changed')
    return value


def verify_source():
    def git(*args):
        return subprocess.check_output(['git', '-C', str(SOURCE), *args], text=True).strip()
    if (SOURCE.is_symlink() or Path(git('rev-parse', '--show-toplevel')).resolve() != SOURCE
            or git('rev-parse', 'HEAD') != BASE or git('rev-parse', '--abbrev-ref', 'HEAD') != 'HEAD'
            or git('status', '--porcelain', '--untracked-files=all')):
        raise ValueError('binding source must remain clean, detached and pinned')


def verify_packet(packet):
    verify_source()
    data = cohort()
    inputs = read_json(packet / 'inputs.json')
    if (digest(RECEIPT) != RECEIPT_SHA or digest(LINKAGE) != LINKAGE_SHA
            or inputs['source'] != BASE or inputs['cohort_sha256'] != COHORT_SHA
            or inputs['harness_ref'] != HARNESS_REF
            or inputs['prior_receipt_sha256'] != RECEIPT_SHA
            or inputs['linkage_sha256'] != LINKAGE_SHA
            or set(inputs['packet_sha256']) != set(FILES)):
        raise ValueError('binding profile provenance changed')
    prior = read_json(RECEIPT)
    if any(inputs[key] != prior[key] for key in SERVING):
        raise ValueError('binding serving receipts changed')
    for name, expected in inputs['packet_sha256'].items():
        path = packet / name
        if path.is_symlink() or digest(path) != expected:
            raise ValueError(f'sealed binding file changed: {name}')
    for filename, key in (('cases.json', 'cases'), ('inventory.json', 'inventory')):
        if read_json(packet / filename) != data[key]:
            raise ValueError('binding inventory changed')
    if read_json(packet / 'schedule.json') != {'coverage': data['schedule']}:
        raise ValueError('binding schedule changed')
    return inputs


def prepare():
    verify_source()
    data = cohort()
    if digest(RECEIPT) != RECEIPT_SHA:
        raise ValueError('retained serving receipt changed')
    packet = SCRATCH / 'packet'
    if packet.exists():
        verify_packet(packet)
        return packet / 'spec.json'
    suite = HERE.parent / 'cf3c-task-suite'
    with tempfile.TemporaryDirectory(prefix='.seal-', dir=SCRATCH) as temporary:
        staged = Path(temporary) / 'packet'
        staged.mkdir(mode=0o700)
        for name in ('prepare.py', 'launcher.sh', 'spec.json'):
            (staged / name).write_bytes((HERE / name).read_bytes())
        for name in ('runner.py', 'graph_trial.py', 'binding.py'):
            (staged / name).write_bytes((suite / name).read_bytes())
        protocol = HERE.parents[2] / 'docs/design/cf3c-binding-continuation-protocol-20261119.md'
        (staged / 'protocol.md').write_bytes(protocol.read_bytes())
        for name, original in (('cmp4_runner.py', 'runner.py'), ('cmp4_graph_trial.py', 'graph_trial.py'), ('analysis.py', 'analysis.py')):
            (staged / name).write_bytes(subprocess.check_output([
                'git', '-C', str(HERE), 'show', f'{HARNESS_REF}:scripts/experiments/toc-cmp-4-live/{original}']))
        for name, key in (('cases.json', 'cases'), ('inventory.json', 'inventory')):
            write_json(staged / name, data[key])
        write_json(staged / 'schedule.json', {'coverage': data['schedule']})
        prior = read_json(RECEIPT)
        write_json(staged / 'inputs.json', {
            'source': BASE, 'cohort_sha256': COHORT_SHA, 'harness_ref': HARNESS_REF,
            'prior_receipt_sha256': RECEIPT_SHA, 'linkage_sha256': LINKAGE_SHA,
            **{key: prior[key] for key in SERVING},
            'packet_sha256': {name: digest(staged / name) for name in FILES},
        })
        verify_packet(staged)
        subprocess.run([str(PYTHON), '-I', '-B', str(staged / 'runner.py'), 'verify'], check=True)
        for path in staged.iterdir():
            path.chmod(0o500 if path.name == 'launcher.sh' else 0o400)
        staged.rename(packet)
        packet.chmod(0o500)
    return packet / 'spec.json'


if __name__ == '__main__':
    print(prepare())

#!/usr/bin/env python3
"""Freeze candidate renders and preverified model custody before row publication."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRATCH = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3')
CMP2 = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp2/packet')
ORCH = Path('/mnt/raid0/llm/epyc-orchestrator')
BASE = '12afe2858f9dbd4691447926d6cf1864de64348c'
PATCH = ROOT / 'scripts/experiments/toc-cmp-3-contract/orchestrator.patch'

def prepare():
    packet = SCRATCH / 'packet'
    candidate = SCRATCH / 'candidate'
    if packet.exists() or candidate.exists():
        raise ValueError('scratch packet or candidate already exists; preserve prior custody')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    packet.mkdir()
    (SCRATCH / 'native').mkdir(exist_ok=True)
    source_manifest = json.loads((CMP2 / 'input-manifest.json').read_text())
    sys.path.insert(0, str(packet))
    for name in ('runner.py', 'launcher.sh', 'spec.json', 'README.md'):
        shutil.copy2(HERE / name, packet / name)
    for name in ('cases.json', 'rule_registry.json', 'verify_ggml_linkage.sh'):
        shutil.copy2(CMP2 / name, packet / name)
    shutil.copy2(CMP2 / 'runner.py', packet / 'cmp2_runner.py')
    spec = importlib.util.spec_from_file_location('cmp3_runner', packet / 'runner.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    base = runner.base
    body = {k: v for k, v in source_manifest.items() if k != 'sha256'}
    if base.digest(base.json_bytes(body)) != source_manifest['sha256']:
        raise ValueError('CMP2 receipt seal mismatch')
    for name, expected in source_manifest['packet_sha256'].items():
        if base.digest((CMP2 / name).read_bytes()) != expected:
            raise ValueError('CMP2 packet custody mismatch: ' + name)
    if base.file_identity(Path(source_manifest['model']['path'])) != source_manifest['model']['stat_at_hash']:
        raise ValueError('pre-grant model digest custody changed')
    for name, expected in source_manifest['build_sha256'].items():
        if base.digest((Path(source_manifest['bin_dir']) / name).read_bytes()) != expected:
            raise ValueError('runtime artifact mismatch: ' + name)
    subprocess.run(['git', 'worktree', 'add', '--detach', str(candidate), BASE], cwd=ORCH, check=True)
    subprocess.run(['git', 'apply', '--index', str(PATCH)], cwd=candidate, check=True)
    patch = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=candidate)
    (packet / 'orchestrator.patch').write_bytes(patch)
    cases = json.loads((packet / 'cases.json').read_text())
    renders = {c['id']: {} for c in cases}
    for trial in runner.schedule(cases):
        if trial['arm'] not in renders[trial['rule_id']]:
            case = next(c for c in cases if c['id'] == trial['rule_id'])
            renders[case['id']][trial['arm']] = runner.candidate_render(case, trial)
    base.atomic_json(packet / 'renders.json', renders)
    files = ['runner.py', 'cmp2_runner.py', 'launcher.sh', 'spec.json', 'README.md', 'cases.json',
             'rule_registry.json', 'verify_ggml_linkage.sh', 'orchestrator.patch', 'renders.json']
    files += [str(p.relative_to(packet)) for p in sorted((packet / 'fixtures').rglob('*')) if p.is_file()]
    manifest = {**{k: source_manifest[k] for k in ('bin_dir', 'build_commit', 'build_version',
                'build_sha256', 'build_manifest_sha256', 'model')},
        'packet_sha256': {n: base.digest((packet / n).read_bytes()) for n in files},
        'candidate_base': BASE, 'candidate_original_diff_sha256': base.digest(PATCH.read_bytes()),
        'cmp2_manifest_sha256': source_manifest['sha256'],
        'linkage_verifier': str(packet / 'verify_ggml_linkage.sh'),
        'fixture': 'deterministic substitute; not measured production compactor'}
    base.atomic_json(packet / 'input-manifest.json', base.sealed(manifest))
    runner.verify_inputs(json.loads((packet / 'input-manifest.json').read_text()))
    return packet / 'spec.json'

if __name__ == '__main__':
    print(prepare())

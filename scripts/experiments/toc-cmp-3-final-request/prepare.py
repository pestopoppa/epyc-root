#!/usr/bin/env python3
"""Seal an isolated candidate and existing model/build custody before admission."""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRATCH = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-final-request')
PRIOR = SCRATCH.parent / 'cmp3-runtime/packet'
ORCH = Path('/mnt/raid0/llm/epyc-orchestrator')
BASE = '12afe2858f9dbd4691447926d6cf1864de64348c'
PRIOR_SEAL = 'edd9170d24af8a4cb1dcede5de62a9ab4332f4cd46c5b8812780b1ad049f7f86'
sys.path.insert(0, str(PRIOR))
from semantic import canonical, digest, read_bound, strict_json


def prepare():
    packet, candidate = SCRATCH / 'packet', SCRATCH / 'candidate'
    if packet.exists() or candidate.exists():
        raise ValueError('existing candidate or packet: preserve custody')
    parent = strict_json((PRIOR / 'inputs.json').read_bytes())
    body = {k: v for k, v in parent.items() if k != 'sha256'}
    if parent['sha256'] != PRIOR_SEAL or digest(canonical(body)) != PRIOR_SEAL:
        raise ValueError('prior manifest seal mismatch')
    # Bind the prior receipt to its archived preparation copy.
    read_bound(PRIOR.parent / 'native/prepared/inputs.json', digest((PRIOR / 'inputs.json').read_bytes()))
    for name, sha in parent['packet_sha256'].items():
        read_bound(PRIOR / name, sha)
    for name, sha in parent['build_sha256'].items():
        read_bound(Path(parent['bin_dir']) / name, sha)
    import cmp2_runner
    if cmp2_runner.file_identity(Path(parent['model']['path'])) != parent['model']['stat_at_hash']:
        raise ValueError('preverified model identity changed')
    patches = [ROOT / 'scripts/experiments/toc-cmp-3-contract/orchestrator.patch',
               ROOT / 'scripts/experiments/toc-cmp-3-runtime/orchestrator.patch', HERE / 'orchestrator.patch']
    if [digest(p.read_bytes()) for p in patches[:2]] != parent['patch_sha256']:
        raise ValueError('preserved source patch mismatch')
    for patch in patches:
        if not patch.is_file():
            raise ValueError(f'missing candidate patch: {patch}')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'worktree', 'add', '--detach', str(candidate), BASE], cwd=ORCH, check=True)
    for patch in patches[:2]:
        subprocess.run(['git', 'apply', '--index', str(patch)], cwd=candidate, check=True)
    combined = subprocess.check_output(['git', 'diff', '--cached', '--binary', 'HEAD'], cwd=candidate)
    if digest(combined) != parent['packet_sha256']['candidate.patch']:
        raise ValueError('preserved candidate source mismatch')
    subprocess.run(['git', 'apply', '--index', str(patches[-1])], cwd=candidate, check=True)
    packet.mkdir()
    for name in ('runner.py', 'fixture.py', 'cases.json', 'launcher.sh', 'spec.json', 'prepare.py', 'test_final_request.py', 'README.md'):
        shutil.copy2(HERE / name, packet / name)
    for name in ('semantic.py', 'cmp2_runner.py', 'verify_ggml_linkage.sh'):
        (packet / name).write_bytes(read_bound(PRIOR / name, parent['packet_sha256'][name]))
    for name, patch in zip(('contract.patch', 'boundary-semantic.patch', 'final-request.patch'), patches, strict=True):
        shutil.copy2(patch, packet / name)
    shutil.copy2(ROOT / 'docs/design/toc-cmp-3-final-request-protocol-20261118.md', packet / 'protocol.md')
    shutil.copy2(PRIOR / 'inputs.json', packet / 'prior-inputs.json')
    (packet / 'candidate.patch').write_bytes(subprocess.check_output(['git', 'diff', '--cached', '--binary', 'HEAD'], cwd=candidate))
    manifest = {k: parent[k] for k in ('bin_dir', 'build_commit', 'build_version', 'build_sha256', 'build_manifest_sha256', 'model')}
    manifest.update(candidate_base=BASE, prior_manifest_sha256=parent['sha256'],
                    patch_sha256=[digest(p.read_bytes()) for p in patches],
                    packet_sha256={p.name: digest(p.read_bytes()) for p in sorted(packet.iterdir())})
    (packet / 'inputs.json').write_bytes(canonical({**manifest, 'sha256': digest(canonical(manifest))}) + b'\n')
    archive = SCRATCH / 'native/prepared'
    archive.mkdir(parents=True)
    for p in packet.iterdir():
        shutil.copy2(p, archive / p.name)
    subprocess.run([str(ORCH / '.venv/bin/python'), '-B', str(packet / 'runner.py'), 'verify'], check=True)
    return packet / 'spec.json'


if __name__ == '__main__':
    print(prepare())

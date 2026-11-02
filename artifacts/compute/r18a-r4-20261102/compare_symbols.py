#!/usr/bin/env python3
"""Fail-closed CPU and gfx90a device symbol comparison of two build directories.

Uses the existing AutoKernel ELF parser. roc-obj-ls locates embedded device
objects; its missing Perl modules are supplied from this capsule only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

for package_root in ('/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd',
                     '/workspace/repos/epyc-inference-research/scripts/kernel_rnd'):
    if Path(package_root).is_dir():
        sys.path.insert(0, package_root)
        break
from autokernel.evaluator.integrity import extract_elf_symbols  # noqa: E402

HERE = Path(__file__).resolve().parent
ROC_OBJ_LS = '/opt/rocm/bin/roc-obj-ls'
DEVICE_LINE = re.compile(r'^\d+\s+hipv4-amdgcn-amd-amdhsa--gfx90a\s+\S+#offset=(\d+)&size=(\d+)$')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def symbols(path, label):
    if not path.is_file() or path.stat().st_size < 64:
        raise ValueError(f'{label}: missing/empty ELF {path}')
    table = extract_elf_symbols(path, label=label)
    names = table.exported_names()
    if not names:
        raise ValueError(f'{label}: ELF exported no symbols')
    return names


def device_symbols(path, label):
    env = dict(os.environ, PERL5LIB=str(HERE / 'perl-lib'))
    result = subprocess.run([ROC_OBJ_LS, str(path)], env=env, text=True,
                            capture_output=True, check=True)
    spans = []
    for line in result.stdout.splitlines():
        m = DEVICE_LINE.match(line)
        if m:
            spans.append((int(m.group(1)), int(m.group(2))))
    if not spans:
        raise ValueError(f'{label}: no gfx90a code objects; roc-obj-ls stderr={result.stderr!r}')
    names = set()
    with path.open('rb') as f, tempfile.TemporaryDirectory(prefix='r18a-elf-') as temp:
        for index, (offset, size) in enumerate(spans):
            if size < 64:
                raise ValueError(f'{label}: empty code object {index}')
            f.seek(offset)
            data = f.read(size)
            if len(data) != size:
                raise ValueError(f'{label}: truncated code object {index}')
            obj = Path(temp) / f'{index}.co'
            obj.write_bytes(data)
            table = extract_elf_symbols(obj, label=f'{label}/device/{index}')
            names.update(x.name[:-3] for x in table.symbols
                         if x.table == table.preferred and x.exported
                         and x.type == 'OBJECT' and x.name.endswith('.kd'))
            obj.unlink()
    if not names:
        raise ValueError(f'{label}: no exported gfx90a device symbols')
    return names, len(spans)


def compare(anchor, candidate, anchor_cpu=None, candidate_cpu=None):
    anchor_cpu = anchor_cpu or anchor
    candidate_cpu = candidate_cpu or candidate
    rows = {}
    for kind, library in (('cpu', 'libggml-cpu.so'), ('hip_host', 'libggml-hip.so')):
        a, c = ((anchor_cpu, candidate_cpu) if kind == 'cpu' else (anchor, candidate))
        a, c = a / 'bin' / library, c / 'bin' / library
        an, cn = symbols(a, f'anchor/{kind}'), symbols(c, f'candidate/{kind}')
        rows[kind] = {'anchor_sha256': digest(a), 'candidate_sha256': digest(c),
                      'anchor_count': len(an), 'candidate_count': len(cn),
                      'removed': sorted(an-cn), 'added': sorted(cn-an)}
    a, c = anchor / 'bin/libggml-hip.so', candidate / 'bin/libggml-hip.so'
    an, ac = device_symbols(a, 'anchor')
    cn, cc = device_symbols(c, 'candidate')
    rows['hip_device'] = {'anchor_code_objects': ac, 'candidate_code_objects': cc,
                          'anchor_count': len(an), 'candidate_count': len(cn),
                          'removed': sorted(an-cn), 'added': sorted(cn-an)}
    return {'schema': 'r18a.independent_symbol_identity.v1',
            'anchor_build': str(anchor.resolve()),
            'candidate_build': str(candidate.resolve()),
            'comparisons': rows,
            'symbol_identity_pass': all(not row['removed'] and not row['added']
                                        for row in rows.values())}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--anchor-build', type=Path, required=True)
    p.add_argument('--candidate-build', type=Path, required=True)
    p.add_argument('--anchor-cpu-build', type=Path)
    p.add_argument('--candidate-cpu-build', type=Path)
    args = p.parse_args()
    try:
        answer = compare(args.anchor_build, args.candidate_build,
                         args.anchor_cpu_build, args.candidate_cpu_build)
    except Exception as exc:
        print(json.dumps({'schema': 'r18a.independent_symbol_identity.v1',
                          'symbol_identity_pass': False, 'error': str(exc)}))
        raise SystemExit(2)
    print(json.dumps(answer, indent=2, sort_keys=True))
    raise SystemExit(0 if answer['symbol_identity_pass'] else 1)

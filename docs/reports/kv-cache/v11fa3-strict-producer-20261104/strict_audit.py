#!/usr/bin/env python3
"""Review candidate: fail-closed gfx90a metadata extraction, not source custody."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

LLVM = Path('/opt/rocm/llvm/bin')
MAGIC = b'__CLANG_OFFLOAD_BUNDLE__'
TARGET = 'hipv4-amdgcn-amd-amdhsa--gfx90a'
FIELDS = ('.vgpr_count', '.agpr_count', '.vgpr_spill_count', '.sgpr_spill_count', '.group_segment_fixed_size', '.private_segment_fixed_size')
HEADER = 'name\tvgpr\tagpr\tvgpr_spill\tsgpr_spill\tlds\tscratch\n'

class AuditError(RuntimeError):
    pass

def call(args, *, text=False, input=None):
    r = subprocess.run(args, input=input, capture_output=True, text=text, check=False)
    if r.returncode:
        raise AuditError(f'{args[0]} failed rc={r.returncode}: {str(r.stderr)[:500]}')
    return r.stdout

def parse_notes(text):
    # No marker, no end marker, YAML failure and malformed metadata are all refusals.
    i = text.find('---')
    j = text.find('...', i + 3) if i >= 0 else -1
    if i < 0 or j < 0:
        raise AuditError('missing metadata YAML boundaries')
    try:
        md = yaml.safe_load(text[i:j + 3])
    except yaml.YAMLError as e:
        raise AuditError('invalid metadata YAML') from e
    if not isinstance(md, dict) or not isinstance(md.get('amdhsa.kernels'), list):
        raise AuditError('missing kernel metadata')
    result = []
    for k in md['amdhsa.kernels']:
        if not isinstance(k, dict) or not isinstance(k.get('.name'), str) or not k['.name']:
            raise AuditError('malformed kernel identity')
        if 'flash_attn' not in k['.name']:
            continue
        vals = [k.get(key) for key in FIELDS]
        if any(type(v) is not int or v < 0 for v in vals):
            raise AuditError('invalid or missing FA resource metadata')
        result.append((k['.name'], *vals))
    return result

def audit(lib, workdir):
    raw = Path(lib).read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    starts = [m.start() for m in re.finditer(re.escape(MAGIC), raw)]
    if not starts:
        raise AuditError('no offload bundles')
    starts.append(len(raw))
    rows, counts = [], {'bundles': len(starts) - 1, 'target_bundles': 0, 'non_target_bundles': 0}
    workdir = Path(workdir)
    for idx, (start, end) in enumerate(zip(starts, starts[1:])):
        bundle, code = workdir / f'{idx}.bin', workdir / f'{idx}.co'
        bundle.write_bytes(raw[start:end])
        targets = call([str(LLVM/'clang-offload-bundler'), '--list', '--type=o', f'--input={bundle}'], text=True).splitlines()
        if not targets or any(not x.strip() for x in targets) or len(targets) != len(set(targets)):
            raise AuditError(f'empty or ambiguous target list in bundle {idx}')
        # Some code objects have feature-suffixed target IDs. Never silently ignore one.
        matching = [x for x in targets if x.strip() == TARGET or x.strip().startswith(TARGET + ':')]
        if not matching:
            counts['non_target_bundles'] += 1
            continue
        for j, target in enumerate(matching):
            co = workdir / f'{idx}-{j}.co'
            call([str(LLVM/'clang-offload-bundler'), '--unbundle', '--type=o', f'--input={bundle}', f'--targets={target.strip()}', f'--output={co}'])
            if not co.is_file() or co.stat().st_size == 0:
                raise AuditError('unbundle produced missing or empty code object')
            notes = call([str(LLVM/'llvm-readelf'), '--notes', str(co)], text=True)
            rows.extend(parse_notes(notes))
            counts['target_bundles'] += 1
    if not counts['target_bundles'] or not rows:
        raise AuditError('no gfx90a objects or FA kernels')
    demangled = call(['c++filt'], input='\n'.join(r[0] for r in rows) + '\n', text=True).splitlines()
    if len(demangled) != len(rows) or any(not n for n in demangled):
        raise AuditError('demangler failed or lost identities')
    rows = [(demangled[i], *r[1:]) for i, r in enumerate(rows)]
    if hashlib.sha256(Path(lib).read_bytes()).hexdigest() != source_sha:
        raise AuditError('library changed during audit')
    return rows, {'schema':'v11fa3.strict-codeobj-audit.v1', 'source_sha256':source_sha, **counts, 'fa_kernels':len(rows)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('library', type=Path)
    p.add_argument('out', type=Path)
    args = p.parse_args()
    # No stale .co files and no success-like output after partial extraction.
    if args.out.exists():
        p.error('output directory already exists')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v11fa3-audit-', dir=args.out.parent) as tmp:
        rows, metadata = audit(args.library, tmp)
    args.out.mkdir(parents=True, exist_ok=False)
    table = HEADER + ''.join('\t'.join(map(str, row)) + '\n' for row in rows)
    (args.out/'fa_kernels.tsv').write_text(table)
    metadata['tsv_sha256'] = hashlib.sha256(table.encode()).hexdigest()
    (args.out/'RESULT.json').write_text(json.dumps(metadata, indent=2, sort_keys=True)+'\n')

if __name__ == '__main__':
    main()

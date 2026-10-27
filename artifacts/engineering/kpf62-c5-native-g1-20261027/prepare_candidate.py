#!/usr/bin/env python3
"""Future granted source assembly only. Never run during HOLD; no build or model load."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
CHAMPION = 'c72ec82f5417bb2937310326120f149b665e8400'
API = 'caea49a696811f5e8e7449c209907c65d21b6751'
ROOT = '297b166dbd27a88f14dc4de8f8858c07bf17b137'
SHARED = Path('/mnt/raid0/llm/llama.cpp')

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assemble(candidate, root_candidate):
    # Only isolated new clones under this packet. Do not create worktrees in shared .git.
    for path in (candidate, root_candidate):
        if path.parent.resolve() != BASE or path.exists():
            raise ValueError('new direct child of packet required')
    if git(SHARED, 'rev-parse', 'refs/heads/ak/champion/llama-cpp-ffc1bac82eec').decode().strip() != CHAMPION:
        raise ValueError('champion moved: re-review source ancestry before assembly')
    subprocess.run(['git', 'clone', '--shared', '--no-checkout', str(SHARED), str(candidate)], check=True)
    subprocess.run(['git', '-C', str(candidate), 'checkout', '--detach', CHAMPION], check=True)
    subprocess.run(['git', 'clone', '--shared', '--no-checkout', '/workspace', str(root_candidate)], check=True)
    subprocess.run(['git', '-C', str(root_candidate), 'checkout', '--detach', ROOT], check=True)
    # These files are bit-identical between champion and the API patch's parent;
    # replacement therefore consists exclusively of the already authored API delta.
    for name in ('src/llama-kv-cache.cpp', 'src/llama-kv-cache.h', 'src/llama-kv-cells.h'):
        if git(candidate, 'show', f'{CHAMPION}:{name}') != git(candidate, 'show', f'{API}^:{name}'):
            raise ValueError(f'API prerequisite drift: {name}')
        if name == 'src/llama-kv-cache.cpp':
            (candidate / name).write_bytes((BASE / 'draft/src/llama-kv-cache.cpp').read_bytes())
        else:
            (candidate / name).write_bytes(git(candidate, 'show', f'{API}:{name}'))
    # Preserve champion C5's fused-decode default-OFF function. Never copy the old
    # branch's entire context/ext files (that would silently undo C5).
    for name, start, end, anchor in (
        ('src/llama-context.cpp', '// chunk-KV reuse (experimental; see llama-ext.h)', '// llama adapter API', '// llama adapter API'),
        ('src/llama-ext.h', '//\n// chunk-KV reuse (experimental, phase P1: attention-only memory)', '// Get the default ggml_type', '// Get the default ggml_type'),
    ):
        old = git(candidate, 'show', f'{API}:{name}').decode()
        part = old[old.index(start):old.index(end)]
        target = candidate / name
        current = target.read_text()
        if current.count(anchor) != 1 or 'llama_chunk_kv_supported' in current:
            raise ValueError(f'non-unique or already instrumented anchor: {name}')
        current = current.replace(anchor, part + anchor)
        if name.endswith('.cpp') and '#include "llama-kv-cache.h"' not in current:
            current = current.replace('#include "llama-io.h"', '#include "llama-io.h"\n#include "llama-kv-cache.h"')
        if name.endswith('.cpp'):
            entry = 'static llama_kv_cache * chunk_kv_cache(const llama_context * ctx, std::string * why) {\n'
            assert current.count(entry) == 1
            current = current.replace(entry, entry + '    if (ctx->get_cparams().dca_chunk_size > 0) {\n        if (why) *why = "dual chunk attention does not support K-shift";\n        return nullptr;\n    }\n')
            entry = '    ctx->memory_update(false);\n\n    return kv->chunk_read_f32'
            assert current.count(entry) == 1
            current = current.replace(entry, '    ctx->memory_update(false);\n    if (kv->get_has_shift()) {\n        LLAMA_LOG_ERROR("%s: pending K-shift could not be applied\\n", __func__);\n        return 0;\n    }\n\n    return kv->chunk_read_f32')
        target.write_text(current)
    (candidate / 'tests/test-chunk-kv.cpp').write_bytes((BASE / 'draft/tests/test-chunk-kv.cpp').read_bytes())
    # Target only: no server-store, reorder planner, sparse G0, G3 or unrelated tests.
    with (candidate / 'tests/CMakeLists.txt').open('a') as stream:
        stream.write('\n# KPF-62 G1 native capture target.\nllama_build(test-chunk-kv.cpp)\ntarget_include_directories(test-chunk-kv PRIVATE ${PROJECT_SOURCE_DIR}/src)\n')
    names = ('src/llama-context.cpp', 'src/llama-ext.h', 'src/llama-kv-cache.cpp',
             'src/llama-kv-cache.h', 'src/llama-kv-cells.h', 'tests/test-chunk-kv.cpp', 'tests/CMakeLists.txt')
    manifest = {'schema': 'epyc.kpf62.source_assembly.v1', 'champion': CHAMPION,
                'api_origin': API, 'capture_origin': '0a9fa2c29bc0929d7a2493a8416659ca892ae3d6',
                'root_adapter': ROOT, 'files': {name: sha(candidate / name) for name in names},
                'scope': 'source-only G1 instrument, no promotion', 'candidate': str(candidate),
                'root_candidate': str(root_candidate)}
    manifest['source_digest'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    (BASE / 'assembly.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    (BASE / 'candidate.diff').write_bytes(git(candidate, 'diff', '--', *names))
    print('SOURCE_ASSEMBLED_NOT_BUILT')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, default=BASE / 'candidate')
    p.add_argument('--root-candidate', type=Path, default=BASE / 'root-reader')
    a = p.parse_args()
    assemble(a.candidate, a.root_candidate)
    adapter = a.root_candidate / 'scripts/vidya/adapters/chunk_kv.py'
    if 'no_protocol_ids=("unknown",)' not in adapter.read_text():
        raise ValueError('ROOT pin lacks landed unknown-protocol correction; rebind before booking')

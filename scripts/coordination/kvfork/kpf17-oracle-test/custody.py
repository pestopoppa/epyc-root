"""Fail closed on an incomplete or unfiled KPF-17 oracle build."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

BUILD = Path('/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104')
RECEIPT = BUILD / 'out/RESULT.json'
FILED = Path('/mnt/raid0/llm/tmp/compute-flags/filing-done/kvfork17-oracle-build-20261104.verdict.json')
SOURCE = '8952a0f693fb923918157eb25117641b74766230'
PATCH = 'b7eb4cabacadb7378bd1bcc8af4532f71ce39c751b5d0f11ce4abe96b010eac6'
TEST = 'b2f7085c3b772b58d6e9eb5ec33f217f22e9e1987bb8f51f040094eb586ef2ab'
HEADER = '90787c4a526d2dedd3d3d11bf944ea81eeb1c2efd77e5e6862e8e69a57b26249'
HELPER = '57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
HEX = re.compile(r'^[0-9a-f]{64}$')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def build_identity():
    receipt = json.loads(RECEIPT.read_text())
    verdict = json.loads(FILED.read_text())
    if verdict.get('id') != 'kvfork17-oracle-build-20261104' or verdict.get('rc') != 0 or verdict.get('row_verdict') != 'pass' or verdict.get('dry_run') is not False:
        raise ValueError('build was not filed PASS')
    if verdict.get('native_result_path') != str(RECEIPT) or verdict.get('verdict', {}).get('native_result_sha256') != digest(RECEIPT):
        raise ValueError('filed build receipt does not match native result')
    manifest = BUILD/'runtime.sha256'
    if digest(manifest) != '1e60119c5549865430164e4a1d44cd74590ef52d969500d763c835fdd2b87b48':
        raise ValueError('build runtime manifest changed')
    for row in manifest.read_text().splitlines():
        expected, name = row.split(None, 1)
        if digest(name.strip()) != expected:
            raise ValueError('build runtime file changed: '+name.strip())
    required = {'schema': 'kpf17.oracle-build.v1', 'status': 'BUILT', 'source_commit': SOURCE,
                'patch_sha256': PATCH, 'patched_test_sha256': TEST, 'oracle_header_sha256': HEADER}
    if any(receipt.get(k) != v for k, v in required.items()):
        raise ValueError('unexpected build source or patch identity')
    files = receipt.get('files'); compilers = receipt.get('compiler_sha256')
    if not isinstance(files, dict) or not isinstance(compilers, dict) or set(compilers) != {'/usr/bin/cc', '/usr/bin/c++'}:
        raise ValueError('missing file or compiler custody')
    binary = (BUILD/'build/bin/test-save-load-state').resolve(strict=True)
    bindir = (BUILD/'build/bin').resolve(strict=True)
    if binary.parent != bindir or str(binary) not in files:
        raise ValueError('expected executable is not recorded')
    needed = ['libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libllama.so', 'libllama-common.so']
    libs = {}
    for name in needed:
        target = (bindir/name).resolve(strict=True)
        if target.parent != bindir or str(target) not in files:
            raise ValueError('required library missing from receipt: ' + name)
        libs[str(target)] = files[str(target)]
    helper = BUILD/'verify_ggml_linkage.sh'
    if files.get(str(helper)) != HELPER:
        raise ValueError('linkage helper is not pinned')
    for name, expected in {**files, **compilers}.items():
        if not isinstance(expected, str) or not HEX.fullmatch(expected) or digest(name) != expected:
            raise ValueError('build file changed: ' + name)
    subprocess.run(['python3', str(BUILD/'complete.py')], check=True, stdout=subprocess.DEVNULL)
    return {'receipt_sha256': digest(RECEIPT), 'filed_sha256': digest(FILED),
            'binary': str(binary), 'binary_sha256': files[str(binary)],
            'libraries': libs, 'source_commit': SOURCE, 'patch_sha256': PATCH,
            'test_sha256': TEST, 'oracle_header_sha256': HEADER}


def model_identity(path):
    model = json.loads(Path(path).read_text())
    if model.get('sha256') != '0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c':
        raise ValueError('model does not have the preverified hash')
    p = Path(model['path']); stat = p.stat()
    if model.get('stat') != {k:getattr(stat, 'st_'+k) for k in ('dev','ino','size','mtime_ns','ctime_ns')}:
        raise ValueError('model identity metadata changed; reverify outside grant')
    return model


def validate_maps(lines, expected):
    seen = {}
    for line in lines:
        parts = line.split(None, 5)
        if len(parts) < 6 or not re.search(r'/lib(?:ggml|llama)(?:[-.]|\.so)', parts[5]):
            continue
        if parts[5].endswith(' (deleted)'):
            raise ValueError('deleted mapped library')
        path = Path(parts[5]).resolve(strict=True); name = str(path)
        if name not in expected or digest(path) != expected[name]:
            raise ValueError('unattested mapped library: ' + name)
        st = path.stat(); major, minor = (int(x, 16) for x in parts[3].split(':'))
        if (major, minor, int(parts[4])) != (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino):
            raise ValueError('mapped library inode changed')
        seen[name] = expected[name]
    required = {'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libllama.so'}
    if not all(any(Path(p).name.startswith(prefix) for p in seen) for prefix in required):
        raise ValueError('required ggml/llama mappings absent')
    return seen

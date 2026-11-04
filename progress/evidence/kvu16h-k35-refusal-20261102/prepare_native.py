#!/usr/bin/env python3
"""Run once BEFORE publishing, outside any compute grant."""
import hashlib
import json
from pathlib import Path
import subprocess
import native_job as j

D = Path('/mnt/raid0/llm/tmp/kvu/k35-native-validation-20261102')
build = j.BINARY.resolve().parent.parent
catalog = build / 'SHA256SUMS'
verified = []
for line in catalog.read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    name = name.lstrip('*')
    if name.startswith('bin/lib') or name == 'bin/llama-server':
        p = build / name
        actual = hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
        if digest != actual:
            raise RuntimeError('store manifest mismatch: ' + name)
        verified.append({'path': str(p.resolve()), 'sha256': actual})
if str(j.BINARY.resolve()) not in [v['path'] for v in verified]:
    raise RuntimeError('server absent from approved store catalog')
with j.MODEL.open('rb') as f:
    if f.read(4) != b'GGUF':
        raise RuntimeError('invalid model header')
version = subprocess.run([str(j.BINARY), '--version'], env={'PATH': '/usr/bin:/bin',
                          'LD_LIBRARY_PATH': str(j.BINARY.resolve().parent)},
                         capture_output=True, text=True, check=True, timeout=20)
if 'ffc1bac82' not in version.stdout + version.stderr:
    raise RuntimeError('unexpected kernel version')
m = j.load_runner()
(D / 'prompt.txt').write_text(m.prompt_for_context(2048, 16))
paths = [j.MODEL, j.BINARY, catalog, D / 'prompt.txt', D / 'native_job.py',
         D / 'check_complete.py', D / 'parent_exec.py', D / 'scripts/benchmark/k35_stack_context_matrix_runner.py']
paths += [Path(v['path']) for v in verified]
record = {'schema': 'epyc.kvu16h.prepared.v1', 'model_verification': 'GGUF magic and stat identity; no weight digest claim',
          'model': str(j.MODEL), 'kernel_catalog': str(catalog), 'verified_store_files': verified,
          'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [D / 'native_job.py', D / 'parent_exec.py', D / 'check_complete.py', D / 'scripts/benchmark/k35_stack_context_matrix_runner.py']},
          'version': version.stdout + version.stderr, 'identities': [j.identity(p) for p in dict.fromkeys(paths)]}
(D / 'prepared.json').write_text(json.dumps(record, indent=2) + '\n')
print('prepared model header, prompt, source identities, and', len(verified), 'manifest-bound store files')

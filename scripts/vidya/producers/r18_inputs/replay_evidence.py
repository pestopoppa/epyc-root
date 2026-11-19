"""Evidence checks for R18-A; integrate only into the owned successor."""
import hashlib
import json
from pathlib import Path

ANCHORS = Path('/mnt/raid0/llm/kernels/builds')
COMPARATOR = Path(__file__).resolve().parent / 'compare_symbols.py'
CPU_SHA = '3f4edd2fc0f1e78003735be59db987d43c4bc0e6a8f821bc419d7b6f492346c0'
HIP_SHA = 'f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079'
COMPARATOR_SHA = '08a5e9e15f8ac07d573d8e0c8c38ec4aef6d78820032ec4e2eb0325a3447bf61'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()

def verify_replay(log, manifest, manifest_sha, build_root):
    if sha(manifest) != manifest_sha:
        raise ValueError('manifest digest changed')
    expected = json.loads(Path(manifest).read_text())['tu']
    seen = {}
    for line in Path(log).read_text(errors='strict').splitlines():
        if not line.startswith('HIP_CUID_REPLAY '):
            continue
        row = json.loads(line[len('HIP_CUID_REPLAY '):])
        key = row['TU']
        if key not in expected or key in seen:
            raise ValueError('unexpected or duplicate replay witness: ' + key)
        if (row['driver_cuid'] != expected[key]['cuid'] or
            row['source_sha256'] != expected[key]['source_sha256'] or
            row['manifest_sha256'] != manifest_sha):
            raise ValueError('replay witness mismatch: ' + key)
        output = Path(row['output']).resolve()
        if not output.is_relative_to(Path(build_root).resolve()) or not output.is_file() or output.stat().st_size < 64:
            raise ValueError('missing or escaped HIP object: ' + key)
        seen[key] = row
    if set(seen) != set(expected):
        raise ValueError(f'replay coverage mismatch: {len(seen)}/{len(expected)}')
    return {'manifest_sha256': manifest_sha, 'count': len(seen), 'translation_units': seen}

def comparison_hashes(cpu_build, gpu_build, dependency_pins):
    paths = {
        'private_cpu': (ANCHORS / 'cpu-20260921-ffc1bac82/bin/libggml-cpu.so', CPU_SHA),
        'store_cpu': (Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/libggml-cpu.so.0.16.0'), CPU_SHA),
        'private_hip': (ANCHORS / 'gpu-20260921-ffc1bac82/bin/libggml-hip.so', HIP_SHA),
        'store_hip': (Path('/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/libggml-hip.so.0.16.0'), HIP_SHA),
        'comparator': (COMPARATOR, COMPARATOR_SHA),
        'candidate_cpu': (Path(cpu_build) / 'bin/libggml-cpu.so', None),
        'candidate_hip': (Path(gpu_build) / 'bin/libggml-hip.so', None),
    }
    for path, digest in dependency_pins.items():
        paths['dependency:' + path] = ((Path(__file__).resolve().parent / 'perl-lib' / path[len('@bundle/'):]) if path.startswith('@bundle/') else Path(path), digest)
    out = {}
    for label, (path, expected) in paths.items():
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError('pinned input changed: ' + label)
        out[label] = {'path': str(path), 'sha256': digest}
    return out

def validate_comparison(result, rc, hashes, cpu_build, gpu_build):
    if rc not in (0, 1) or result.get('schema') != 'r18a.independent_symbol_identity.v1' or 'error' in result:
        raise ValueError('invalid comparator execution')
    if result.get('anchor_build') != str((ANCHORS / 'gpu-20260921-ffc1bac82').resolve()) or result.get('candidate_build') != str(Path(gpu_build).resolve()):
        raise ValueError('comparison paths mismatch')
    rows = result.get('comparisons')
    if not isinstance(rows, dict) or set(rows) != {'cpu', 'hip_host', 'hip_device'}:
        raise ValueError('incomplete surfaces')
    for name, row in rows.items():
        if not isinstance(row, dict) or not all(isinstance(row.get(k), list) and all(isinstance(x, str) for x in row[k]) for k in ('added', 'removed')):
            raise ValueError('incomplete difference sets: ' + name)
        if not all(isinstance(row.get(k), int) and row[k] > 0 for k in ('anchor_count', 'candidate_count')):
            raise ValueError('missing surface counts: ' + name)
    for name, anchor, candidate in [('cpu','private_cpu','candidate_cpu'), ('hip_host','private_hip','candidate_hip')]:
        if rows[name].get('anchor_sha256') != hashes[anchor]['sha256'] or rows[name].get('candidate_sha256') != hashes[candidate]['sha256']:
            raise ValueError('comparison artifact mismatch: ' + name)
    if not all(isinstance(rows['hip_device'].get(k), int) and rows['hip_device'][k] > 0 for k in ('anchor_code_objects', 'candidate_code_objects')):
        raise ValueError('missing code-object counts')
    passed = all(not r['added'] and not r['removed'] for r in rows.values())
    if result.get('symbol_identity_pass') is not passed or rc != (0 if passed else 1):
        raise ValueError('comparator verdict inconsistent')
    return passed

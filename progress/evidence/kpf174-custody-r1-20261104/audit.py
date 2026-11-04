#!/usr/bin/env python3
"""Read-only historical-image/native-witness audit; never starts inference."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin')
PRIOR = Path('/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf-gpu-followups/out/kpf131b')
PREPARATION = Path('/mnt/raid0/llm/tmp/codex3-kpf174d-131b-controls-20261030')
MARKERS = ('LLAMA_KPF_LAYOUT_TRACE', 'LLAMA_KPF_ITEM4_TRACE', 'KPF_LAYOUT_BEGIN', 'KPF_ITEM4_BEGIN')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    record = PRIOR / 'records/kpf13-default_specoff-20261023T182758Z.json'
    expected = json.loads(record.read_text())['binary_sha256']
    artifacts = []
    seen = set()
    for path in sorted(IMAGE.iterdir()):
        if not path.is_file() or not (path.name == 'llama-server' or '.so' in path.name):
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        data = path.read_bytes()
        artifacts.append({'path': str(path), 'resolved': str(resolved), 'sha256': digest(data),
                          'native_witness_markers': {m: m.encode() in data for m in MARKERS}})
    server = next(a for a in artifacts if Path(a['path']).name == 'llama-server')
    inputs = []
    for name in ('control.py', 'layout_witness.py', 'layout-trace.patch', 'exact-inputs.json', 'CANDIDATE.md'):
        path = PREPARATION / name
        inputs.append({'path': str(path), 'sha256': digest(path.read_bytes())})
    cells = []
    exact = json.loads((PREPARATION / 'exact-inputs.json').read_text())
    # Preserve its original structure and custody; no semantic regrading.
    for path in sorted((PRIOR / 'cells/default_specoff').glob('*.json')):
        cells.append({'path': str(path), 'sha256': digest(path.read_bytes())})
    result = {
        'schema': 'kpf131-historical-image-readiness-audit/v1',
        'scope': 'offline artifact inspection only; no model hash, preparation, grant, publication or inference',
        'historical_record': {'path': str(record), 'sha256': digest(record.read_bytes()), 'binary_sha256': expected},
        'current_server_matches_historical_record': server['sha256'] == expected,
        'artifacts': artifacts,
        'prepared_control_inputs': inputs,
        'historical_specoff_cells': cells,
        'exact_input_top_level_type': type(exact).__name__,
        'witness_markers_present': any(any(a['native_witness_markers'].values()) for a in artifacts),
        'ready_for_historical_control_row': False,
        'reason': 'Existing physical-layout control producer requires native layout and task/batch witnesses absent from the exact historical image. Its trace patch produces a different image. No independent exact-image witness implementation was found in the inspected preparation.',
        'remaining_implementation': 'Implement and validate an external observer on the exact historical image that binds physical KV prefix positions, occupied layout, allocator head and task/batch rows to each request; preserve image and runtime DSO custody. Then freeze the five-cell same-image matched-control rule and acceptance reconciliation before publication.',
        'conclusion_limits': 'Missing these known markers does not prove that every possible external observer is impossible; no such observer is implemented in this packet. Current DSO hashes do not retrospectively establish historical DSO contents. Original FAILs unchanged.',
        'publish_row_spec_created': False,
        'qualification': 'NOT_RUN',
    }
    out = HERE / 'AUDIT.json'
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': str(out), 'historical_server_identity_match': result['current_server_matches_historical_record'],
                      'known_native_witnesses_present': result['witness_markers_present'], 'ready': False}))
    assert result['current_server_matches_historical_record'], 'Historical server changed'
    assert not result['witness_markers_present'], 'Reassess: witness markers now present'


if __name__ == '__main__':
    main()

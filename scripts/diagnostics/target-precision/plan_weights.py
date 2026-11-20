"""Plan a single-source conversion; never download weights or launch a producer."""
import hashlib
import re
from pathlib import PurePosixPath

GIB = 1024 ** 3


def _require(value, message):
    if not value:
        raise ValueError(message)


def plan_weights(api, index_bytes, source_commit, available_bytes, *, disk_floor=150 * GIB):
    """Bind HF's shard index to one immutable revision, then budget all outputs.

    This plan is not a weight receipt. Execution must verify every original,
    hash tools/outputs, and compare tensor/tokenizer catalogs before admission.
    The storage envelope is deliberately conservative, not a measured file size.
    """
    import json
    _require(api.get('id') == 'Qwen/Qwen3.8-27B', 'unexpected upstream repository')
    revision = api.get('sha', '')
    _require(re.fullmatch('[0-9a-f]{40}', revision), 'unpinned upstream revision')
    _require(re.fullmatch('[0-9a-f]{40}', source_commit), 'unpinned converter commit')
    _require(type(available_bytes) is int and available_bytes >= 0, 'invalid available bytes')
    _require(type(disk_floor) is int and disk_floor >= 150 * GIB, 'disk floor cannot be lowered')
    files = {}
    for f in api['siblings']:
        name = f['rfilename']
        p = PurePosixPath(name)
        _require(not p.is_absolute() and '..' not in p.parts and str(p) == name, 'unsafe source path')
        _require(name not in files, 'duplicate source path')
        files[name] = f
    index_name = 'model.safetensors.index.json'
    _require(index_name in files, 'missing shard index')
    index_file = files[index_name]
    blob = hashlib.sha1(b'blob ' + str(len(index_bytes)).encode() + b'\0' + index_bytes).hexdigest()
    _require(blob == index_file.get('blobId') and len(index_bytes) == index_file.get('size'), 'index identity mismatch')
    index = json.loads(index_bytes)
    mapping = index.get('weight_map')
    _require(isinstance(mapping, dict) and mapping and all(isinstance(k, str) and k for k in mapping), 'invalid weight map')
    shards = set(mapping.values())
    _require(shards == {n for n in files if n.endswith('.safetensors')}, 'incomplete or extra shard coverage')
    selected = sorted(shards | {index_name, 'config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json', 'merges.txt', 'chat_template.jinja'})
    sources = []
    for name in selected:
        _require(name in files, 'missing conversion metadata: ' + name)
        f = files[name]
        size = f.get('size')
        _require(type(size) is int and size > 0, 'invalid source size')
        lfs = f.get('lfs')
        if lfs:
            _require(lfs.get('size') == size and re.fullmatch('[0-9a-f]{64}', lfs.get('sha256', '')), 'invalid LFS identity')
            identity = {'sha256': lfs['sha256']}
        else:
            _require(re.fullmatch('[0-9a-f]{40}', f.get('blobId', '')), 'missing git blob identity')
            identity = {'git_blob_sha1': f['blobId']}
        sources.append(dict(path=name, size=size, **identity,
                            url=f'https://huggingface.co/{api["id"]}/resolve/{revision}/{name}'))
    source_bytes = sum(f['size'] for f in sources)
    # Allow BF16 expansion from narrow input tensors, plus metadata/alignment.
    # Keep source and all three artifacts: no deletion-based admission assumption.
    per_output_cap = 2 * source_bytes + GIB
    peak = source_bytes + 3 * per_output_cap
    return dict(schema='epyc.target-precision.weight-plan.v1',
                base={'repo': api['id'], 'revision': revision}, sources=sources,
                converter_commit=source_commit,
                steps=[['python3', 'convert_hf_to_gguf.py', 'source', '--outtype', 'bf16', '--outfile', 'target-BF16.gguf'],
                       ['llama-quantize', 'target-BF16.gguf', 'target-Q8_0.gguf', 'Q8_0'],
                       ['llama-quantize', 'target-BF16.gguf', 'target-Q4_K_M.gguf', 'Q4_K_M']],
                storage=dict(source_bytes=source_bytes, per_output_cap_bytes=per_output_cap,
                             peak_additional_bytes=peak, disk_floor_bytes=disk_floor,
                             available_bytes=available_bytes, admitted=available_bytes >= disk_floor + peak),
                execution_admitted=False,
                remaining=['verify downloaded originals', 'bind converter and quantizer content/build identities',
                           'enforce output caps and resource floors during preparation',
                           'retain original conversion/quantization logs and output hashes',
                           'verify tensor and tokenizer correspondence', 'bind fixed drafter to pinned upstream',
                           'prepare weight receipt only after successful derivation'])


def tensor_storage_plan(plan, index_bytes, headers, available_bytes):
    """Size native tensors from bounded safetensors headers, without weight reads.

    Header digests identify fetched metadata, not the shard payload. F32 ceilings
    allow retained nonquantized tensors in every arm. Converter-added tensors and
    temporary workspace still require a converter-specific audit before execution.
    """
    import json
    import math
    import struct
    _require(type(available_bytes) is int and available_bytes >= 0, 'invalid available bytes')
    index_source = next(s for s in plan['sources'] if s['path'] == 'model.safetensors.index.json')
    blob = hashlib.sha1(b'blob ' + str(len(index_bytes)).encode() + b'\0' + index_bytes).hexdigest()
    _require(blob == index_source['git_blob_sha1'], 'index identity mismatch')
    mapping = json.loads(index_bytes)['weight_map']
    shards = {s['path']: s for s in plan['sources'] if s['path'].endswith('.safetensors')}
    _require(set(headers) == set(shards), 'header shard coverage mismatch')
    widths = {'BF16': 2, 'F16': 2, 'F32': 4, 'F64': 8,
              'I64': 8, 'I32': 4, 'I16': 2, 'I8': 1, 'U8': 1, 'BOOL': 1}
    seen, receipts = set(), []
    elements = payload = 0
    for shard, source in sorted(shards.items()):
        raw = headers[shard]
        _require(len(raw) >= 8, 'truncated header prefix')
        n = struct.unpack('<Q', raw[:8])[0]
        _require(0 < n <= 16 * 1024 * 1024 and len(raw) == n + 8, 'invalid header length')
        def unique(pairs):
            d = {}
            for key, value in pairs:
                _require(key not in d, 'duplicate header key')
                d[key] = value
            return d
        catalog = json.loads(raw[8:], object_pairs_hook=unique)
        _require(isinstance(catalog, dict), 'invalid tensor catalog')
        spans = []
        for name, tensor in catalog.items():
            if name == '__metadata__':
                continue
            _require(name not in seen and mapping.get(name) == shard, 'tensor index correspondence mismatch')
            seen.add(name)
            shape, dtype, offsets = tensor.get('shape'), tensor.get('dtype'), tensor.get('data_offsets')
            _require(isinstance(shape, list) and all(type(d) is int and d >= 0 for d in shape), 'invalid tensor shape')
            _require(dtype in widths, 'unsupported source dtype')
            _require(isinstance(offsets, list) and len(offsets) == 2 and
                     all(type(o) is int and o >= 0 for o in offsets), 'invalid data offsets')
            count = math.prod(shape)
            _require(offsets[1] - offsets[0] == count * widths[dtype], 'tensor byte count mismatch')
            spans.append(tuple(offsets))
            elements += count
        cursor = 0
        for start, end in sorted(spans):
            _require(start == cursor, 'overlap or gap in shard payload')
            cursor = end
        _require(cursor + len(raw) == source['size'], 'shard size mismatch')
        payload += cursor
        receipts.append(dict(path=shard, header_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    _require(seen == set(mapping), 'missing indexed tensor')
    # No optimistic Q4 bits-per-weight admission: mixed quantization may retain
    # F32 tensors. Explicit metadata reserve and per-tensor alignment in all arms.
    cap = 4 * elements + 32 * len(seen) + GIB
    peak = plan['storage']['source_bytes'] + 3 * cap
    floor = plan['storage']['disk_floor_bytes']
    _require(type(floor) is int and floor >= 150 * GIB, 'disk floor cannot be lowered')
    return dict(schema='epyc.target-precision.tensor-sizing.v1', base=plan['base'],
                converter_commit=plan['converter_commit'], headers=receipts,
                tensor_count=len(seen), elements=elements, source_payload_bytes=payload,
                bf16_payload_bytes=2 * elements, f32_payload_ceiling_bytes=4 * elements,
                per_output_cap_bytes=cap, peak_additional_bytes=peak,
                disk_floor_bytes=floor, available_bytes=available_bytes,
                disk_envelope_fits=available_bytes >= floor + peak,
                execution_admitted=False,
                limitations=['headers are not verified shard payloads',
                             'audit converter tensor additions and temporary workspace',
                             'verify tool/output, tokenizer and drafter correspondence',
                             'recheck all resource floors immediately before acquisition'])

#!/usr/bin/env python3
"""Extract Qwen35MoE verify-pass layer IDs from GGUF headers, not weights.

Requires gguf-py from the pinned v10 llama.cpp tree on PYTHONPATH. This is a
source-derived expected graph, not proof of actual graph construction, flash
attention use, binary identity, event delivery, or accelerator residency.
"""
import argparse
import hashlib
import json
import os


def derive_layers(metadata, tensor_names):
    if metadata.get('general.architecture') != 'qwen35moe':
        raise ValueError('unsupported architecture')
    total = metadata.get('qwen35moe.block_count')
    nextn = metadata.get('qwen35moe.nextn_predict_layers', 0)
    interval = metadata.get('qwen35moe.full_attention_interval', 4)
    if (type(total) is not int or not 1 <= total <= 512 or type(nextn) is not int
            or nextn not in (0, 1) or nextn >= total or type(interval) is not int or not 1 <= interval <= total):
        raise ValueError('invalid or unsupported architecture dimensions')
    trunk = total - nextn
    recurrent = metadata.get('qwen35moe.attention.recurrent_layers')
    if recurrent is None:
        recurrent = [(i + 1) % interval != 0 for i in range(trunk)] + [False] * nextn
        source = 'full_attention_interval'
    else:
        if not isinstance(recurrent, list) or len(recurrent) != total or any(type(x) is not bool for x in recurrent):
            raise ValueError('invalid recurrent layer array')
        if any(recurrent[trunk:]):
            raise ValueError('recurrent MTP layers unsupported')
        source = 'attention.recurrent_layers'
    attention = [i for i in range(trunk) if not recurrent[i]]
    names = set(tensor_names)
    for i in attention + list(range(trunk, total)):
        if any(f'blk.{i}.{n}.weight' not in names for n in ('attn_q', 'attn_k', 'attn_v', 'attn_output')):
            raise ValueError(f'missing separate full-attention tensor header for layer {i}')
    if not attention:
        raise ValueError('empty trunk attention set')
    return {'verify_attention_layer_ids': attention, 'mtp_attention_layer_ids': list(range(trunk, total)),
            'total_layers': total, 'trunk_layers': trunk, 'nextn_layers': nextn, 'layer_rule': source}


def extract(path):
    from gguf import GGUFReader
    before = os.stat(path)
    reader = GGUFReader(path)
    keys = ('general.architecture', 'general.name', 'qwen35moe.block_count',
            'qwen35moe.nextn_predict_layers', 'qwen35moe.full_attention_interval',
            'qwen35moe.attention.recurrent_layers')
    metadata = {k: reader.fields[k].contents() for k in keys if k in reader.fields}
    manifest = derive_layers(metadata, [t.name for t in reader.tensors])
    with open(path, 'rb') as f:
        digest = hashlib.sha256(f.read(reader.data_offset)).hexdigest()
    after = os.stat(path)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('model changed while reading header')
    manifest.update(metadata=metadata, provenance={'path': os.path.realpath(path), 'size_bytes': before.st_size,
                    'header_bytes': reader.data_offset, 'header_sha256': digest,
                    'source_commit': 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115',
                    'source_files': ['src/llama-model.cpp', 'src/llama-hparams.cpp', 'src/models/qwen35moe.cpp'],
                    'scope': 'header digest only; does not identify weight bytes'})
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('gguf')
    args = parser.parse_args()
    print(json.dumps(extract(args.gguf), indent=2))

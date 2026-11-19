#!/usr/bin/env python3
"""Reproduce the architect-general loader reshape witness without opening a server."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

from gguf import GGUFReader

ARCH_SOURCE = 'src/models/qwen4exp.cpp'
LOADER_SOURCE = 'src/llama-model-loader.cpp'
TENSORS = {
    'blk.0.hc_attn_norm.weight': 'LLM_TENSOR_HC_ATTN_NORM',
    'blk.0.hc_ffn_norm.weight': 'LLM_TENSOR_HC_FFN_NORM',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def stat_id(path):
    value = path.stat()
    return [value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def build_loader_witness(plan_path, kernel):
    envelope = json.loads(plan_path.read_bytes())
    raw = base64.b64decode(envelope['bytes_b64'], validate=True)
    if sha(raw) != envelope['sha256']:
        raise ValueError('archived plan bytes differ from their digest')
    plan = json.loads(raw)
    if plan['profile'] != 'architect-general-hip':
        raise ValueError('expected the isolated architect-general HIP profile')
    model = plan['model_shards']
    metadata = {}
    tensors = {}
    for pin in model:
        path = Path(pin['path'])
        if stat_id(path) != pin['stat']:
            raise ValueError(f'pinned model shard changed: {path.name}')
        reader = GGUFReader(path)
        for key in ('general.architecture', 'qwen4exp.embedding_length', 'qwen4exp.hyper_connection.count'):
            if key in reader.fields:
                value = reader.fields[key].contents()
                if metadata.setdefault(key, value) != value:
                    raise ValueError(f'conflicting metadata: {key}')
        for tensor in reader.tensors:
            if tensor.name in TENSORS:
                if tensor.name in tensors:
                    raise ValueError(f'duplicate tensor: {tensor.name}')
                tensors[tensor.name] = {
                    'disk_shape': [int(dim) for dim in tensor.shape],
                    'tensor_type': tensor.tensor_type.name,
                    'tensor_bytes': int(tensor.n_bytes),
                    'shard': path.name, 'shard_sha256': pin['sha256'],
                }
        if stat_id(path) != pin['stat']:
            raise ValueError(f'pinned model shard changed while reading: {path.name}')
    if metadata['general.architecture'] != 'qwen4exp' or tensors.keys() != TENSORS.keys():
        raise ValueError('expected the qwen4exp architecture and both layer-0 norm tensors')
    embedding = metadata['qwen4exp.embedding_length']
    hyper_connections = metadata['qwen4exp.hyper_connection.count']
    if type(embedding) is not int or type(hyper_connections) is not int or min(embedding, hyper_connections) <= 1:
        raise ValueError('expected nontrivial dimensions in GGUF')
    elements = embedding * hyper_connections
    for tensor in tensors.values():
        if tensor['disk_shape'] != [elements] or tensor['tensor_type'] != 'F32' or tensor['tensor_bytes'] != 4 * elements:
            raise ValueError('GGUF dimensions/type cannot establish the expected size-preserving reshape')
    runtimes = {}
    for name, arm in plan['arms'].items():
        commit = arm['kernel_commit']
        tree = git(kernel, 'rev-parse', f'{commit}^{{tree}}').decode().strip()
        if tree != arm['kernel_tree']:
            raise ValueError(f'{name}: kernel source tree differs')
        arch = git(kernel, 'show', f'{commit}:{ARCH_SOURCE}')
        candidate = name == 'candidate'
        shape = '{ n_embd, hc }' if candidate else '{ hc_dim }'
        declarations = {}
        for tensor, symbol in TENSORS.items():
            matching = [line.strip() for line in arch.decode().splitlines()
                        if 'create_tensor' in line and symbol in line and shape in line
                        and ('TENSOR_ALLOW_RESHAPE' in line) == candidate]
            if len(matching) != 1:
                raise ValueError(f'{name}: loader declaration shifted for {tensor}')
            declarations[tensor] = matching[0]
        loader = git(kernel, 'show', f'{commit}:{LOADER_SOURCE}')
        if candidate and any(fragment not in loader for fragment in (
            b'if (flags & TENSOR_ALLOW_RESHAPE)',
            b't_meta.ne[dim] = dim < ne.size() ? ne.begin()[dim] : 1;',
            b't_meta.nb[dim] = ggml_row_size(t_meta.type, t_meta.ne[dim-1]);',
            b'ggml_nbytes(&t_meta) == ggml_nbytes(cur)',
        )):
            raise ValueError('candidate reshape implementation shifted')
        runtimes[name] = {
            'kernel_commit': commit, 'kernel_tree': tree,
            'loader_source_sha256': sha(loader), 'arch_source_sha256': sha(arch),
            'tensor_declarations': declarations,
            'loader_shape': [embedding, hyper_connections] if candidate else [elements],
            'loader_reshape_expected': candidate,
        }
    return {
        'schema': 'epyc.quality_pack_loader_reshape_witness.v1',
        'scope': 'GGUF metadata and pinned source inspection. Fresh native runs establish loaded runtime and output.',
        'profile': plan['profile'], 'source_plan_sha256': sha(raw),
        'model_shard_sha256': [pin['sha256'] for pin in model],
        'gguf_metadata': metadata, 'tensors': tensors, 'runtime_source': runtimes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('kernel', type=Path)
    args = parser.parse_args()
    print(json.dumps(build_loader_witness(args.plan, args.kernel), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()

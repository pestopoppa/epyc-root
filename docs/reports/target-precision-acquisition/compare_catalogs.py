#!/usr/bin/env python3
"""Compare complete GGUF tensor catalogs without loading tensor payloads.

Structural correspondence is necessary, but cannot prove shared source weights.
Use the pinned downloader manifest separately for complete artifact identity.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def merge_shards(shards):
    if not shards:
        raise ValueError('no shards')
    merged = {}
    for shard in shards:
        if not shard:
            raise ValueError('empty shard catalog')
        for name, dims in shard.items():
            if not isinstance(name, str) or not name:
                raise ValueError('invalid tensor name')
            if not isinstance(dims, list) or not dims or any(type(d) is not int or d <= 0 for d in dims):
                raise ValueError('invalid tensor shape')
            if name in merged:
                raise ValueError('duplicate tensor across shards: ' + name)
            merged[name] = dims
    return merged


def compare(arms):
    if len(arms) < 2:
        raise ValueError('at least two arms required')
    merged = {name: merge_shards(shards) for name, shards in arms.items()}
    reference = next(iter(merged))
    baseline = merged[reference]
    differences = {}
    for name, tensors in merged.items():
        if name == reference:
            continue
        differences[name] = {
            'missing': sorted(baseline.keys() - tensors.keys()),
            'extra': sorted(tensors.keys() - baseline.keys()),
            'shape_mismatch': {key: {'reference': baseline[key], 'candidate': tensors[key]}
                               for key in sorted(baseline.keys() & tensors.keys()) if baseline[key] != tensors[key]},
        }
    matched = all(not any(diff.values()) for diff in differences.values())
    return {'schema': 'epyc.target-precision.catalog-comparison.v1',
            'reference': reference, 'tensor_counts': {k: len(v) for k, v in merged.items()},
            'differences': differences, 'structural_correspondence': matched,
            'causal_precision_gate': 'UNRESOLVED',
            'limitations': ['Catalog equality does not establish identical source weights or base revision.',
                            'Header inspection does not verify full-artifact digests, tokenizer equivalence, or runtime controls.']}


def validate_split_set(records):
    counts = {r['split_count'] for r in records}
    if counts == {None}:
        if len(records) != 1:
            raise ValueError('multiple files without split metadata')
        return
    if None in counts or len(counts) != 1:
        raise ValueError('inconsistent split count')
    count = next(iter(counts))
    if type(count) is not int or count < 1 or len(records) != count:
        raise ValueError('incomplete split set')
    if sorted(r['split_no'] for r in records) != list(range(count)):
        raise ValueError('duplicate or missing split number')
    totals = {r['split_tensors'] for r in records}
    if len(totals) != 1 or next(iter(totals)) != sum(r['catalog_tensor_count'] for r in records):
        raise ValueError('inconsistent split tensor total')


def read_catalog(path, reader_class):
    reader = reader_class(path)
    if reader.data_offset > len(reader.data):
        raise ValueError('truncated catalog')
    tensors = {}
    for field in reader.catalog_fields:
        name = field.parts[1].tobytes().decode('utf-8')
        if name in tensors:
            raise ValueError('duplicate tensor within shard: ' + name)
        tensors[name] = [int(d) for d in field.parts[3]]
    def value(key):
        field = reader.fields.get(key)
        return field.contents() if field is not None else None
    if value('GGUF.tensor_count') != len(tensors):
        raise ValueError('incomplete tensor catalog')
    return tensors, {'path': str(path), 'catalog_end_aligned': int(reader.data_offset),
                     'catalog_tensor_count': len(tensors), 'split_no': value('split.no'),
                     'split_count': value('split.count'), 'split_tensors': value('split.tensors.count'),
                     'catalog_sha256': hashlib.sha256(json.dumps(tensors, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gguf-python', type=Path, required=True)
    parser.add_argument('--arm', action='append', required=True, help='NAME=PATH; repeat NAME for shards')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.gguf_python))
    from gguf import GGUFReader

    class HeaderReader(GGUFReader):
        def _build_tensors(self, start_offs, fields):
            self.catalog_fields = fields

    arms, inspected = {}, []
    for arg in args.arm:
        name, sep, path = arg.partition('=')
        if not sep or not name or not path:
            parser.error('arm requires NAME=PATH')
        tensors, evidence = read_catalog(Path(path), HeaderReader)
        arms.setdefault(name, []).append(tensors)
        evidence['arm'] = name
        inspected.append(evidence)
    for name in arms:
        validate_split_set([r for r in inspected if r['arm'] == name])
    result = compare(arms)
    result['inspected'] = inspected
    reader_path = args.gguf_python / 'gguf' / 'gguf_reader.py'
    result['reader'] = {'path': str(reader_path), 'sha256': hashlib.sha256(reader_path.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'structural_correspondence': result['structural_correspondence'],
                      'tensor_counts': result['tensor_counts'], 'causal_precision_gate': 'UNRESOLVED'}))
    return 0 if result['structural_correspondence'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

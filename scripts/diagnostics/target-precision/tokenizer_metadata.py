"""Bounded, typed GGUF tokenizer-metadata comparison; no tensor payload reads.

A PASS establishes metadata equality to the supplied vocabulary-only GGUF.
It does not establish the reference's source/build provenance, tokenization
behavior, tensor correspondence, or verified weight identity. It deliberately
does not implement the conversion.v1/source-release authorization protocol.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

from release_sources import require, signature
from acquisition import safe_directory

BYTE_CAP = 128 * 1024 * 1024
ITEM_CAP = 2_000_000
FORMATS = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i',
           6: 'f', 7: '?', 10: 'Q', 11: 'q', 12: 'd'}
REQUIRED = {'tokenizer.ggml.model', 'tokenizer.ggml.pre',
            'tokenizer.ggml.tokens', 'tokenizer.ggml.token_type',
            'tokenizer.ggml.merges'}


class MetadataReader:
    def __init__(self, stream, byte_cap, item_cap):
        self.stream = stream
        self.remaining = byte_cap
        self.items = item_cap
        self.digest = hashlib.sha256()
        self.consumed = 0

    def read(self, count):
        require(0 <= count <= self.remaining, 'metadata byte budget exceeded')
        data = self.stream.read(count)
        require(len(data) == count, 'truncated GGUF metadata')
        self.remaining -= count
        self.consumed += count
        self.digest.update(data)
        return data

    def number(self, fmt):
        return struct.unpack('<'+fmt, self.read(struct.calcsize('<'+fmt)))[0]

    def string(self):
        return self.read(self.number('Q')).decode('utf-8', errors='strict')

    def value(self, kind):
        self.items -= 1
        require(self.items >= 0, 'metadata item budget exceeded')
        if kind == 8:
            return self.string()
        if kind == 9:
            element, count = self.number('I'), self.number('Q')
            require(element in FORMATS or element == 8, 'nested/unknown GGUF array type')
            require(count <= self.items, 'metadata item budget exceeded')
            return [element, [self.value(element) for _ in range(count)]]
        require(kind in FORMATS, 'unknown GGUF value type')
        if kind == 7:
            raw = self.number('B')
            require(raw in (0, 1), 'noncanonical GGUF boolean')
            return bool(raw)
        # IEEE bit equality matters even for signed zero; JSON also cannot
        # faithfully carry NaN payloads. Store floats as exact serialized bytes.
        if kind in (6, 12):
            return self.read(struct.calcsize('<'+FORMATS[kind])).hex()
        return self.number(FORMATS[kind])


def read_metadata(path, *, byte_cap=BYTE_CAP, item_cap=ITEM_CAP):
    """Read through the KV table only, retaining type tags as well as values."""
    path = Path(path).absolute()
    safe_directory(path.parent)
    require(type(byte_cap) is int and 24 <= byte_cap <= BYTE_CAP, 'invalid byte cap')
    require(type(item_cap) is int and 1 <= item_cap <= ITEM_CAP, 'invalid item cap')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb', buffering=0) as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                'single-link regular GGUF required')
        reader = MetadataReader(stream, byte_cap, item_cap)
        require(reader.read(4) == b'GGUF' and reader.number('I') == 3,
                'little-endian GGUF v3 required')
        tensor_count, count = reader.number('Q'), reader.number('Q')
        require(count <= item_cap, 'metadata field budget exceeded')
        fields, seen = {}, set()
        for _ in range(count):
            key = reader.string()
            require(key and key not in seen, 'empty/duplicate GGUF key')
            seen.add(key)
            kind = reader.number('I')
            value = reader.value(kind)
            if key.startswith('tokenizer.'):
                fields[key] = [kind, value]
        require(signature(before) == signature(os.fstat(stream.fileno())),
                'GGUF changed during metadata read')
        require(signature(before) == signature(os.stat(path, follow_symlinks=False)),
                'GGUF path changed during metadata read')
    require(REQUIRED <= fields.keys(), 'incomplete tokenizer metadata')
    require(fields['tokenizer.ggml.model'] == [8, 'gpt2'], 'GPT2/BPE profile required')
    require(fields['tokenizer.ggml.pre'][0] == 8 and fields['tokenizer.ggml.pre'][1],
            'pretokenizer required')
    tokens, types, merges = [fields['tokenizer.ggml.'+k]
                             for k in ('tokens', 'token_type', 'merges')]
    require(tokens[0] == types[0] == merges[0] == 9 and tokens[1][0] == merges[1][0] == 8
            and types[1][0] == 5, 'invalid vocabulary array types')
    require(tokens[1][1] and len(tokens[1][1]) == len(types[1][1]),
            'token/type inventory mismatch')
    require(all(type(t) is int and 1 <= t <= 6 for t in types[1][1]), 'invalid token type')
    return dict(path=str(path), file_size=before.st_size, tensor_count=tensor_count,
                metadata_bytes=reader.consumed, metadata_sha256=reader.digest.hexdigest(),
                fields=fields)


def compare(reference, output):
    expected, actual = read_metadata(reference), read_metadata(output)
    require(expected['path'] != actual['path'], 'distinct reference/output required')
    require(expected['tensor_count'] == 0 and actual['tensor_count'] > 0,
            'vocabulary-only reference and tensor-bearing output required')
    a, b = expected.pop('fields'), actual.pop('fields')
    mismatches = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    return dict(schema='epyc.target-precision.tokenizer-metadata.v1',
                verdict='FAIL' if mismatches else 'PASS', mismatched_keys=mismatches,
                reference=expected, output=actual, compared_fields=len(a.keys() | b.keys()),
                source_provenance_verified=False, behavior_verified=False,
                tensor_correspondence_verified=False, verified_weights=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    receipt = Path(args.receipt).absolute()
    require(receipt not in (Path(args.reference).absolute(), Path(args.output).absolute()),
            'receipt must be separate')
    result = compare(args.reference, args.output)
    with receipt.open('x') as stream:
        stream.write(json.dumps(result, sort_keys=True)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

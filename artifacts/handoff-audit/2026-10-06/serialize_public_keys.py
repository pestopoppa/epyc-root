#!/usr/bin/env python3
"""Serialize audit task keys for public artifacts without changing their identity.

Transforms only exact box/key-reference values declared by manifest.json. The
encoding is reversible and output lives in a separate directory; inputs are
never modified. Run with --input and --output paths.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

HEX16 = re.compile(r'^[0-9a-f]{16}$')
PUBLIC = re.compile(r'^h:([0-9a-f]{4}):([0-9a-f]{4}):([0-9a-f]{4}):([0-9a-f]{4})$')
KEY_FIELDS = {'key', 'reviewed_open_keys', 'keys', 'task_keys', 'live_key', 'historical_key'}


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def encode(key: str) -> str:
    if not HEX16.fullmatch(key):
        raise ValueError(f'not a manifest task-key digest: {key!r}')
    return 'h:' + ':'.join(key[i:i+4] for i in range(0, 16, 4))


def decode(key: str) -> str:
    m = PUBLIC.fullmatch(key)
    if not m:
        raise ValueError(f'not an encoded public task key: {key!r}')
    return ''.join(m.groups())


def task_keys(manifest: dict) -> set[str]:
    return {box['key'] for row in manifest['files'] for box in row.get('boxes', [])}


def transform(value, field: str | None, known: set[str], reverse: bool = False):
    if isinstance(value, dict):
        return {k: transform(v, k, known, reverse) for k, v in value.items()}
    if isinstance(value, list):
        if field in KEY_FIELDS:
            out = []
            for item in value:
                if isinstance(item, str) and (decode(item) in known if reverse and PUBLIC.fullmatch(item) else item in known):
                    out.append(decode(item) if reverse else encode(item))
                else:
                    out.append(transform(item, None, known, reverse))
            return out
        return [transform(item, None, known, reverse) for item in value]
    if isinstance(value, str) and field in KEY_FIELDS:
        if reverse and PUBLIC.fullmatch(value):
            original = decode(value)
            return original if original in known else value
        if not reverse and value in known:
            return encode(value)
    return value


def artifact_paths(input_dir: Path):
    # Input is the dedicated generated audit-artifact directory. Include overlap
    # and semantic cross-check sidecars as well as shard/review/decision JSON.
    return sorted(p for p in input_dir.glob('*.json')
                  if p.is_file() and p.name != 'serialization-provenance.json')

def tree_hashes(directory: Path) -> dict[str, str]:
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    src = args.input.resolve()
    out = args.output.resolve()
    if src == out or src in out.parents:
        raise SystemExit('output must be a separate directory outside the input tree')
    manifest = json.loads((src / 'manifest.json').read_text())
    known = task_keys(manifest)
    if any(not HEX16.fullmatch(k) for k in known):
        raise SystemExit('manifest contains a task key outside the exact lowercase 16-hex contract')
    before_tree = tree_hashes(src)
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    total_transformed = 0
    for path in artifact_paths(src):
        original_bytes = path.read_bytes()
        original = json.loads(original_bytes)
        public = transform(original, None, known)
        restored = transform(public, None, known, reverse=True)
        if restored != original:
            raise SystemExit(f'{path.name}: reversible decode differs from original JSON data')
        raw = json.dumps(public, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
        (out / path.name).write_bytes(raw)
        reopened = json.loads(raw)
        if transform(reopened, None, known, reverse=True) != original:
            raise SystemExit(f'{path.name}: serialized public JSON fails decode round-trip')
        orig_rows = original.get('files', []) if isinstance(original, dict) and isinstance(original.get('files'), list) else []
        public_rows = public.get('files', []) if isinstance(public, dict) and isinstance(public.get('files'), list) else []
        original_texts = [b['text'] for f in orig_rows for b in f.get('boxes', [])]
        public_texts = [b['text'] for f in public_rows for b in f.get('boxes', [])]
        if original_texts != public_texts:
            raise SystemExit(f'{path.name}: task text changed during public serialization')
        original_hashes = [f.get('sha256') for f in orig_rows]
        public_hashes = [f.get('sha256') for f in public_rows]
        if original_hashes != public_hashes:
            raise SystemExit(f'{path.name}: source SHA-256 metadata changed')
        before_refs = sum(1 for v in _walk(original) if isinstance(v, str) and v in known)
        total_transformed += before_refs
        entries.append({
            'path': path.name,
            'input_bytes_sha256': hashlib.sha256(original_bytes).hexdigest(),
            'canonical_data_sha256': hashlib.sha256(canonical_bytes(original)).hexdigest(),
            'decoded_public_canonical_data_sha256': hashlib.sha256(canonical_bytes(restored)).hexdigest(),
            'task_key_references_encoded': before_refs,
            'task_text_and_source_hashes_unchanged': True
        })
    after_tree = tree_hashes(src)
    if before_tree != after_tree:
        changed = sorted(k for k in set(before_tree) | set(after_tree) if before_tree.get(k) != after_tree.get(k))
        raise SystemExit(f'input tree bytes changed during generation: {changed}')
    metadata = {
        'format': 'public-task-key-presentation-v1',
        'encoding': 'h:<4 lowercase hex>:<4 lowercase hex>:<4 lowercase hex>:<4 lowercase hex>',
        'meaning': 'Reversible grouped presentation of the original exact manifest task-key digest; decode by concatenating four groups. This is serialization only, not redaction, identity replacement, or source modification.',
        'task_text_is_dispatch_identity': True,
        'source_sha256_fields_preserved': True,
        'original_input_tree_unchanged': True,
        'original_input_tree_file_count': len(before_tree),
        'original_input_tree_sha256_before_after_equal': True,
        'total_task_key_references_encoded': total_transformed,
        'artifacts': entries
    }
    (out / 'serialization-provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'artifacts': len(entries), 'task_keys': len(known), 'references_encoded': total_transformed, 'round_trip': 'exact decoded JSON equality', 'errors': []}, indent=2))
    return 0


def _walk(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k in KEY_FIELDS:
                if isinstance(v, str):
                    yield v
                elif isinstance(v, list):
                    yield from (x for x in v if isinstance(x, str))
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)

if __name__ == '__main__':
    raise SystemExit(main())

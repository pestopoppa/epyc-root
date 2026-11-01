#!/usr/bin/env python3
"""Create SHA-bound strategy-prompt variants without running inference."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(base_path: Path, expected_sha256: str, source_commit: str,
            source_path: str, output: Path) -> dict:
    if len(source_commit) != 40 or any(c not in '0123456789abcdef' for c in source_commit):
        raise ValueError('source commit must be a full lowercase git SHA-1')
    if not source_path or Path(source_path).is_absolute() or '..' in Path(source_path).parts:
        raise ValueError('source path must be relative without parent traversal')
    base = base_path.read_bytes()
    if digest(base) != expected_sha256:
        raise ValueError('base prompt digest mismatch')
    if output.exists() and any(output.iterdir()):
        raise ValueError('output directory must be empty')
    additions = Path(__file__).resolve().parent
    arms = {'baseline': base}
    for name, file in [('strategy_short', 'short.txt'), ('strategy_long', 'long.txt')]:
        suffix = (additions / file).read_bytes().strip()
        if not suffix:
            raise ValueError('empty strategy prompt')
        arms[name] = base + b'\n\nStrategy guidance:\n' + suffix + b'\n'
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'schema': 'epyc.strategy_prompt_ablation.preparation.v1',
                'source_commit': source_commit, 'source_path': source_path,
                'source_sha256': digest(base), 'arms': {}}
    for name, data in arms.items():
        path = output / (name + '.txt')
        path.write_bytes(data)
        manifest['arms'][name] = {'file': path.name, 'sha256': digest(data), 'bytes': len(data)}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--base-sha256', required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--source-path', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.base, args.base_sha256, args.source_commit, args.source_path, args.output)


if __name__ == '__main__':
    main()

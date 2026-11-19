#!/usr/bin/env python3
"""Prepare the full source candidate only; builds/native runs require rows."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import native_port
import server_port

HERE = Path(__file__).resolve().parent
HEADERS = ('controller.h', 'round_lifecycle.h', 'model_boundary.h', 'native_sink.h')


def transformed(read):
    server = server_port.server_context(read('tools/server/server-context.cpp'))
    server = native_port.replace_once(server, '#include "round_lifecycle.h"', '#include "native_sink.h"')
    server = native_port.replace_once(server, '            slots.emplace_back();',
        '            slots.emplace_back();\n            slots.back().cafe3_factory = cafe3::make_native_lifecycle;')
    return {'common/speculative.h': native_port.header(read('common/speculative.h')),
            'common/speculative.cpp': native_port.implementation(read('common/speculative.cpp')),
            'tools/server/server-context.cpp': server}


def prepare(tree):
    tree = tree.resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tree), *args], text=True).strip()
    # Refuse production, an old base, or any pre-existing tracked/untracked edits.
    if not tree.is_relative_to(Path('/mnt/raid0/llm/tmp/df2')):
        raise ValueError('candidate must be in df2 scratch')
    if subprocess.run(['git', '-C', str(tree), 'symbolic-ref', '-q', 'HEAD'],
                      stdout=subprocess.DEVNULL).returncode == 0:
        raise ValueError('candidate must be a detached experimental worktree')
    if git('rev-parse', 'HEAD') != native_port.PRODUCTION or git('rev-parse', 'refs/heads/production-consolidated-v10^{commit}') != native_port.PRODUCTION:
        raise ValueError('production base changed; review port before rebuilding')
    if git('status', '--porcelain'):
        raise ValueError('candidate must start clean')
    outputs = transformed(lambda path: (tree / path).read_text())
    outputs.update({'common/' + name: (HERE / name).read_text() for name in HEADERS})
    # All anchor validation occurs before writing any file.
    for name, text in outputs.items():
        (tree / name).write_text(text)
    manifest = {'schema': 'epyc.cafe3.source.v1', 'production': native_port.PRODUCTION,
                'files': {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in outputs}}
    (tree / 'cafe3-source.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(prepare(Path(sys.argv[1])), indent=2))

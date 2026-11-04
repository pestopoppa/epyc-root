#!/usr/bin/env python3
"""Bind a future G8 run to a completed, content-verified build receipt.

No model weight is read or hashed here. A caller must separately establish model
preflight, admitted resource ownership, captured process identity, GPU residency,
STOP/drain, and the exact request/trace protocol.
"""
import hashlib
import json
import re
from pathlib import Path

SOURCE = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
PATCH = 'bf4011f6fd65c48647699cea06aae9193585e875c9fb5612add805bba4e7b219'


class BindingError(ValueError):
    pass


def _digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def bind_receipt(receipt):
    if not isinstance(receipt, dict) or receipt.get('schema') != 'epyc.g8.build.v1' or receipt.get('mode') != 'build':
        raise BindingError('not a full G8 build receipt')
    if receipt.get('source_commit') != SOURCE or receipt.get('patch_sha256') != PATCH:
        raise BindingError('wrong source or instrumentation patch')
    try:
        run = Path(receipt['run']).resolve(strict=True)
        build = run / 'build'
        required = {'server': build / 'bin/llama-server', 'server_impl': build / 'bin/libllama-server-impl.so', 'common': build / 'bin/libllama-common.so',
                    'hip': build / 'bin/libggml-hip.so', 'llama': build / 'bin/libllama.so',
                    'patch': run / 'receipt/source.patch', 'linkage': run / 'receipt/linkage.log',
                    'cache': build / 'CMakeCache.txt'}
        files = receipt['files']
        if not isinstance(files, dict):
            raise BindingError('receipt files missing')
        bound = {}
        for name, path in required.items():
            p = path.resolve(strict=True)
            if not p.is_relative_to(run) or not p.is_file():
                raise BindingError('artifact outside run')
            expected = files.get(str(p))
            actual = _digest(p)
            if not isinstance(expected, str) or expected != actual:
                raise BindingError('artifact digest mismatch: ' + name)
            bound[name] = {'path': str(p), 'sha256': actual}
        if bound['patch']['sha256'] != PATCH:
            raise BindingError('patch digest mismatch')
        if b'G8_COMPARE_BEGIN' not in Path(bound['common']['path']).read_bytes():
            raise BindingError('trace marker missing from implementation')
        linkage = Path(bound['linkage']['path']).read_text(encoding='utf-8')
        if not linkage.strip() or 'not found' in linkage.lower():
            raise BindingError('linkage evidence missing or failed')
        matches = re.findall(r'^\s*OK\s+libllama-common\.so(?:\.[^\s]+)?\s+->\s+(\S+)\s*$', linkage, re.M)
        if len(matches) != 1 or Path(matches[0]).resolve(strict=True) != Path(bound['common']['path']):
            raise BindingError('linked common library does not match marker-bearing artifact')
        return {'status': 'BUILD_BOUND', 'run': str(run), 'source_commit': SOURCE, 'patch_sha256': PATCH,
                'artifacts': bound, 'scope': 'artifact identity only; no live residency or admission'}
    except (KeyError, OSError, TypeError, UnicodeError) as exc:
        raise BindingError('incomplete or unreadable build receipt') from exc

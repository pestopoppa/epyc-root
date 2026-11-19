#!/usr/bin/env python3
"""Bind G3's future runtime to its actual timestamped V4 build receipt.

This checks build content only. It does not verify an active grant, GPU device
ownership, runtime mappings, observation-window overlap, or process drain.
"""
import hashlib
from pathlib import Path

SOURCE = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
PATCH = '3c2e57bfdf98a8cae15dfec9d0719cc210c1b51f38c7c0f4a1c0a3aee7cbd97d'


class ReceiptError(ValueError):
    pass


def _digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def bind_v4_receipt(record, expected_root, *, expected_patch=PATCH):
    """Validate native result's artifacts against their content-bound receipt.

    expected_root is trusted launcher configuration, not a value read from the
    result. expected_patch may be overridden only by tests.
    """
    if not isinstance(record, dict) or record.get('schema') != 'epyc.g3.build.v1' or record.get('mode') != 'build':
        raise ReceiptError('not a complete native G3 build result')
    if record.get('source_commit') != SOURCE or record.get('patch_sha256') != expected_patch:
        raise ReceiptError('wrong source or V4 patch')
    try:
        root = Path(expected_root).resolve(strict=True)
        run = Path(record['run']).resolve(strict=True)
        if run.parent != root / 'runs':
            raise ReceiptError('build outside expected runs root')
        build = run / 'build'
        required = {'server': build / 'bin/llama-server',
                    'server_impl': build / 'bin/libllama-server-impl.so',
                    'hip': build / 'bin/libggml-hip.so',
                    'llama': build / 'bin/libllama.so',
                    'patch': run / 'receipt/source.patch',
                    'source_after': run / 'receipt/source-after.patch',
                    'linkage': run / 'receipt/linkage.log',
                    'cache': build / 'CMakeCache.txt'}
        files = record['files']
        if not isinstance(files, dict):
            raise ReceiptError('missing artifact digests')
        bound = {}
        for label, path in required.items():
            path = path.resolve(strict=True)
            if not path.is_relative_to(run) or not path.is_file():
                raise ReceiptError('artifact outside run')
            actual = _digest(path)
            # source-after is retained by the native builder but absent from its
            # result's file list; its content must equal the pinned patch.
            expected = expected_patch if label == 'source_after' else files.get(str(path))
            if actual != expected:
                raise ReceiptError('digest mismatch: ' + label)
            bound[label] = {'path': str(path), 'sha256': actual}
        if bound['patch']['sha256'] != expected_patch:
            raise ReceiptError('unsealed source patch')
        for label, markers in {
            'server_impl': (b'G3_TARGET_BEGIN_V3', b'G3_TARGET_END_V3', b'time_ns=%lld'),
            'hip': (b'G3_FATTN_DISPATCH_V3', b'time_ns=%lld'),
            'llama': (b'g3_fattn_layer_',),
        }.items():
            blob = Path(bound[label]['path']).read_bytes()
            if any(marker not in blob for marker in markers):
                raise ReceiptError('compiled marker missing: ' + label)
        linkage = Path(bound['linkage']['path']).read_text(encoding='utf-8')
        if not linkage.strip() or 'not found' in linkage.lower():
            raise ReceiptError('empty or failed linkage record')
        return {'status': 'BUILD_BOUND', 'source_commit': SOURCE,
                'patch_sha256': expected_patch, 'artifacts': bound,
                'scope': 'build identity only; no claim of runtime residency or grant'}
    except (OSError, KeyError, TypeError, UnicodeError) as exc:
        raise ReceiptError('missing or unreadable native build receipt') from exc

#!/usr/bin/env python3
"""Reopen and validate the build receipt before row completion."""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

from integrity import verify as verify_integrity
from custody import create_manifest

ROOT = pathlib.Path('/mnt/raid0/llm/tmp/kvu/kpf174-custody-r4-20261104')
COMPILER_PATHS = (
    '/usr/bin/cc',
    '/usr/bin/c++',
    '/opt/rocm-6.2.0/lib/llvm/bin/clang++',
)


def digest_file(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_compilers(compilers, expected_paths=None):
    """Require every declared compiler and reject missing, extra, or altered tools."""
    if not isinstance(compilers, dict):
        raise ValueError('compiler digest map is missing or malformed')
    use_host_namespace = expected_paths is None
    expected_paths = COMPILER_PATHS if use_host_namespace else expected_paths
    canonical = set(expected_paths)
    if set(compilers) != canonical:
        missing = sorted(canonical - set(compilers))
        extra = sorted(set(compilers) - canonical)
        raise ValueError(f'compiler set mismatch (missing={missing}, extra={extra})')
    for name in sorted(canonical):
        expected = compilers[name]
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError(f'invalid compiler SHA-256 for {name}')
    if use_host_namespace:
        # The build runs in /proc/1/root; the completion hook can run outside
        # that chroot, where ROCm's clang++ path may not exist or may differ.
        try:
            result = subprocess.run(
                ['/usr/bin/sudo', '-n', '/usr/bin/chroot', '/proc/1/root',
                 '/usr/bin/sha256sum', '--', *sorted(canonical)],
                check=True, capture_output=True, text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f'cannot verify host compiler digests: {exc}') from exc
        actuals = {}
        for line in result.stdout.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                actuals[parts[1].lstrip('*')] = parts[0]
    else:
        actuals = {}
        for name in canonical:
            path = pathlib.Path(name)
            if not path.is_file():
                raise ValueError(f'required compiler missing: {name}')
            actuals[name] = digest_file(path)
    for name, expected in compilers.items():
        if actuals.get(name) != expected:
            raise ValueError(f'compiler missing or digest mismatch: {name}')


def validate_receipt(d, root=ROOT):
    if os.environ.get('FILLER_DRYRUN') == '1':
        assert d['schema'] == 'epyc.kpf174d.first_unit.v1' and d['status'] == 'compiled'
        assert d['source_commit'] == '6ec877068936588b6d63dbba5842bbd540b92031'
        assert d['source_sha256'] == 'd4619db202efa483c26403e62a0cbf82846b887d1dce44fab6e3ad54fecfa2d9'
        assert d['target'] == 'src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o'
        r = pathlib.Path(d['run_dir']).resolve(strict=True)
        assert r.parent == (root/'runs').resolve(strict=True)
        assert d['integrity'] == verify_integrity(actual_cache=r/'build/CMakeCache.txt')
        paths = [r/'build'/d['target'], r/'build/compile_commands.json', r/'build/CMakeCache.txt', r/'configure.log', r/'first-unit.log']
        assert set(d['files']) == {str(x.resolve(strict=True)) for x in paths}
        for path in paths:
            h = hashlib.sha256(path.read_bytes()).hexdigest()
            assert h == d['files'][str(path.resolve(strict=True))]
        assert 'LLAMA_KPF_LAYOUT_TRACE' in subprocess.check_output(['strings', str(paths[0])], text=True)
        return
    assert d['schema'] == 'epyc.kpf174d.build.v1' and d['status'] == 'built'
    assert d['linkage_verifier_sha256'] == '57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
    assert digest_file(root/'v3/verify_ggml_linkage.sh') == d['linkage_verifier_sha256']
    assert d['source_commit'] == '6ec877068936588b6d63dbba5842bbd540b92031'
    assert d['parent_source'] == '84d0a31603d495377dee24e1159bbbf02f1e2f21'
    assert d['linkage_pass'] is True and d['knobs'] == ['LLAMA_KPF_LAYOUT_TRACE', 'LLAMA_KPF_ITEM4_TRACE', '--slot-fork-min-tokens']
    assert len(d['binary_sha256']) == 64
    assert set(d['libraries']) == {'libllama.so', 'libllama-common.so', 'libllama-server-impl.so', 'libggml-hip.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so'}
    assert all(len(x) == 64 for x in d['libraries'].values())
    verify_compilers(d['compilers'])
    r = pathlib.Path(d['run_dir']).resolve(strict=True)
    assert r.parent == (root / 'runs').resolve(strict=True)
    assert d['integrity'] == verify_integrity(actual_cache=r/'build/CMakeCache.txt')
    names = [pathlib.Path(k).name for k in d['files']]
    assert d['files'][str((r / 'build/bin/llama-server').resolve(strict=True))] == d['binary_sha256']
    for lib, val in d['libraries'].items():
        assert d['files'][str((r / 'build/bin' / lib).resolve(strict=True))] == val
    for prefix in ('llama-server', 'libllama.so', 'libllama-common.so', 'libllama-server-impl.so', 'libggml-hip.so'):
        assert any(n.startswith(prefix) for n in names), prefix
    assert json.loads((root/'CUSTODY.json').read_text()) == create_manifest(r/'build/bin', root/'RESULT.json')
    for name, expected in d['files'].items():
        path = pathlib.Path(name).resolve(strict=True)
        assert path.is_relative_to(r)
        assert digest_file(path) == expected


def main():
    p = os.environ.get('FILLER_DRYRUN_RESULT_PATH') if os.environ.get('FILLER_DRYRUN') == '1' else str(ROOT / 'RESULT.json')
    try:
        validate_receipt(json.loads(pathlib.Path(p).read_text()))
    except (AssertionError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f'build receipt refused: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

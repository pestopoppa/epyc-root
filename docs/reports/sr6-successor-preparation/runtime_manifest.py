#!/usr/bin/env python3
"""Verify a caller-pinned kernel manifest and selected CPU server artifacts.

This is an input preflight, not authority for a source commit, a runtime linkage
proof, model identity, sampler selection, or proof that loaded bytes remain
unchanged after the check. The caller must bind the manifest digest to an
approved build and independently verify the running process's linkage.
No model weights are read by this module.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

HEX = re.compile(r'[0-9a-f]{64}\Z')
REQUIRED = frozenset({
    'bin/llama-server', 'bin/libllama-server-impl.so',
    'bin/libllama.so.0.0.10303', 'bin/libllama-common.so.0.0.10303',
    'bin/libmtmd.so.0.0.10303',
    'bin/libggml.so.0.16.0', 'bin/libggml-base.so.0.16.0',
    'bin/libggml-cpu.so.0.16.0',
})


def _read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise ValueError('regular bounded file required')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            data = f.read(limit + 1)
        if len(data) > limit or len(data) != st.st_size:
            raise ValueError('file changed or exceeded limit')
        after = os.fstat(fd)
        if (st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('file changed during read')
        return data
    finally:
        os.close(fd)


def verify_runtime_manifest(build_root, manifest_sha256):
    """Compare eight named v10 server artifacts to a pinned SHA256SUMS file."""
    if not isinstance(build_root, Path) or not build_root.is_absolute() or build_root.is_symlink() or not build_root.is_dir():
        raise ValueError('absolute real build root required')
    if not isinstance(manifest_sha256, str) or not HEX.fullmatch(manifest_sha256):
        raise ValueError('manifest digest required')
    try:
        raw = _read_regular(build_root / 'SHA256SUMS', 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != manifest_sha256:
            raise ValueError('manifest digest mismatch')
        found = {}
        for line in raw.decode('ascii').splitlines():
            match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.+/-]+)', line)
            if not match:
                raise ValueError('invalid manifest line')
            digest, name = match.groups()
            if name in found:
                raise ValueError('duplicate manifest path')
            found[name] = digest
        if not REQUIRED <= found.keys():
            raise ValueError('required artifacts missing')
        bin_dir = build_root / 'bin'
        if bin_dir.is_symlink() or not bin_dir.is_dir():
            raise ValueError('real bin directory required')
        checked = {}
        for name in sorted(REQUIRED):
            observed = hashlib.sha256(_read_regular(build_root / name, 1024 * 1024 * 1024)).hexdigest()
            if observed != found[name]:
                raise ValueError('artifact digest mismatch: ' + name)
            checked[name] = observed
        return {'manifest_sha256': manifest_sha256, 'artifacts': checked,
                'limitations': ['manifest approval and source binding are external',
                                'runtime linkage, model and sampler unverified']}
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError('runtime preflight failed') from exc

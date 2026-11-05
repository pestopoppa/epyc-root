#!/usr/bin/env python3
"""Private ELF/memfd loader fixture; no model or ggml is loaded."""
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
stopped = False

def stop(*_):
    global stopped
    stopped = True

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

def boundary():
    if stopped or (D / 'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):
        raise RuntimeError('STOP')
    if time.time() >= float(os.environ.get('FILLER_DEADLINE', os.environ.get('FILLER_END', '9999999999'))):
        raise RuntimeError('deadline')

def main():
    smoke = os.environ.get('FILLER_SMOKE') == '1' or os.environ.get('FILLER_DRYRUN') == '1'
    out = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'out/RESULT.json'
    if sys.argv[1:] == ['--complete']:
        result = json.loads(out.read_text())
        if result['smoke'] is not smoke or result['status'] != 'PASS' or result['case_count'] != 4 or not all(c['ok'] for c in result['cases']):
            raise RuntimeError('incomplete')
        boundary()
        return
    boundary()
    if smoke and len(os.sched_getaffinity(0)) != 4:
        raise RuntimeError('smoke affinity')
    # The output is unique to this process and is deleted after the ELF is sealed.
    obj = D / ('fixture-%d.so' % os.getpid())
    try:
        subprocess.run(['/usr/bin/cc', '-shared', '-fPIC', '-o', str(obj), str(D / 'fixture.c')], check=True, timeout=60)
        boundary()
        blob = obj.read_bytes()
    finally:
        obj.unlink(missing_ok=True)
    fd = os.memfd_create('kpf17-sealed-elf', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        offset = 0
        while offset < len(blob):
            offset += os.write(fd, blob[offset:])
        seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        lib = ctypes.CDLL('/proc/self/fd/%d' % fd)
        func = lib.sealed_fixture_value
        func.restype = ctypes.c_int
        info = os.fstat(fd)
        lines = Path('/proc/self/maps').read_text().splitlines()
        maps = [line for line in lines if len(line.split()) >= 6
                and tuple(int(part, 16) for part in line.split()[3].split(':')) == (os.major(info.st_dev), os.minor(info.st_dev))
                and line.split()[4] == str(info.st_ino) and 'memfd:kpf17-sealed-elf' in line]
        cases = [{'case':'loaded_value', 'ok':func() == 1729},
                 {'case':'sealed_and_mapped', 'ok':bool(maps) and fcntl.fcntl(fd, fcntl.F_GET_SEALS) & seals == seals}]
        boundary()
        alias = os.open('/proc/self/fd/%d' % fd, os.O_RDWR | os.O_CLOEXEC)
        try:
            try:
                os.pwrite(alias, b'X', 0)
                refused = False
            except OSError as e:
                if e.errno != errno.EPERM:
                    raise
                refused = True
            cases.append({'case':'alias_write_refused', 'ok':refused})
            boundary()
            cases.append({'case':'bytes_and_call_unchanged', 'ok':os.pread(fd, len(blob), 0) == blob and func() == 1729})
        finally:
            os.close(alias)
        if not all(c['ok'] for c in cases):
            raise RuntimeError('control mismatch')
        result = {'schema':'kpf17.sealed-elf-loader.v1', 'status':'PASS', 'smoke':smoke,
                  'case_count':len(cases), 'cases':cases, 'elf_sha256':hashlib.sha256(blob).hexdigest(),
                  'fixture_sha256':hashlib.sha256((D / 'fixture.c').read_bytes()).hexdigest(),
                  'device':info.st_dev, 'inode':info.st_ino, 'maps':maps,
                  'scope':'private ELF fixture and same-process alias; not ggml, cross-process, build identity or complete custody'}
    finally:
        os.close(fd)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise RuntimeError('output exists')
    tmp = out.with_name(out.name + '.tmp')
    with tmp.open('x') as f:
        json.dump(result, f, sort_keys=True)
        f.write('\n')
    boundary()
    os.replace(tmp, out)

if __name__ == '__main__':
    main()

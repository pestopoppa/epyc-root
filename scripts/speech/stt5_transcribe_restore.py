#!/usr/bin/env python3
"""Source-bound CPU rebuild of the independent STT5 native-token runner.

No audio or model inputs. Smoke and grant builds are isolated; a stopped build
is retained and cannot be mistaken for a complete artifact or retried silently.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

WITNESSES = (b'CS8_NEMO_TOKENS %d', b'CS8_NEMO_TOKEN %d %d', b'CS8_NEMO_TOKENS_END')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    with Path(path).open('x') as f:
        json.dump(data, f, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def verify(cfg):
    source = cfg['source']
    def git(*args):
        return subprocess.check_output(['git', '-C', source, *args])
    if git('rev-parse', 'HEAD').decode().strip() != cfg['commit']:
        raise ValueError('source commit drift')
    if hashlib.sha256(git('diff', 'HEAD', '--binary')).hexdigest() != cfg['diff_sha256']:
        raise ValueError('source overlay drift')
    if git('ls-files', '--others', '--exclude-standard').strip():
        raise ValueError('untracked source inputs')
    for path, digest in cfg['pins'].items():
        if sha(path) != digest:
            raise ValueError('prepared input drift: ' + path)


def session_members(session):
    """Only processes in the new session whose leader PID we captured."""
    live = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[3]) == session and fields[0] != 'Z':
                live.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return live


def drain(child):
    members = session_members(child.pid)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in members:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        until = time.monotonic() + 5
        while time.monotonic() < until:
            child.poll()  # reap leader as soon as possible
            members = session_members(child.pid)
            if not members:
                child.wait()
                return
            time.sleep(.05)
    raise RuntimeError('owned build session still alive: ' + str(members))


def binary_evidence(path):
    data = Path(path).read_bytes()
    if not data.startswith(b'\x7fELF') or not all(marker in data for marker in WITNESSES):
        raise ValueError('compiled native witness absent')
    return sha(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config', type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    verify(cfg)
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    out = Path(cfg['smoke_output'] if smoke else cfg['output'])
    out.mkdir(exist_ok=True)
    binding = sha(args.config)
    write_new(out / 'START.json', dict(config_sha256=binding, started_epoch=time.time(),
              row_id=os.environ.get('FILLER_ID'), cpus=sorted(os.sched_getaffinity(0)), smoke=smoke))
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    build = out / 'build'
    commands = [
        ['cmake', '-S', cfg['source'], '-B', str(build), '-DCMAKE_BUILD_TYPE=Release',
         '-DTRANSCRIBE_BUILD_TESTS=OFF', '-DTRANSCRIBE_BUILD_EXAMPLES=ON',
         '-DTRANSCRIBE_BUILD_SHARED=ON', '-DTRANSCRIBE_USE_OPENMP=OFF',
         '-DTRANSCRIBE_CUDA=OFF', '-DTRANSCRIBE_HIP=OFF', '-DTRANSCRIBE_METAL=OFF',
         '-DTRANSCRIBE_USE_SYSTEM_BLAS=OFF'],
        ['cmake', '--build', str(build), '--target', 'transcribe-cli', '--parallel',
         str(min(24, len(os.sched_getaffinity(0))))],
    ]
    stopfile = Path(os.environ.get('FILLER_STOPFILE', str(out.parent / 'STOP')))
    deadline = float(os.environ.get('FILLER_DEADLINE', time.time() + 1800)) - 20
    for index, cmd in enumerate(commands):
        if stopping or stopfile.exists() or time.time() >= deadline:
            return 75
        with (out / f'step-{index}.log').open('xb') as log:
            child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            try:
                while child.poll() is None:
                    if stopping or stopfile.exists() or time.time() >= deadline:
                        drain(child)
                        return 75
                    time.sleep(.1)
                if child.returncode:
                    write_new(out / 'FAIL.json', dict(command=cmd, rc=child.returncode))
                    return child.returncode
            finally:
                drain(child)
    verify(cfg)
    binary = build / 'bin/transcribe-cli'
    digest = binary_evidence(binary)
    libs = sorted((build / 'ggml/src').rglob('libggml*.so.*'))
    libs += sorted((build / 'src').glob('libtranscribe.so.*'))
    libs = sorted({p.resolve() for p in libs})
    if not libs:
        raise ValueError('no build libraries')
    write_new(out / 'summary.json', dict(schema='stt5-transcribe-restore/v1',
              verdict='PASS', config_sha256=binding, source_commit=cfg['commit'],
              source_diff_sha256=cfg['diff_sha256'], binary=str(binary), binary_sha256=digest,
              libraries={str(p): sha(p) for p in libs}, native_witness_compiled=True,
              smoke=smoke, parity_established=False, validation_exposed=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Rebuild retained Voxtral trace overlays, without audio or weight exposure.

This creates NEW runtime identities. Neither byte identity with historical
runners nor parity is inferred. All process cleanup uses the shared owned-
session drain from the independent-runner restoration driver.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time

from stt5_transcribe_restore import drain, sha, verify, write_new

WITNESSES = (b'CS8_VOXTRAL_TOKENS %zu', b'CS8_VOXTRAL_TOKEN %zu %d',
             b'CS8_VOXTRAL_TOKENS_END')


def replace_one(command, old, new):
    if command.count(old) != 1:
        raise ValueError('expected exactly one build argument: ' + old)
    command = list(command)
    command[command.index(old)] = str(new)
    return command


def compile_overlay(entries, suffix, overlay, output, source):
    matches = [e for e in entries if e['file'].endswith('/' + suffix)]
    if len(matches) != 1:
        raise ValueError('ambiguous compile recipe: ' + suffix)
    entry = matches[0]
    cmd = shlex.split(entry['command'])
    if cmd.count('-o') != 1 or cmd.count('-c') != 1:
        raise ValueError('invalid compile recipe')
    cmd[cmd.index('-o') + 1] = str(output)
    cmd[cmd.index('-c') + 1] = str(overlay)
    cmd.insert(1, '-I' + str(Path(source) / 'examples/cli'))
    return cmd, entry['directory']


def witness(path):
    data = Path(path).read_bytes()
    if not data.startswith(b'\x7fELF') or not all(w in data for w in WITNESSES):
        raise ValueError('native trace witness absent')
    return sha(path)


def verify_all(cfg):
    verify(cfg)
    for tree, commit in cfg['submodules'].items():
        actual = subprocess.check_output(['git', '-C', tree, 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', tree, 'status', '--porcelain'])
        if actual != commit or dirty:
            raise ValueError('submodule source drift: ' + tree)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config', type=Path)
    cfgpath = ap.parse_args().config
    cfg = json.loads(cfgpath.read_text())
    verify_all(cfg)
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    out = Path(cfg['smoke_output'] if smoke else cfg['output'])
    out.mkdir(exist_ok=True)
    write_new(out / 'START.json', dict(config_sha256=sha(cfgpath), smoke=smoke,
              row_id=os.environ.get('FILLER_ID'), cpus=sorted(os.sched_getaffinity(0))))
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    stopfile = Path(os.environ.get('FILLER_STOPFILE', str(out.parent / 'STOP')))
    deadline = float(os.environ.get('FILLER_DEADLINE', time.time() + 3600)) - 20
    index = 0

    def run(cmd, cwd=None):
        nonlocal index
        if stopping or stopfile.exists() or time.time() >= deadline:
            raise InterruptedError
        with (out / f'step-{index}.log').open('xb') as log:
            index += 1
            child = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            try:
                while child.poll() is None:
                    if stopping or stopfile.exists() or time.time() >= deadline:
                        raise InterruptedError
                    time.sleep(.1)
                if child.returncode:
                    raise subprocess.CalledProcessError(child.returncode, cmd)
            finally:
                drain(child)

    build = out / 'build'
    try:
        run(['cmake', '-S', cfg['source'], '-B', str(build),
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
             '-DCRISPASR_BUILD_TESTS=OFF', '-DCRISPASR_BUILD_EXAMPLES=ON',
             '-DBUILD_SHARED_LIBS=ON', '-DGGML_BLAS=OFF', '-DGGML_CUDA=OFF',
             '-DGGML_HIP=OFF', '-DGGML_METAL=OFF', '-DGGML_VULKAN=OFF'])
        entries = json.loads((build / 'compile_commands.json').read_text())
        # Compile retained overlay first: smoke observes a genuine traced ELF
        # object, with no model load, then the publisher requests clean stop.
        for ms in (480, 960):
            variant = out / f'voxtral{ms}'
            variant.mkdir()
            run(*compile_overlay(entries, 'crispasr_backend_voxtral4b.cpp',
                 cfg['overlays'][str(ms)], variant / 'backend.o', cfg['source']))
            witness(variant / 'backend.o')
        run(['cmake', '--build', str(build), '--target', 'crispasr-cli',
             '--parallel', str(min(24, len(os.sched_getaffinity(0))))])
        v960 = out / 'voxtral960'
        run(*compile_overlay(entries, 'voxtral4b.cpp', cfg['delay960'],
                             v960 / 'voxtral4b.o', cfg['source']))
        run(['ar', 'qc', str(v960 / 'libvoxtral4b.a'), str(v960 / 'voxtral4b.o')])
        run(['ranlib', str(v960 / 'libvoxtral4b.a')])
        libcmd = shlex.split((build / 'src/CMakeFiles/crispasr-lib.dir/link.txt').read_text())
        libcmd = replace_one(libcmd, 'libvoxtral4b.a', v960 / 'libvoxtral4b.a')
        libcmd = replace_one(libcmd, 'libcrispasr.so.0.8.44', v960 / 'libcrispasr.so.0.8.44')
        run(libcmd, build / 'src')
        (v960 / 'libcrispasr.so.1').symlink_to('libcrispasr.so.0.8.44')
        artifacts = {}
        for ms in (480, 960):
            variant = out / f'voxtral{ms}'
            cmd = shlex.split((build / 'examples/cli/CMakeFiles/crispasr-cli.dir/link.txt').read_text())
            cmd = replace_one(cmd, 'CMakeFiles/crispasr-cli.dir/crispasr_backend_voxtral4b.cpp.o', variant / 'backend.o')
            cmd[cmd.index('-o') + 1] = str(variant / 'crispasr')
            if ms == 960:
                cmd = replace_one(cmd, '../../src/libcrispasr.so.0.8.44', v960 / 'libcrispasr.so.0.8.44')
                cmd = replace_one(cmd, '../../src/libvoxtral4b.a', v960 / 'libvoxtral4b.a')
            run(cmd, build / 'examples/cli')
            artifacts[str(variant / 'crispasr')] = witness(variant / 'crispasr')
        verify_all(cfg)
        for p in sorted(build.rglob('*.so.*')) + [v960 / 'libcrispasr.so.0.8.44']:
            if p.is_file():
                artifacts[str(p.resolve())] = sha(p)
        write_new(out / 'summary.json', dict(schema='stt5-voxtral-restore/v1', verdict='PASS',
                  config_sha256=sha(cfgpath), source_commit=cfg['commit'], artifacts=artifacts,
                  smoke=smoke, historical_byte_identity=False, parity_established=False,
                  validation_exposed=False))
        return 0
    except InterruptedError:
        return 75
    except subprocess.CalledProcessError as exc:
        write_new(out / 'FAIL.json', dict(command=exc.cmd, rc=exc.returncode))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Owned-child source-header fixture; no server or model is launched."""
import argparse
import os
from pathlib import Path
import struct
import subprocess
import tempfile

PIN = 'a1f0c8cf9bd7102415a72577474f307b8ba94db9'
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition: raise ValueError(message)


def capture(fd, base, allowed_ids):
    raw = os.pread(fd, 0x48, base)
    require(len(raw) == 0x48, 'short ubatch read')
    count = struct.unpack_from('<I', raw, 0x10)[0]
    ptr = struct.unpack_from('<Q', raw, 0x40)[0]
    require(0 < count <= 3 and ptr == allowed_ids, 'count or pointer outside fixture bounds')
    ids = os.pread(fd, 4*count, ptr)
    require(len(ids) == 4*count, 'short seq id read')
    return count, list(struct.unpack('<'+'i'*count, ids))


def main(source, scratch):
    source = Path(source).resolve()
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    require(head == PIN, 'source commit mismatch')
    # Verify every compiler input tracked in the checkout is clean before compiling.
    status = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True)
    require(not status, 'source checkout modified')
    scratch = Path(scratch).resolve(); scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix='ubatch-native-') as d:
        binary = str(Path(d)/'fixture')
        subprocess.run(['c++', '-std=c++17', '-O0', '-I'+str(source/'src'), '-I'+str(source/'include'), '-I'+str(source/'ggml/include'), str(HERE/'fixture.cpp'), '-o', binary], check=True)
        child = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            line = child.stdout.readline().split()
            require(len(line) == 6, 'malformed child metadata')
            pid, base, ids, size, count_off, ptr_off = map(int, line)
            require(pid == child.pid and count_off == 0x10 and ptr_off == 0x40 and size >= 0x48, 'header/object offset mismatch')
            with open(f'/proc/{pid}/mem', 'rb', buffering=0) as mem:
                baseline = capture(mem.fileno(), base, ids)
                require(baseline == (3, [11, 22, 33]), 'baseline mismatch')
                child.stdin.write('r\n'); child.stdin.flush(); require(child.stdout.readline().strip() == 'ready', 'row mutation not acknowledged')
                row = capture(mem.fileno(), base, ids)
                require(row == (3, [11, 99, 33]) and row != baseline, 'row mutation missed')
                child.stdin.write('n\n'); child.stdin.flush(); require(child.stdout.readline().strip() == 'ready', 'count mutation not acknowledged')
                count = capture(mem.fileno(), base, ids)
                require(count == (2, [11, 99]) and count != row, 'count mutation missed')
            child.stdin.write('q\n'); child.stdin.flush()
            require(child.wait(timeout=10) == 0, 'child exit failure')
            print('PASS: historical source-header ubatch own-child read; row and count mutations observed')
        finally:
            if child.poll() is None:
                child.kill(); child.wait()
            child.stdin.close(); child.stdout.close()

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source', required=True); p.add_argument('--scratch', required=True)
    args = p.parse_args(); main(args.source, args.scratch)

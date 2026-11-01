#!/usr/bin/env python3
"""Model-free exact-birth group drain: wrong birth must never signal."""
import pathlib
import subprocess

from owner_pregrant import drain_group


def main():
    proc = subprocess.Popen(['/bin/sleep', '30'], start_new_session=True)
    birth = int((pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
    try:
        try:
            drain_group(proc.pid, birth + 1, {proc.pid: birth})
        except RuntimeError as exc:
            assert 'leader PID reused' in str(exc)
        else:
            raise RuntimeError('wrong leader birth reached group signal')
        assert proc.poll() is None
        assert drain_group(proc.pid, birth, {proc.pid: birth})
        proc.wait(timeout=5)
        assert proc.poll() is not None
        print('wrong-birth group signal refused; captured birth drained; MODEL_FREE only')
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)


if __name__ == '__main__':
    main()

"""Run the captured tokenizer with bounded stop/deadline response."""
import subprocess
import time


class Stopped(Exception):
    pass


def run(argv, data, env, stopping, timeout, *, popen=subprocess.Popen, clock=time.monotonic):
    if stopping():
        raise Stopped('stop before tokenizer')
    p = popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    end = clock() + timeout
    first = True
    try:
        while True:
            if stopping():
                raise Stopped('stop during tokenizer')
            left = end - clock()
            if left <= 0:
                raise TimeoutError('tokenizer timed out')
            try:
                out, err = p.communicate(input=data if first else None, timeout=min(.2, left))
                if p.returncode != 0:
                    raise RuntimeError('tokenizer failed: ' + err.decode('utf-8', errors='replace')[-1024:])
                return out
            except subprocess.TimeoutExpired:
                first = False
    finally:
        if p.poll() is None:
            try:
                p.terminate()
            except ProcessLookupError:
                pass
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()

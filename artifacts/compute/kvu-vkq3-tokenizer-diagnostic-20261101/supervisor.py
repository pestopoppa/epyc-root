"""Offline draft: bounded custody for one caller-supplied tokenizer child.

Not a rowflow worker. Caller must bind grant, input, binary and model identities,
private receipts and parent-death containment before use in a real diagnostic.
The cleanup field proves only that the direct child exited; it says nothing about descendants.
"""
import os
import selectors
import subprocess
import time


class CleanupError(RuntimeError):
    pass


def supervise(argv, input_bytes, env, *, stopped, timeout_s, stdout_cap=8_000_000,
              stderr_cap=65_536, cleanup_s=2.0):
    if timeout_s <= 0 or stdout_cap <= 0 or stderr_cap <= 0:
        raise ValueError('timeout and output caps must be positive')
    started = time.monotonic()
    if stopped():
        return {'status': 'cancelled', 'elapsed_s': 0.0, 'cleanup': True,
                'returncode': None, 'input_bytes_written': 0, 'stdout': b'', 'stderr': b''}
    stdout = bytearray()
    stderr = bytearray()
    pending = memoryview(input_bytes)
    status = None
    input_bytes_written = 0
    result = None
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=env, close_fds=True)
    selector = None
    try:
        selector = selectors.DefaultSelector()
        for pipe in (child.stdin, child.stdout, child.stderr):
            os.set_blocking(pipe.fileno(), False)
        selector.register(child.stdout, selectors.EVENT_READ, stdout)
        selector.register(child.stderr, selectors.EVENT_READ, stderr)
        if pending:
            selector.register(child.stdin, selectors.EVENT_WRITE, None)
        else:
            child.stdin.close()
        while selector.get_map() or child.poll() is None:
            if stopped():
                status = 'cancelled'
                break
            remaining = timeout_s - (time.monotonic() - started)
            if remaining <= 0:
                status = 'timeout'
                break
            for key, _ in selector.select(min(0.1, remaining)):
                if key.fileobj is child.stdin:
                    try:
                        written = os.write(child.stdin.fileno(), pending[:65536])
                    except BrokenPipeError:
                        status = 'input_incomplete'
                        break
                    if written <= 0:
                        status = 'input_incomplete'
                        break
                    input_bytes_written += written
                    pending = pending[written:]
                    if not pending:
                        selector.unregister(child.stdin)
                        child.stdin.close()
                else:
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    else:
                        buf = key.data
                        cap = stdout_cap if buf is stdout else stderr_cap
                        if len(buf) + len(chunk) > cap:
                            buf.extend(chunk[:max(0, cap-len(buf))])
                            status = 'output_overflow'
                            break
                        buf.extend(chunk)
            if status:
                break
        if status is None:
            status = 'completed' if child.returncode == 0 else 'nonzero_exit'
    finally:
        if selector is not None:
            selector.close()
        for pipe in (child.stdin, child.stdout, child.stderr):
            if not pipe.closed:
                pipe.close()
        if child.poll() is None:
            try:
                child.terminate()
            except ProcessLookupError:
                pass  # The captured child exited between poll and signal.
            try:
                child.wait(timeout=cleanup_s)
            except subprocess.TimeoutExpired:
                try:
                    child.kill()
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=cleanup_s)
                except subprocess.TimeoutExpired as exc:
                    raise CleanupError('captured child did not reap') from exc
        else:
            child.wait()
        result = {'status': status, 'elapsed_s': time.monotonic()-started,
                  'cleanup': child.poll() is not None, 'returncode': child.returncode,
                  'input_bytes_written': input_bytes_written,
                  'stdout': bytes(stdout), 'stderr': bytes(stderr)}
    return result

"""Offline owned-server cancellation prototype; not a native launcher.

On uncertain client outcomes, terminate the captured server child, then reap it.
This does not establish descendant disappearance or GPU cleanup.  Complete
scientific verdicts are forbidden until a separate process-tree proof exists.
"""
import math
import subprocess
import time
import transport

class CleanupError(RuntimeError):
    pass


def stop_owned(child, term_grace=1.0, kill_grace=1.0):
    if not isinstance(child, subprocess.Popen):
        raise TypeError('captured Popen required')
    if not all(math.isfinite(x) and x > 0 for x in (term_grace, kill_grace)):
        raise ValueError('positive finite cleanup bounds required')
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=term_grace)
        except subprocess.TimeoutExpired:
            child.kill()
            try:
                child.wait(timeout=kill_grace)
            except subprocess.TimeoutExpired as exc:
                raise CleanupError('captured server could not be reaped') from exc
    if child.poll() is None:
        raise CleanupError('captured server still alive')
    return {'server_reaped': True, 'server_rc': child.returncode,
            'descendants_proven_absent': False}


def request_owned(child, url, body, *, stop_file, deadline, endpoint_owned, term_grace=1.0, kill_grace=1.0):
    """Request only a caller-verified owned endpoint; stop server on uncertainty.

    endpoint_owned must prove endpoint belongs to this captured server; this
    prototype delegates that proof and refuses if unavailable. Caller still owns
    normal-completion cleanup and must never treat server_reaped as tree cleanup.
    """
    if not isinstance(child, subprocess.Popen) or not callable(endpoint_owned):
        raise ValueError('captured server and endpoint ownership verifier required')
    if child.poll() is not None or endpoint_owned(child, url) is not True:
        raise ValueError('server is not live at verified owned endpoint')
    try:
        result = transport.request(url, body, stop_file=stop_file, deadline=deadline, term_grace=term_grace)
    except BaseException:
        stop_owned(child, term_grace, kill_grace)
        raise
    if result['state'] == 'unknown':
        cleanup = stop_owned(child, term_grace, kill_grace)
        return {**result, 'cleanup': cleanup}
    if result['state'] == 'complete' and (child.poll() is not None or endpoint_owned(child, url) is not True):
        cleanup = stop_owned(child, term_grace, kill_grace)
        return {'state':'unknown', 'reason':'ownership_changed', 'cleanup':cleanup}
    return result

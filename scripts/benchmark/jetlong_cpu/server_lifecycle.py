#!/usr/bin/env python3
"""Candidate server lifecycle for JetLong; requires owner integration, not a row.

One direct child, isolated environment, bounded request budget and cleanup.  The
caller must reserve an isolated endpoint, source-bind the binary and choose a
keeper-admitted CPU booking. Descendants are deliberately not signalled by name.
"""
import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

import runner
import provenance


class LaunchError(RuntimeError):
    pass


def _owned_listener(pid, base_url):
    """Fail closed unless this exact process owns the sole IPv4 listener."""
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path:
        raise LaunchError('endpoint must be an IPv4 loopback origin')
    try:
        inodes = set()
        for row in Path(f'/proc/{pid}/net/tcp').read_text().splitlines()[1:]:
            fields = row.split()
            address, port = fields[1].split(':')
            if int(port, 16) == parsed.port and fields[3] == '0A':
                if address not in ('0100007F', '00000000'):
                    raise LaunchError('unexpected listener address')
                inodes.add(fields[9])
        fds = Path(f'/proc/{pid}/fd')
        owned = {os.readlink(fd) for fd in fds.iterdir() if fd.is_symlink()}
        if len(inodes) != 1 or f'socket:[{next(iter(inodes))}]' not in owned:
            raise LaunchError('endpoint listener is not owned by captured server')
    except (OSError, ValueError, IndexError) as exc:
        raise LaunchError('cannot prove endpoint ownership') from exc


def _request(base_url, tokens, timeout_s, n_predict):
    body = json.dumps({'prompt': tokens, 'n_predict': n_predict,
                       'cache_prompt': False}).encode()
    req = urllib.request.Request(base_url + '/completion', data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as reply:
            return json.load(reply)
    except (TimeoutError, socket.timeout) as exc:
        raise TimeoutError('request timed out') from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise TimeoutError('request timed out') from exc
        raise


def _cleanup(child, term_s, kill_s):
    """Signal only the exact child started here and confirm it was reaped."""
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=term_s)
        except subprocess.TimeoutExpired:
            child.kill()
            try:
                child.wait(timeout=kill_s)
            except subprocess.TimeoutExpired as exc:
                raise LaunchError('owned server did not exit after SIGKILL') from exc
    else:
        child.wait()


def run_owned(*, command, env, base_url, plan_path, fixture_root, output_dir,
              arm, budget_s, minimum_cell_s, request_timeout_s, startup_s=30,
              term_s=5, kill_s=5, n_predict=128, log_path, runtime_check=None):
    """Start exactly one direct child, run one arm, and always reap that child.

    Never use against an existing endpoint: caller owns port admission. Startup
    and cleanup time are deducted from the grant budget. Exceptions propagate;
    an in-flight ledger start remains unknown on interruption or uncertain I/O.
    """
    if (not command or not all(isinstance(x, str) and x for x in command)
        or not base_url.startswith('http://127.0.0.1:')
        or min(budget_s, minimum_cell_s, request_timeout_s, startup_s, term_s, kill_s) <= 0
        or type(n_predict) is not int or n_predict <= 0):
        raise ValueError('invalid lifecycle configuration')
    if budget_s <= startup_s + term_s + kill_s:
        raise ValueError('budget does not cover startup and cleanup')
    if not env.get('LD_LIBRARY_PATH'):
        raise ValueError('an isolated library path is required')
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + budget_s
    # Signals are turned into exceptions so finally always reaps our child.
    old_handlers = {}
    def interrupted(signum, _frame):
        raise InterruptedError(f'interrupted by signal {signum}')
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.signal(sig, interrupted)
        with path.open('ab', buffering=0) as logfile:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                     stdout=logfile, stderr=subprocess.STDOUT,
                                     env=env, close_fds=True)
            try:
                startup_deadline = min(deadline - term_s - kill_s,
                                       time.monotonic() + startup_s)
                while time.monotonic() < startup_deadline:
                    if child.poll() is not None:
                        raise LaunchError(f'owned server exited rc={child.returncode}')
                    try:
                        with urllib.request.urlopen(base_url + '/health', timeout=0.25) as reply:
                            health = json.load(reply)
                        if health.get('status') == 'ok':
                            _owned_listener(child.pid, base_url)
                            break
                    except (OSError, ValueError, urllib.error.URLError):
                        pass
                else:
                    raise LaunchError('owned server health deadline expired')
                if child.poll() is not None:
                    raise LaunchError('owned server exited during startup')
                if runtime_check is not None:
                    runtime_check(child.pid)
                remaining = deadline - time.monotonic() - term_s - kill_s
                if remaining < minimum_cell_s:
                    return 75
                def transport(tokens, timeout):
                    _owned_listener(child.pid, base_url)
                    if runtime_check is not None:
                        runtime_check(child.pid)
                    result = _request(base_url, tokens, timeout, n_predict)
                    _owned_listener(child.pid, base_url)
                    if runtime_check is not None:
                        runtime_check(child.pid)
                    return result
                return runner.run_segment(plan_path, output_dir, fixture_root, arm,
                    transport,
                    remaining, minimum_cell_s, request_timeout_s)
            finally:
                _cleanup(child, term_s, kill_s)
    finally:
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


def run_verified(*, manifest, expected_dir, **kwargs):
    """Verify pinned small files and live library mappings; model custody is separate.

    This is still a prototype: source-to-build proof, descendant cleanup and
    a keeper entry must be supplied before any native row can be published.
    """
    artifacts = manifest.get('artifacts', {})
    command = kwargs.get('command', [])
    if not command or str(Path(command[0]).resolve()) not in artifacts:
        raise provenance.ProvenanceError('server executable not pinned')
    if kwargs.get('env', {}).get('LD_LIBRARY_PATH') != str(Path(expected_dir).resolve()):
        raise provenance.ProvenanceError('library path must be the pinned directory alone')
    provenance.check_artifacts(manifest)
    if 'runtime_check' in kwargs:
        raise ValueError('runtime check is owned by run_verified')
    return run_owned(runtime_check=lambda pid: provenance.check_live(pid, expected_dir, manifest), **kwargs)

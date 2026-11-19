"""Concrete captured-child owner for the prospective Q38 isolated-arm runner.

This module does not grant compute access. Callers must provide independent
native process/socket/mapped-library identity and descendant-drain verifiers;
without them the runtime refuses to dispatch or start another arm. It signals
only the exact child it captured, never a process-name pattern or a process group.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any, Callable

from q38_t7_runtime import SpawnFailure


def _birth(pid: int) -> str:
    text = Path(f'/proc/{pid}/stat').read_text()
    end = text.rfind(')')
    if end < 0:
        raise ValueError('invalid process stat')
    return text[end + 2:].split()[19]


def _sha256(path: str) -> str:
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _draft_flag(arg: str) -> bool:
    name = arg.split('=', 1)[0].lower()
    return name == '-md' or name.startswith(('--model-draft', '--draft', '--spec-', '--speculative'))


def command_for(arm: str, recipe: dict[str, Any], *, verify_digests: bool = True) -> tuple[list[str], dict[str, str]]:
    """Build from a common recipe and explicit arm fields; reject ambiguity."""
    if arm not in ('drafted', 'nodraft') or set(recipe) != {
        'binary', 'model', 'shape', 'draft_model', 'draft_options'
    }:
        raise ValueError('invalid arm or recipe')
    binary, model, shape = recipe['binary'], recipe['model'], recipe['shape']
    if not isinstance(binary, str) or not os.path.isabs(binary):
        raise ValueError('binary must be an absolute path')
    if not isinstance(model, str) or not os.path.isabs(model):
        raise ValueError('model must be an absolute path')
    if not isinstance(shape, dict) or set(shape) != {
        'common_argv', 'binary_sha256', 'model_sha256', 'env'
    }:
        raise ValueError('invalid common recipe shape')
    args, env = shape['common_argv'], shape['env']
    if not isinstance(args, list) or not all(isinstance(a, str) and a for a in args):
        raise ValueError('invalid common argv')
    if any(_draft_flag(a) for a in args):
        raise ValueError('draft options must not occur in common argv')
    if any(a.startswith('--model=') or (a.startswith('-m') and a != '-m') for a in args):
        raise ValueError('ambiguous model options are not allowed')
    model_flags = [i for i, arg in enumerate(args) if arg in ('-m', '--model')]
    if len(model_flags) != 1 or model_flags[0] + 1 >= len(args) or args[model_flags[0] + 1] != model:
        raise ValueError('common argv must name the pinned main model exactly once')
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ValueError('explicit string environment required')
    if any(k.upper().startswith('LLAMA_ARG_') or 'DRAFT' in k.upper() for k in env):
        raise ValueError('ambient llama and draft environment forbidden')
    if verify_digests and (_sha256(binary) != shape['binary_sha256'] or _sha256(model) != shape['model_sha256']):
        raise ValueError('binary or model digest mismatch')
    options, draft = recipe['draft_options'], recipe['draft_model']
    argv = [binary, *args]
    if arm == 'nodraft':
        if draft is not None or options != {}:
            raise ValueError('no-draft server cannot carry draft configuration')
    else:
        if not isinstance(draft, str) or not os.path.isabs(draft) or not isinstance(options, dict):
            raise ValueError('drafted server requires explicit draft')
        if set(options) != {'type', 'n_max', 'draft_sha256'}:
            raise ValueError('invalid draft options')
        if options['type'] != 'draft-dflash' or type(options['n_max']) is not int or options['n_max'] < 1:
            raise ValueError('invalid speculative recipe')
        if verify_digests and _sha256(draft) != options['draft_sha256']:
            raise ValueError('draft digest mismatch')
        argv += ['-md', draft, '--spec-type', options['type'], '--spec-draft-n-max', str(options['n_max'])]
    return argv, dict(env)


@dataclass
class Handle:
    process: subprocess.Popen
    birth: str
    pidfd: int
    argv: list[str]
    arm: str
    recipe: dict[str, Any]
    recipe_sha256: str
    closed: bool = False


class Supervisor:
    """Own a launched child; independently supplied verifiers enforce custody.

    identity_verifier(handle, arm, recipe) must establish the mapped binary,
    libraries, mode and listening socket. drain_verifier(handle) must establish
    descendant drain, not just child exit. Neither proof can be guessed here.
    """

    def __init__(self, identity_verifier: Callable, drain_verifier: Callable,
                 *, log_path: str, stop_timeout: float = 5.0):
        if not callable(identity_verifier) or not callable(drain_verifier):
            raise ValueError('native identity and drain verifiers are mandatory')
        self.identity_verifier, self.drain_verifier = identity_verifier, drain_verifier
        self.log_path, self.stop_timeout = log_path, stop_timeout

    def spawn(self, arm: str, recipe: dict[str, Any]) -> Handle:
        argv, env = command_for(arm, recipe)
        with open(self.log_path, 'ab', buffering=0) as log:
            try:
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                           env=env, close_fds=True, start_new_session=True)
            except Exception as exc:
                raise SpawnFailure(f'spawn failed before child capture: {exc}', True) from exc
        pidfd = None
        try:
            pidfd = os.pidfd_open(process.pid)
            birth = _birth(process.pid)
            if process.poll() is not None:
                raise RuntimeError('child exited before identity capture')
            recipe_copy = copy.deepcopy(recipe)
            recipe_hash = hashlib.sha256(json.dumps(recipe_copy, sort_keys=True, separators=(',', ':'),
                                                     allow_nan=False).encode()).hexdigest()
            return Handle(process, birth, pidfd, argv, arm, recipe_copy, recipe_hash)
        except BaseException as exc:
            # This exact PID belongs to our unreaped Popen child. Descendant
            # custody was not established, so cleanup remains unverified.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=self.stop_timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=self.stop_timeout)
            if pidfd is not None:
                os.close(pidfd)
            raise SpawnFailure(f'identity capture failed: {exc}', False) from exc

    def verify(self, handle: Handle, arm: str, recipe: dict[str, Any]) -> bool:
        if handle.closed or handle.process.poll() is not None:
            return False
        try:
            # Full model/draft hashing belongs at launch, not on every request;
            # the native identity and tokenizer attestors must independently
            # bind the actually loaded model throughout the run.
            argv, _ = command_for(arm, recipe, verify_digests=False)
            recipe_hash = hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(',', ':'),
                                                     allow_nan=False).encode()).hexdigest()
            return (arm == handle.arm and recipe_hash == handle.recipe_sha256
                    and argv == handle.argv and _birth(handle.process.pid) == handle.birth
                    and self.identity_verifier(handle, arm, recipe) is True
                    and handle.process.poll() is None
                    and _birth(handle.process.pid) == handle.birth)
        except Exception:
            return False

    def wait_ready(self, handle: Handle, arm: str, recipe: dict[str, Any], *, timeout: float = 10.0) -> bool:
        """Wait for the exact captured process to satisfy native identity."""
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            if self.verify(handle, arm, recipe):
                return True
            if handle.process.poll() is not None or time.monotonic() >= deadline:
                return False
            time.sleep(min(.05, max(0.0, deadline - time.monotonic())))

    def stop_and_drain(self, handle: Handle) -> bool:
        if handle.closed:
            return False
        try:
            if handle.process.poll() is None:
                if _birth(handle.process.pid) != handle.birth:
                    return False
                signal.pidfd_send_signal(handle.pidfd, signal.SIGTERM)
                try:
                    handle.process.wait(timeout=self.stop_timeout)
                except subprocess.TimeoutExpired:
                    signal.pidfd_send_signal(handle.pidfd, signal.SIGKILL)
                    handle.process.wait(timeout=self.stop_timeout)
            if handle.process.poll() is None or self.drain_verifier(handle) is not True:
                return False
        except Exception:
            return False
        os.close(handle.pidfd)
        handle.closed = True
        return True

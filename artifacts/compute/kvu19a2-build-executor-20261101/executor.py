"""Fail-closed command execution coordinator for a prospective KVU build.

No CLI or concrete supervisor is provided. A caller must supply a verified,
identity-safe supervisor, bound source/tool evidence, and a native journal.
"""
import hashlib
import json


class Incomplete(RuntimeError):
    pass


def command_digest(command):
    if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x or '\x00' in x for x in command):
        raise ValueError('command must be a nonempty argv of nonempty strings')
    return hashlib.sha256(json.dumps(command, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def execute(plan, journal, supervisor, verify_inputs, verify_outputs, stop_requested):
    """Execute a frozen plan through injected custody interfaces.

    supervisor.run(argv) returns (integer exit code, exact bool cleanup receipt).
    If run raises after spawning, it must own and drain all children itself; the
    exception cannot establish cleanup, so this coordinator always fails closed.
    verify_inputs must bind the actual compiler inputs at the point of use.
    No command after any failure, STOP, or unverified cleanup may run.
    """
    mode = plan.get('mode')
    if mode not in ('qualification', 'target'):
        raise Incomplete('invalid mode')
    def check_mode():
        if plan.get('mode') != mode:
            raise Incomplete('plan mode changed')
    commands = plan.get('commands')
    if not isinstance(commands, list) or not commands:
        raise Incomplete('no commands')
    frozen = [list(cmd) if isinstance(cmd, list) else cmd for cmd in commands]
    digests = [command_digest(cmd) for cmd in frozen]
    if stop_requested() or verify_inputs(mode) is not True:
        raise Incomplete('STOP or input custody unverified')
    check_mode()
    for index, (command, digest) in enumerate(zip(frozen, digests)):
        if stop_requested() or verify_inputs(mode) is not True:
            raise Incomplete('STOP or changed input custody')
        check_mode()
        journal.start(index, digest)
        check_mode()
        try:
            rc, cleanup = supervisor.run(command)
        except BaseException as exc:
            # Caller must retain any partial native journal; absence of a command-end
            # cannot be converted into completion even when cleanup was attempted.
            raise Incomplete('command or supervisor failed; cleanup unverified') from exc
        if type(rc) is not int or type(cleanup) is not bool:
            raise Incomplete('invalid supervisor receipt')
        journal.end(index, rc, cleanup)
        if rc != 0 or cleanup is not True:
            raise Incomplete('command failed or cleanup unverified')
        check_mode()
    if stop_requested() or verify_outputs(mode) is not True:
        raise Incomplete('STOP or output evidence unverified')
    check_mode()
    journal.complete(True)
    return True

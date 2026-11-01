"""Offline Q38 coordinator adapter. Not a runnable server launcher.

The injected supervisor must own child reaping and atomically capture its identity
before execution, and must drain descendants on failed launch.  A future concrete
supervisor must prove that contract before this adapter can be scheduled.
"""
from __future__ import annotations
import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Protocol, Any


class RuntimeFailure(RuntimeError):
    pass


class SpawnFailure(RuntimeFailure):
    def __init__(self, message: str, cleanup_verified: bool):
        super().__init__(message)
        self.cleanup_verified = cleanup_verified


class Supervisor(Protocol):
    def spawn(self, arm: str, recipe: dict) -> Any: ...
    def verify(self, handle: Any, arm: str, recipe: dict) -> bool: ...
    def stop_and_drain(self, handle: Any) -> bool: ...


@dataclass
class Server:
    arm: str
    handle: Any
    verified: bool = False
    stopped: bool = False


class Runtime:
    """Routes requests only after identity proof; pre-request custody is required."""
    def __init__(self, supervisor: Supervisor, transport: Any, journal: Any, stop: Any):
        self.supervisor, self.transport, self.journal, self.stop_requested = supervisor, transport, journal, stop
        self.active: Server | None = None
        self.cleanup_unverified = False

    def stopping(self):
        return bool(self.stop_requested())

    def start(self, arm, recipe):
        if self.active is not None or self.stopping():
            raise RuntimeFailure('active server or STOP')
        try:
            handle = self.supervisor.spawn(arm, copy.deepcopy(recipe))
        except SpawnFailure as exc:
            if not exc.cleanup_verified:
                self.cleanup_unverified = True
            raise
        except BaseException as exc:
            # Unknown backend exceptions carry no proof of post-spawn cleanup.
            self.cleanup_unverified = True
            raise RuntimeFailure('spawn failed without cleanup receipt') from exc
        if handle is None:
            self.cleanup_unverified = True
            raise RuntimeFailure('spawn returned no captured identity')
        self.active = Server(arm, handle)
        return self.active

    def verify(self, server, arm, recipe):
        if server is not self.active or server.stopped or server.arm != arm:
            raise RuntimeFailure('server identity mismatch')
        if self.supervisor.verify(server.handle, arm, copy.deepcopy(recipe)) is not True:
            raise RuntimeFailure('server recipe or process identity unverified')
        server.verified = True

    def request(self, server, body, kind):
        if server is not self.active or server.stopped or not server.verified or self.stopping():
            raise RuntimeFailure('request without verified active server')
        if kind not in ('warm', 'measure'):
            raise RuntimeFailure('invalid request kind')
        payload = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
        # Journal must atomically refuse reuse and durably record exposure before send.
        receipt = self.journal.before_request(server.arm, kind, hashlib.sha256(payload).hexdigest())
        if receipt is not True:
            raise RuntimeFailure('exposure receipt missing')
        response = self.transport.send(server.handle, copy.deepcopy(body))
        if self.journal.after_response(server.arm, kind, response) is not True:
            raise RuntimeFailure('response custody unverified')
        return response

    def stop(self, server):
        if server is not self.active or server.stopped:
            return False
        try:
            ok = self.supervisor.stop_and_drain(server.handle) is True
        except BaseException:
            ok = False
        server.stopped = True
        self.active = None
        if not ok:
            self.cleanup_unverified = True
        return ok

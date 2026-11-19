"""Linux-native verifier building blocks for the Q38 isolated-arm owner.

Socket and mapping evidence are sampled while the captured child is alive;
descendant drain additionally needs an exclusively owned cgroup attestation.
These helpers do not create a cgroup or grant authority to run inference.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
from typing import Callable

from q38_t7_supervisor import _birth, _sha256


def _mapped_files(pid: int) -> dict[str, tuple[int, int, int]]:
    paths = {}
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) < 6 or not parts[5].startswith('/'):
            continue
        path = parts[5]
        if path.endswith(' (deleted)'):
            raise ValueError('deleted executable mapping')
        major, minor = (int(value, 16) for value in parts[3].split(':'))
        identity = (major, minor, int(parts[4]))
        path = os.path.realpath(path)
        if path in paths and paths[path] != identity:
            raise ValueError('ambiguous mapping identity')
        paths[path] = identity
    return paths


def _mapped_paths(pid: int) -> set[str]:
    return set(_mapped_files(pid))


def _file_identity(path: str) -> tuple[int, int, int]:
    stat = os.stat(path)
    return (os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino)


def _owned_listeners(pid: int, host: str, port: int) -> set[str]:
    owned = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith('socket:[') and target.endswith(']'):
            owned.add(target[8:-1])
    matches = set()
    lines = Path(f'/proc/{pid}/net/tcp').read_text().splitlines()[1:]
    for line in lines:
        fields = line.split()
        if len(fields) < 10 or fields[3] != '0A':
            continue
        address, hex_port = fields[1].split(':')
        if (socket.inet_ntoa(bytes.fromhex(address)[::-1]) == host
                and int(hex_port, 16) == port and fields[9] in owned):
            matches.add(fields[9])
    return matches


class NativeIdentityVerifier:
    """Verify exact child, binary, socket and a pinned complete ggml map.

    ``membership_verifier`` must separately prove the live child was placed in
    an exclusively owned cgroup before it could spawn descendants. A check of
    current membership alone is not that proof. The map must include every
    expected library; any additional ggml library fails closed.
    """

    def __init__(self, host: str, port: int, libraries: dict[str, str],
                 membership_verifier: Callable, mode_verifier: Callable,
                 *, require_ggml: bool = True):
        if host != '127.0.0.1' or type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('explicit loopback IPv4 listener required')
        if (not isinstance(libraries, dict) or not libraries or not callable(membership_verifier)
                or not callable(mode_verifier)):
            raise ValueError('pinned libraries, membership and mode verifiers required')
        self.host, self.port = host, port
        self.libraries = {os.path.realpath(path): digest for path, digest in libraries.items()}
        self.membership_verifier, self.require_ggml = membership_verifier, require_ggml
        self.mode_verifier = mode_verifier

    def __call__(self, handle, arm: str, recipe: dict) -> bool:
        try:
            pid = handle.process.pid
            if handle.closed or handle.process.poll() is not None or _birth(pid) != handle.birth:
                return False
            argv = Path(f'/proc/{pid}/cmdline').read_bytes().rstrip(b'\0').split(b'\0')
            if argv != [os.fsencode(arg) for arg in handle.argv]:
                return False
            exe = os.path.realpath(f'/proc/{pid}/exe')
            if (exe != os.path.realpath(recipe['binary'])
                    or _sha256(f'/proc/{pid}/exe') != recipe['shape']['binary_sha256']):
                return False
            mapped = _mapped_files(pid)
            paths = set(mapped)
            if not set(self.libraries).issubset(paths):
                return False
            for path, digest in self.libraries.items():
                # Bind the path being hashed to the actual mapping's device and
                # inode on both sides of the read. A replaced pathname alone
                # must not attest a different library already mapped by the child.
                if (_file_identity(path) != mapped[path] or _sha256(path) != digest
                        or _file_identity(path) != mapped[path]):
                    return False
            ggml = {path for path in paths if Path(path).name.startswith('libggml')}
            if (self.require_ggml and not ggml) or not ggml.issubset(self.libraries):
                return False
            if len(_owned_listeners(pid, self.host, self.port)) != 1:
                return False
            if self.membership_verifier(handle) is not True:
                return False
            if self.mode_verifier(handle, arm, recipe) is not True:
                return False
            return handle.process.poll() is None and _birth(pid) == handle.birth
        except Exception:
            return False


class ExclusiveCgroupDrainVerifier:
    """Check an attested exclusive cgroup has no processes or descendants.

    ``ownership_verifier`` must validate exclusive creation and continuous
    membership/ownership; populated=0 in a reused or shared cgroup proves
    nothing. Paths are rooted and symlink escapes fail closed.
    """

    def __init__(self, relative_path: str, ownership_verifier: Callable,
                 *, root: str = '/sys/fs/cgroup'):
        if not relative_path or not callable(ownership_verifier):
            raise ValueError('exclusive cgroup and ownership verifier required')
        self.root = Path(root).resolve()
        self.path = (self.root / relative_path.lstrip('/')).resolve()
        if self.path == self.root or not self.path.is_relative_to(self.root):
            raise ValueError('dedicated cgroup beneath root required')
        self.ownership_verifier = ownership_verifier

    def __call__(self, handle) -> bool:
        try:
            if handle.process.poll() is None or self.ownership_verifier(handle, self.path) is not True:
                return False
            def empty():
                events = dict(line.split() for line in (self.path / 'cgroup.events').read_text().splitlines())
                procs = (self.path / 'cgroup.procs').read_text().strip()
                return events.get('populated') == '0' and not procs
            return empty() and self.ownership_verifier(handle, self.path) is True and empty()
        except Exception:
            return False

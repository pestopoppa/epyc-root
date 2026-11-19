"""Persistent, fail-closed no-redraw custody for one paired VKQ3 attempt.

The root is provisioned before publication outside row scratch. This ledger
cannot attest that a prompt was not exposed before the ledger existed: that
requires a separate exposure audit. Reservations are never removed or resumed.
"""
import hashlib
import json
import os
import re
import stat

_HASH = re.compile(r'^[0-9a-f]{64}$')
_ROOT_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


class PairedExposure:
    """One process owns one irrecoverable reservation, containing two arms."""
    def __init__(self, root, prompt_sha256, plan_sha256, arms):
        if not _HASH.fullmatch(prompt_sha256) or not _HASH.fullmatch(plan_sha256):
            raise ValueError('invalid prompt or plan digest')
        if tuple(arms) != ('hybrid', 'legacy'):
            raise ValueError('expected the predeclared paired arms')
        self._arms = tuple(arms)
        self._next = 0
        self._fd = None
        rootfd = os.open(root, _ROOT_FLAGS)
        try:
            st = os.fstat(rootfd)
            if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o077:
                raise ValueError('exposure ledger root must be private and owned')
            # Directory creation is the irreversible reservation; even an I/O
            # failure afterward burns the prompt rather than enabling redraw.
            os.mkdir(prompt_sha256, 0o700, dir_fd=rootfd)
            os.fsync(rootfd)
            self._fd = os.open(prompt_sha256, _ROOT_FLAGS, dir_fd=rootfd)
            self._write('attempt.json', {'schema': 'vkq3.paired-exposure.v1',
                'prompt_sha256': prompt_sha256, 'plan_sha256': plan_sha256,
                'arms': list(self._arms)})
        except BaseException:
            self.close()
            raise
        finally:
            os.close(rootfd)

    def _write(self, name, record):
        fd = os.open(name, _FILE_FLAGS, 0o600, dir_fd=self._fd)
        try:
            data = (json.dumps(record, sort_keys=True) + '\n').encode()
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if not written:
                    raise OSError('short ledger write')
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self._fd)

    def reserve_arm(self, arm):
        if self._fd is None or self._next >= len(self._arms) or arm != self._arms[self._next]:
            raise ValueError('arm is not the next predeclared arm')
        # Persist before making the HTTP request. A crash is an exposure, even
        # if the request's actual arrival is unknown.
        self._write(arm + '.json', {'arm': arm})
        self._next += 1

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

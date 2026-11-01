#!/usr/bin/env python3
"""Prospective native build event journal; no processes or build execution."""
import json
import os
import stat
from pathlib import Path


class BuildJournal:
    """Exclusive, ordered JSONL receipt writer. The caller owns process custody."""

    def __init__(self, parent, filename, mode, command_count):
        if mode not in ('qualification', 'target') or type(command_count) is not int or command_count < 1:
            raise ValueError('explicit mode and positive command count required')
        if not isinstance(filename, str) or filename in ('', '.', '..') or '/' in filename:
            raise ValueError('filename must be a single path component')
        self.parent_fd = os.open(Path(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        self.fd = None
        self.poisoned = False
        try:
            st = os.fstat(self.parent_fd)
            if st.st_uid != os.geteuid() or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise PermissionError('journal directory must be private and owned')
            self.fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.parent_fd)
            os.fsync(self.parent_fd)
            self.mode, self.count, self.next_index = mode, command_count, 0
            self.active = False
            self.terminal = False
            self._write({'event': 'begin', 'mode': mode, 'command_count': command_count})
        except BaseException:
            if self.fd is not None:
                os.close(self.fd)
            os.close(self.parent_fd)
            raise

    def _write(self, event):
        if self.poisoned:
            raise OSError('journal is poisoned by an earlier write failure')
        try:
            payload = (json.dumps(event, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
            view = memoryview(payload)
            while view:
                written = os.write(self.fd, view)
                if written <= 0:
                    raise OSError('short journal write')
                view = view[written:]
            os.fsync(self.fd)
        except BaseException:
            self.poisoned = True
            raise

    def start(self, index, command_sha256):
        if self.terminal or self.active or index != self.next_index or index >= self.count:
            raise ValueError('command ordering violation')
        if not isinstance(command_sha256, str) or len(command_sha256) != 64 or any(c not in '0123456789abcdef' for c in command_sha256):
            raise ValueError('missing command digest')
        self._write({'event': 'command-start', 'index': index, 'command_sha256': command_sha256})
        self.active = True

    def end(self, index, returncode, cleanup_verified):
        if self.terminal or not self.active or index != self.next_index or type(returncode) is not int or type(cleanup_verified) is not bool:
            raise ValueError('invalid command end')
        self._write({'event': 'command-end', 'index': index, 'returncode': returncode, 'cleanup_verified': cleanup_verified})
        self.active = False
        if returncode != 0 or not cleanup_verified:
            self._write({'event': 'partial', 'reason': 'command-or-cleanup-failed'})
            self.terminal = True
        else:
            self.next_index += 1

    def complete(self, evidence_verified):
        if self.terminal or self.active or self.next_index != self.count or evidence_verified is not True:
            raise ValueError('completion requires every command and evidence')
        self._write({'event': 'complete', 'mode': self.mode})
        self.terminal = True

    def close(self):
        os.close(self.fd)
        os.close(self.parent_fd)

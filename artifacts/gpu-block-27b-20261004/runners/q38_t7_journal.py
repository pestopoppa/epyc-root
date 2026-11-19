"""Durable Q38 request-exposure ledger; caller must preserve its canonical DB.

Exposure is inserted before dispatch. An interrupted or completed exposure
cannot be redrawn by reopening this database under another run ID. This does
not detect a caller substituting a different database or a different model pin;
rowflow/source custody must enforce the one canonical ledger.
"""

import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
import os
import stat


class ExposureError(RuntimeError):
    pass


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


class DurableJournal:
    def __init__(self, path, *, cohort_id, model_sha256, run_id, expected_binding=None):
        if not _sha(cohort_id) or not _sha(model_sha256):
            raise ValueError('cohort and model SHA-256 are required')
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError('run identity is required')
        self.path = Path(path)
        self.cohort_id, self.model_sha256, self.run_id = cohort_id, model_sha256, run_id
        if self.path.is_symlink() or not self.path.parent.is_dir():
            raise ValueError('journal path must have an existing directory and no symlink')
        flags = os.O_RDWR | os.O_NOFOLLOW | (0 if expected_binding is not None else os.O_CREAT)
        fd = os.open(self.path, flags, 0o600)
        try:
            opened = os.fstat(fd)
            mode = opened.st_mode
            if not stat.S_ISREG(mode) or mode & 0o077:
                raise ValueError('journal must be a private regular file')
            self._file_identity = (opened.st_dev, opened.st_ino)
        finally:
            os.close(fd)
        self._db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        self._assert_current()
        self._db.execute('PRAGMA synchronous=FULL')
        self._db.execute('PRAGMA journal_mode=DELETE')
        self._db.execute('''CREATE TABLE IF NOT EXISTS exposure (
            cohort TEXT NOT NULL, model TEXT NOT NULL, arm TEXT NOT NULL,
            pair_key TEXT NOT NULL, kind TEXT NOT NULL, body_sha TEXT NOT NULL,
            run_id TEXT NOT NULL, status TEXT NOT NULL, response_sha TEXT, response_json TEXT,
            PRIMARY KEY (cohort, arm, pair_key, kind))''')
        self._db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS no_measurement_redraw
            ON exposure (model, arm, body_sha) WHERE kind = 'measure' ''')
        self._db.execute('CREATE TABLE IF NOT EXISTS ledger_meta (id INTEGER PRIMARY KEY CHECK(id=1), ledger_id TEXT NOT NULL)')
        self._db.execute('INSERT OR IGNORE INTO ledger_meta (id, ledger_id) VALUES (1, ?)', (secrets.token_hex(32),))
        self.ledger_id = self._db.execute('SELECT ledger_id FROM ledger_meta WHERE id=1').fetchone()[0]
        if expected_binding is not None and self.binding() != expected_binding:
            self._db.close()
            raise ValueError('journal seal does not match canonical file')
        # Persist creation of the database directory entry, not just SQLite rows.
        fd = os.open(str(self.path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def before_request(self, arm, pair_key, kind, body_sha):
        self._assert_current()
        if (arm not in ('drafted', 'nodraft') or kind not in ('warm', 'measure')
                or not isinstance(pair_key, str) or not pair_key or not _sha(body_sha)):
            raise ExposureError('invalid request identity')
        try:
            self._db.execute('BEGIN IMMEDIATE')
            self._db.execute('INSERT INTO exposure '
                             '(cohort, model, arm, pair_key, kind, body_sha, run_id, status) '
                             'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                             (self.cohort_id, self.model_sha256, arm, pair_key, kind,
                              body_sha, self.run_id, 'EXPOSED'))
            self._db.execute('COMMIT')
            self._assert_current()
        except sqlite3.IntegrityError as exc:
            self._db.execute('ROLLBACK')
            raise ExposureError('request was already exposed; redraw refused') from exc
        except BaseException:
            if self._db.in_transaction:
                self._db.execute('ROLLBACK')
            raise
        return True

    def after_response(self, arm, pair_key, kind, response):
        self._assert_current()
        raw = json.dumps(response, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        try:
            self._db.execute('BEGIN IMMEDIATE')
            cur = self._db.execute('UPDATE exposure SET status=?, response_sha=?, response_json=? '
                                   'WHERE cohort=? AND arm=? AND pair_key=? AND kind=? '
                                   'AND run_id=? AND status=?',
                                   ('RECORDED', digest, raw, self.cohort_id, arm,
                                    pair_key, kind, self.run_id, 'EXPOSED'))
            if cur.rowcount != 1:
                raise ExposureError('response has no matching open exposure')
            self._db.execute('COMMIT')
            self._assert_current()
        except BaseException:
            if self._db.in_transaction:
                self._db.execute('ROLLBACK')
            raise
        return True

    def close(self):
        self._db.close()

    def _assert_current(self):
        current = os.stat(self.path, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != self._file_identity:
            raise ExposureError('canonical journal path was replaced')

    def binding(self):
        self._assert_current()
        return {'path': str(self.path.absolute()), 'device': self._file_identity[0],
                'inode': self._file_identity[1], 'ledger_id': self.ledger_id}

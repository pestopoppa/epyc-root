"""Prospective, hash-chained online shadow event stream (coverage, not a verdict).

The caller must execute the actual searches and call this sink at their event
boundary. Source and arm identities are producer declarations, not evidence of
what was loaded or displayed. A stream without a finish record is incomplete.
There is deliberately no import/replay interface and no retrospective writer.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

from scripts.vidya.producers.repl_shadow import ShadowAttribution, Span

_HEX = re.compile(r'^[0-9a-f]{64}$')
_NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$')
SCHEMA = 'epyc.repl_shadow_events.v1'


def _now():
    return datetime.now(timezone.utc)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class ShadowSink:
    """Exclusive stream containing only searches and first observed opens.

    One sink belongs to a single session. Create it before the first search;
    callers cannot supply timestamps, precomputed results, or historical files.
    No open before close or supersession is *unknown*, never a negative follow.
    """

    def __init__(self, directory, *, run_id, session, source_sha256, arm_identities):
        if not isinstance(run_id, str) or not _NAME.fullmatch(run_id):
            raise ValueError('invalid run id')
        if not isinstance(session, str) or not re.fullmatch(r'[0-9a-f]{16}', session):
            raise ValueError('invalid session')
        if not isinstance(source_sha256, str) or not _HEX.fullmatch(source_sha256):
            raise ValueError('invalid source identity')
        if (not isinstance(arm_identities, dict) or not arm_identities or
                any(not isinstance(k, str) or not _NAME.fullmatch(k) or
                    not isinstance(v, str) or not _HEX.fullmatch(v)
                    for k, v in arm_identities.items())):
            raise ValueError('invalid arm identities')
        root = Path(directory)
        if not root.is_absolute() or not root.is_dir():
            raise ValueError('capture directory must already exist and be absolute')
        self.path = root / (run_id + '.shadow.jsonl')
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self._stream = os.fdopen(fd, 'w', encoding='utf-8')
        self._prev = '0' * 64
        self._sequence = 0
        self._failed = False
        self._searches = 0
        self._opens = 0
        self._pending = None
        self._closed = False
        self.session = session
        self.arm_identities = dict(arm_identities)
        self._write({'kind': 'start', 'schema': SCHEMA, 'run_id': run_id,
                     'session': session, 'source_sha256': source_sha256,
                     'arm_identities': self.arm_identities, 'identity_scope': 'producer-declared',
                     'started_at': _now().isoformat()})

    def _write(self, payload):
        if self._failed:
            raise ValueError('capture is incomplete after write failure')
        body = {'sequence': self._sequence, 'previous_sha256': self._prev, **payload}
        digest = hashlib.sha256(_canonical(body).encode('utf-8')).hexdigest()
        try:
            self._stream.write(_canonical({**body, 'sha256': digest}) + '\n')
            self._stream.flush()
            os.fsync(self._stream.fileno())
        except Exception:
            self._failed = True
            raise
        self._prev = digest
        self._sequence += 1

    def _emit_pending(self, reason, opened_span=None):
        if self._pending is None:
            return
        result = self._pending.result()
        self._write({'kind': 'result', 'reason': reason, 'result': result,
                     'opened_span': asdict(opened_span) if opened_span is not None else None,
                     'interpretation': {arm: ('shown' if arm == result['shown_arm'] else
                                               'counterfactual_span_match')
                                        for arm in result['arms']}})
        self._pending = None

    def search(self, *, query_digest, rankings, shown_arm):
        if self._closed:
            raise ValueError('closed capture')
        if not isinstance(rankings, dict) or set(rankings) != set(self.arm_identities):
            raise ValueError('rankings must include exactly the declared arms')
        candidate = ShadowAttribution(session=self.session, query_digest=query_digest,
                                      searched_at=_now(), rankings=rankings, shown_arm=shown_arm)
        self._emit_pending('superseded')
        self._pending = candidate
        self._searches += 1
        self._write({'kind': 'search', 'result': candidate.result()})

    def opened(self, *, span):
        if self._closed:
            raise ValueError('closed capture')
        if not isinstance(span, Span):
            raise ValueError('invalid open span')
        if self._pending is None:
            return False
        self._pending.observe_open(session=self.session, opened_at=_now(), span=span)
        self._opens += 1
        self._emit_pending('observed_open', span)
        return True

    def close(self):
        if self._closed:
            raise ValueError('closed capture')
        self._emit_pending('capture_closed')
        self._write({'kind': 'finish', 'ended_at': _now().isoformat(),
                     'searches': self._searches, 'observed_opens': self._opens})
        self._stream.close()
        self._closed = True
        return self.path

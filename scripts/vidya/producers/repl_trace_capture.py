"""Prospective v2 REPL spill trace capture; coverage only, not retrieval quality.

Call ``record`` at the native event boundary. Never import old JSONL: it cannot
prove that capture was enabled at the time of the original run. This module is
not wired into the application until the caller and a planning canary land.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.vidya.adapters import _native_sidecar as carrier

SCHEMA = 'epyc.vidya.repl_trace_coverage.v1'
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_SESSION = re.compile(r'^[0-9a-f]{16}$')
_SECTION = re.compile(r'^(?:[A-Za-z][A-Za-z0-9_.-]{0,47}|h:[0-9a-f]{12})$')
_PII = re.compile(r'(@[A-Za-z0-9-]+\.[A-Za-z]{2,}|\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b|\b(?:sk|ghp|hf|xox[a-z])[-_][A-Za-z0-9]{8,}|\b\d{13,19}\b|\b\d{1,3}(?:\.\d{1,3}){3}\b|-----BEGIN)')
_RUN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$')
_BASE = {'v', 'kind', 'provenance', 'session', 'ts', 'section', 'content_digest', 'content_chars'}


def _time():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def _nonnegative(value):
    return type(value) is int and 0 <= value < 10**12


def validate_event(e):
    if not isinstance(e, dict) or e.get('kind') not in ('search', 'open'):
        raise ValueError('invalid event kind')
    fields = {'query_digest', 'k', 'mode', 'hits'} if e['kind'] == 'search' else {'start', 'end'}
    if set(e) != _BASE | fields or e['v'] != 2 or e['provenance'] != 'trace':
        raise ValueError('event schema')
    if not isinstance(e['session'], str) or not _SESSION.fullmatch(e['session']):
        raise ValueError('session identity')
    if not isinstance(e['content_digest'], str) or not _HEX64.fullmatch(e['content_digest']):
        raise ValueError('content identity')
    if not isinstance(e['section'], str) or not _SECTION.fullmatch(e['section']):
        raise ValueError('section identity')
    if any(_PII.search(value) for value in e.values() if isinstance(value, str)):
        raise ValueError('PII-like string')
    if not carrier.utc_timestamp(e['ts']) or not _nonnegative(e['content_chars']):
        raise ValueError('timestamp or content size')
    n = e['content_chars']
    if e['kind'] == 'open':
        if not (_nonnegative(e['start']) and _nonnegative(e['end']) and e['start'] <= e['end'] <= n):
            raise ValueError('open span')
    else:
        if not isinstance(e['query_digest'], str) or not _HEX64.fullmatch(e['query_digest']):
            raise ValueError('query identity')
        if not _nonnegative(e['k']) or e['mode'] != 'grep' or not isinstance(e['hits'], list) or len(e['hits']) > max(64, e['k']):
            raise ValueError('search shape')
        for hit in e['hits']:
            if not (isinstance(hit, list) and len(hit) == 3 and hit[0] == e['section'] and
                    _nonnegative(hit[1]) and _nonnegative(hit[2]) and hit[1] <= hit[2] <= n):
                raise ValueError('search span')


class TraceCapture:
    """An exclusive, producer-bound event stream; no pre-existing input accepted."""
    def __init__(self, directory, *, run_id, source_sha256):
        if not isinstance(run_id, str) or not _RUN.fullmatch(run_id):
            raise ValueError('run id')
        if not isinstance(source_sha256, str) or not _HEX64.fullmatch(source_sha256):
            raise ValueError('source sha256')
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.source_sha256 = source_sha256
        self.started = _time()
        self.path = self.directory / (run_id + '.trace.jsonl')
        self.stream = open(self.path, 'x', encoding='utf-8')
        self.closed = False
        self.count = 0
        self.failures = 0
        self.last_event = None
        self._write({'schema': SCHEMA, 'kind': 'start', 'run_id': run_id,
                     'source_sha256': source_sha256, 'started_at': self.started,
                     'capture_id': uuid.uuid4().hex})

    def _write(self, obj):
        self.stream.write(carrier.canonical_json(obj) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def record(self, event):
        if self.closed:
            raise ValueError('closed capture')
        try:
            validate_event(event)
            stamp = datetime.fromisoformat(event['ts'].replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            if (not 0 <= age <= 5 or
                stamp < datetime.fromisoformat(self.started) - timedelta(seconds=1) or
                (self.last_event is not None and stamp < self.last_event)):
                raise ValueError('event time outside capture or out of order')
        except (ValueError, TypeError, KeyError):
            self.failures += 1
            raise
        self._write({'kind': 'event', 'event': event})
        self.count += 1
        self.last_event = stamp

    def finalize(self):
        if self.closed:
            raise ValueError('closed capture')
        ended = _time()
        end_stamp = datetime.fromisoformat(ended)
        if (end_stamp < datetime.fromisoformat(self.started) or
                (self.last_event is not None and end_stamp < self.last_event)):
            raise ValueError('capture end precedes start or last event')
        self._write({'kind': 'finish', 'events': self.count, 'rejected': self.failures, 'ended_at': ended})
        self.stream.close()
        self.closed = True
        row = {'schema': SCHEMA, 'run_id': self.run_id, 'producer': 'repl-trace-coverage',
               'measurement_id': 'trace_' + carrier.content_hash({'run_id': self.run_id, 'started_at': self.started})[:24],
               'metric': 'recorded_trace_events', 'value': self.count, 'unit': 'events',
               'metric_direction': 'higher_better', 'category': 'CANDIDATE',
               'claim': 'Recorded v2 trace events; capture coverage only, not retrieval quality or follow rate',
               'protocol_id': '', 'reps': 1, 'reps_basis': 'capture-session',
               'results_path': str(self.path), 'results_sha256': carrier.file_sha256(self.path),
               'date': ended, 'emitted_at': ended,
               'extra': {'source_sha256': self.source_sha256, 'started_at': self.started,
                         'rejected': self.failures, 'direction_scope': 'capture coverage only',
                         'source_identity_scope': 'producer-declared' }}
        carrier.seal(row)
        sidecar = self.directory / (self.run_id + '.belief_measurements.jsonl')
        if sidecar.exists():
            raise FileExistsError(sidecar)
        carrier.write_rows_atomic(sidecar, [row])
        return sidecar


def validate(row):
    errors = carrier.common_problems(row, schema=SCHEMA, optional_text=('protocol_id',)) + carrier.self_hash_problems(row)
    try:
        if errors or not carrier.results_present(row):
            return errors + ['trace attestation missing or changed']
        lines = [json.loads(line) for line in Path(row['results_path']).read_text().splitlines()]
        start, finish = lines[0], lines[-1]
        if set(start) != {'schema', 'kind', 'run_id', 'source_sha256', 'started_at', 'capture_id'} or start['schema'] != SCHEMA or start['kind'] != 'start':
            raise ValueError('start')
        if set(finish) != {'kind', 'events', 'rejected', 'ended_at'} or finish['kind'] != 'finish':
            raise ValueError('finish')
        previous = datetime.fromisoformat(start['started_at'].replace('Z', '+00:00')) - timedelta(seconds=1)
        finished = datetime.fromisoformat(finish['ended_at'].replace('Z', '+00:00'))
        if finished < datetime.fromisoformat(start['started_at'].replace('Z', '+00:00')):
            raise ValueError('finish precedes start')
        for item in lines[1:-1]:
            if set(item) != {'kind', 'event'} or item['kind'] != 'event':
                raise ValueError('event wrapper')
            validate_event(item['event'])
            stamp = datetime.fromisoformat(item['event']['ts'].replace('Z', '+00:00'))
            if not previous <= stamp <= finished:
                raise ValueError('event time outside capture or out of order')
            previous = stamp
        extra = row['extra']
        expected_keys = {'schema', 'run_id', 'producer', 'measurement_id', 'metric', 'value', 'unit',
                         'metric_direction', 'category', 'claim', 'protocol_id', 'reps', 'reps_basis',
                         'results_path', 'results_sha256', 'date', 'emitted_at', 'extra', 'row_sha256'}
        if (set(row) != expected_keys or row['producer'] != 'repl-trace-coverage' or
            row['category'] != 'CANDIDATE' or row['reps'] != 1 or row['reps_basis'] != 'capture-session' or
            row['claim'] != 'Recorded v2 trace events; capture coverage only, not retrieval quality or follow rate' or
            row['date'] != finish['ended_at'] or row['emitted_at'] != finish['ended_at'] or
            not carrier.utc_timestamp(start['started_at']) or not carrier.utc_timestamp(finish['ended_at']) or
            not _RUN.fullmatch(start['run_id']) or not _HEX64.fullmatch(start['source_sha256']) or
            not re.fullmatch(r'[0-9a-f]{32}', start['capture_id']) or
            set(extra) != {'source_sha256', 'started_at', 'rejected', 'direction_scope', 'source_identity_scope'} or
            start['run_id'] != row['run_id'] or start['source_sha256'] != extra['source_sha256'] or
            start['started_at'] != extra['started_at'] or finish['events'] != len(lines)-2 or
            finish['events'] != row['value'] or finish['rejected'] != extra['rejected'] or
            not _nonnegative(finish['rejected']) or row['protocol_id'] != '' or
            row['metric'] != 'recorded_trace_events' or row['unit'] != 'events' or
            row['metric_direction'] != 'higher_better' or extra['direction_scope'] != 'capture coverage only' or
            extra['source_identity_scope'] != 'producer-declared' or
            row['measurement_id'] != 'trace_' + carrier.content_hash({'run_id': row['run_id'], 'started_at': start['started_at']})[:24]):
            raise ValueError('row does not match capture')
        return []
    except (OSError, KeyError, ValueError, TypeError, IndexError, json.JSONDecodeError):
        return errors + ['invalid trace capture']


def project(row):
    problems = validate(row)
    if problems:
        raise ValueError('; '.join(problems))
    return carrier.to_claim_tuple(row, source_kind='repl-trace-coverage', locator=row['results_path'])

"""Validate a completed shadow stream, without claiming its producer was genuine.

The hash chain detects un-rehashed changes, not deliberate forgery. Source and arm
identities remain producer declarations even when they match expected digests.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from scripts.vidya.producers.repl_shadow import ShadowAttribution, Span
from scripts.vidya.producers.repl_shadow_sink import SCHEMA

_HEX = re.compile(r'^[0-9a-f]{64}$')
_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]{0,63}$')
_BASE = {'sequence', 'previous_sha256', 'sha256', 'kind'}


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate JSON key')
        out[key] = value
    return out


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError('invalid timestamp')
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('timestamp must be timezone-aware')
    return dt


def _span(value):
    if not isinstance(value, dict) or set(value) != {'section_digest', 'content_digest', 'start', 'end', 'content_chars'}:
        raise ValueError('invalid span')
    return Span(**value)


def _identity(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def validate_shadow_stream(path, *, expected_source_sha256=None):
    """Return validated records or raise ValueError. No authenticity is inferred."""
    try:
        raw = Path(path).read_bytes()
        if not raw.endswith(b'\n'):
            raise ValueError('incomplete final line')
        rows = [json.loads(line, object_pairs_hook=_object) for line in raw.splitlines()]
        if len(rows) < 2 or not all(isinstance(row, dict) for row in rows):
            raise ValueError('missing start or finish')
        prev = '0' * 64
        for n, row in enumerate(rows):
            if (type(row.get('sequence')) is not int or row['sequence'] != n or
                    row.get('previous_sha256') != prev or not _identity(row.get('sha256'), _HEX)):
                raise ValueError('invalid chain')
            body = {k: v for k, v in row.items() if k != 'sha256'}
            digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            if digest != row['sha256']:
                raise ValueError('invalid chain digest')
            prev = digest
        start = rows[0]
        if (set(start) != _BASE | {'schema', 'run_id', 'session', 'source_sha256', 'arm_identities', 'identity_scope', 'started_at'} or
            start['kind'] != 'start' or start['schema'] != SCHEMA or start['identity_scope'] != 'producer-declared' or
            not _identity(start['run_id'], _NAME) or not _identity(start['session'], re.compile(r'^[0-9a-f]{16}$')) or
            not _identity(start['source_sha256'], _HEX) or
            (expected_source_sha256 is not None and start['source_sha256'] != expected_source_sha256)):
            raise ValueError('invalid declared source')
        arms = start['arm_identities']
        if not isinstance(arms, dict) or not arms or any(not _identity(k, _NAME) or not _identity(v, _HEX) for k, v in arms.items()):
            raise ValueError('invalid arm identities')
        last = _stamp(start['started_at'])
        pending = None
        next_kind = None
        searches = opens = 0
        for row in rows[1:]:
            kind = row.get('kind')
            if next_kind is not None and kind != next_kind:
                raise ValueError('invalid result successor')
            next_kind = None
            if kind == 'search':
                if set(row) != _BASE | {'result'} or pending is not None:
                    raise ValueError('invalid search state')
                result = row['result']
                if not isinstance(result, dict) or set(result) != {'session', 'query_digest', 'searched_at', 'shown_arm', 'opened_at', 'arms'} or result['session'] != start['session'] or result['opened_at'] is not None:
                    raise ValueError('invalid search result')
                stamp = _stamp(result['searched_at'])
                if stamp < last or not isinstance(result['arms'], dict) or set(result['arms']) != set(arms):
                    raise ValueError('invalid search timestamp or arms')
                ranking = {}
                for arm, items in result['arms'].items():
                    if not isinstance(items, list):
                        raise ValueError('invalid ranking')
                    ranking[arm] = []
                    for rank, item in enumerate(items, 1):
                        if not isinstance(item, dict) or set(item) != {'rank', 'span', 'next_open_overlap'} or type(item['rank']) is not int or item['rank'] != rank or item['next_open_overlap'] is not None:
                            raise ValueError('invalid ranked span')
                        ranking[arm].append(_span(item['span']))
                pending = ShadowAttribution(session=start['session'], query_digest=result['query_digest'], searched_at=stamp, rankings=ranking, shown_arm=result['shown_arm'])
                if pending.result() != result:
                    raise ValueError('noncanonical search')
                searches += 1
                last = stamp
            elif kind == 'result':
                if set(row) != _BASE | {'reason', 'result', 'opened_span', 'interpretation'} or pending is None:
                    raise ValueError('invalid result state')
                reason = row['reason']
                if reason == 'observed_open':
                    span = _span(row['opened_span'])
                    stamp = _stamp(row['result']['opened_at'])
                    if stamp <= last:
                        raise ValueError('invalid open time')
                    pending.observe_open(session=start['session'], opened_at=stamp, span=span)
                    last = stamp
                    opens += 1
                elif reason in ('superseded', 'capture_closed'):
                    if row['opened_span'] is not None:
                        raise ValueError('unknown outcome carries an open')
                    next_kind = 'search' if reason == 'superseded' else 'finish'
                else:
                    raise ValueError('invalid reason')
                expected = pending.result()
                interpretation = {arm: ('shown' if arm == expected['shown_arm'] else 'counterfactual_span_match') for arm in arms}
                if row['result'] != expected or row['interpretation'] != interpretation:
                    raise ValueError('result cannot be rederived')
                pending = None
            elif kind == 'finish':
                if row is not rows[-1] or set(row) != _BASE | {'ended_at', 'searches', 'observed_opens'} or pending is not None:
                    raise ValueError('invalid finish state')
                if type(row['searches']) is not int or type(row['observed_opens']) is not int or row['searches'] != searches or row['observed_opens'] != opens or _stamp(row['ended_at']) < last:
                    raise ValueError('invalid finish counts or time')
            else:
                raise ValueError('invalid record kind')
        if rows[-1].get('kind') != 'finish':
            raise ValueError('missing finish')
        return rows
    except (OSError, UnicodeError, KeyError, TypeError, OverflowError, json.JSONDecodeError) as exc:
        raise ValueError('invalid shadow stream') from exc

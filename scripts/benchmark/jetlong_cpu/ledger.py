#!/usr/bin/env python3
"""Offline durable ledger for a future JetLong paired runner; not a launcher.

One event file per cell with exclusive creation. A started-only cell is unknown:
recovery never retries it implicitly. Timed-out cells count as failed attempts.
"""
import hashlib
import json
import os
from pathlib import Path

ARMS = ('J', 'Y')

def read_plan(path):
    raw = Path(path).read_bytes()
    plan = json.loads(raw)
    items = plan['items']
    if not items or len({i['id'] for i in items}) != len(items):
        raise ValueError('empty or duplicate item IDs')
    for item in items:
        if not isinstance(item['id'], str) or not item['id'] or '/' in item['id'] or item['id'] in ('.', '..'):
            raise ValueError('unsafe item ID')
        if not isinstance(item['expected'], str) or not item['expected'].strip():
            raise ValueError('empty expected answer')
        if item['length'] not in (300000, 524288):
            raise ValueError('unexpected target length')
    return plan, hashlib.sha256(raw).hexdigest()

def _atomic_new(path, obj):
    # Reserve names exclusively: no second writer may overwrite an existing event.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(obj, f, sort_keys=True, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    except BaseException:
        # Preserve the possibly partial event as an unknown; never delete evidence.
        raise

def initialize(directory, plan_path):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    plan, digest = read_plan(plan_path)
    pin = directory / 'plan.sha256'
    if not pin.exists():
        try: _atomic_new(pin, {'sha256': digest})
        except FileExistsError: pass
    if json.loads(pin.read_text()) != {'sha256': digest}:
        raise ValueError('plan identity changed')
    return plan, digest

def _cell(directory, item_id, arm, suffix):
    if arm not in ARMS or not item_id or '/' in item_id or item_id in ('.', '..'):
        raise ValueError('invalid cell')
    return Path(directory) / f'{item_id}.{arm}.{suffix}.json'

def start(directory, plan, plan_sha, item_id, arm):
    if item_id not in {i['id'] for i in plan['items']}:
        raise ValueError('item not in plan')
    _atomic_new(_cell(directory, item_id, arm, 'started'), {'id': item_id, 'arm': arm, 'plan_sha256': plan_sha})

def finish(directory, plan_sha, item_id, arm, status, response=None, timings=None):
    started = json.loads(_cell(directory, item_id, arm, 'started').read_text())
    if started != {'id': item_id, 'arm': arm, 'plan_sha256': plan_sha}:
        raise ValueError('start identity mismatch')
    if status not in ('ok', 'timeout') or (status == 'ok' and not isinstance(response, str)):
        raise ValueError('invalid terminal result')
    _atomic_new(_cell(directory, item_id, arm, 'finished'), {'id': item_id, 'arm': arm, 'plan_sha256': plan_sha, 'status': status, 'response': response, 'timings': timings})

def inventory(directory, plan, plan_sha):
    states = {'unstarted': [], 'unknown': [], 'finished': []}
    for item in plan['items']:
        for arm in ARMS:
            s = _cell(directory, item['id'], arm, 'started').exists()
            f = _cell(directory, item['id'], arm, 'finished').exists()
            if f and not s: raise ValueError('terminal event without start')
            if s:
                start_event = json.loads(_cell(directory, item['id'], arm, 'started').read_text())
                if start_event != {'id': item['id'], 'arm': arm, 'plan_sha256': plan_sha}:
                    raise ValueError('invalid started event')
            if f:
                event = json.loads(_cell(directory, item['id'], arm, 'finished').read_text())
                if (event.get('id'), event.get('arm'), event.get('plan_sha256')) != (item['id'], arm, plan_sha) or event.get('status') not in ('ok', 'timeout'):
                    raise ValueError('invalid finished event')
                if event['status'] == 'ok' and not isinstance(event.get('response'), str):
                    raise ValueError('missing response')
            states['finished' if f else 'unknown' if s else 'unstarted'].append((item['id'], arm))
    return states

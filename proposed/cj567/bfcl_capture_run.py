"""Fail-closed BFCL native multi-turn capture custody; no local grading rule.

Model/build digests must come from independently verified launcher manifests.
This module binds those assertions; it does not attest a running server's identity.
Never expose the journal, selection manifest or checker workspace to the model.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from bfcl_native import UPSTREAM

LOCK = Path(__file__).with_name('bfcl-catalog-lock.json')
CATALOGS = {'GorillaFileSystem': 'gorilla_file_system.json',
            'TwitterAPI': 'posting_api.json'}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def released_catalog(case, directory):
    """Read exact released schema bytes, preserving class/file order."""
    lock = json.loads(LOCK.read_bytes())
    functions, bindings, names = [], {}, set()
    for cls in case['involved_classes']:
        if cls not in CATALOGS:
            raise ValueError('unbound schema class: ' + cls)
        name = CATALOGS[cls]
        raw = (Path(directory) / name).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != lock['files']['multi_turn_func_doc/' + name]['sha256']:
            raise ValueError('released schema digest mismatch: ' + name)
        for schema in map(json.loads, raw.splitlines()):
            if schema['name'] in names:
                raise ValueError('colliding released schema name')
            names.add(schema['name'])
            functions.append(schema)
        bindings[name] = sha
    return functions, {'repository': lock['repository'], 'revision': lock['revision'],
                       'files': bindings, 'lock_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest()}


class Journal:
    """Exclusive, fsync-per-event journal; interrupted attempts cannot be redrawn."""

    def __init__(self, path):
        path = Path(path)
        self.file = path.open('xb', buffering=0)
        self.sequence = 0
        self.previous = None
        self.failed = False
        try:
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except BaseException:
            self.file.close()
            raise

    def append(self, event):
        if self.failed:
            raise RuntimeError('journal failed; cannot append')
        row = {'sequence': self.sequence, 'previous_sha256': self.previous,
               'recorded_at': datetime.now(timezone.utc).isoformat(),
               'event': copy.deepcopy(event)}
        raw = encoded(row)
        sha = hashlib.sha256(raw).hexdigest()
        try:
            data = encoded({**row, 'sha256': sha}) + b'\n'
            # FileIO.write may write fewer bytes than requested.
            while data:
                count = self.file.write(data)
                if not count:
                    raise OSError('short journal write')
                data = data[count:]
            os.fsync(self.file.fileno())
        except BaseException:
            self.failed = True
            raise
        self.previous = sha
        self.sequence += 1

    def close(self):
        self.file.close()


def capture_case(bridge, row, model, identity, catalog_directory, output, query,
                 should_stop=lambda: False):
    """Capture once with write-time custody, then call unmodified official replay.

    Identity is an assertion from the launcher's verified model/build manifests.
    No resume/retry is supported; an existing output always refuses the attempt.
    """
    identity = copy.deepcopy(identity)
    for key in ('model_sha256', 'server_binary_sha256', 'build_manifest_sha256',
                'runtime_manifest_sha256'):
        if not isinstance(identity.get(key), str) or not re.fullmatch('[0-9a-f]{64}', identity[key]):
            raise ValueError('missing content identity: ' + key)
    if identity.get('model') != model or not isinstance(model, str) or not model:
        raise ValueError('request model/identity mismatch')
    if row['case']['id'] != row['gold']['id']:
        raise ValueError('case/gold ID mismatch')
    category = row['category']
    lock = json.loads(LOCK.read_bytes())
    for field, prefix in (('case', ''), ('gold', 'possible_answer/')):
        source = prefix + 'BFCL_v3_' + category + '.json'
        if source not in lock['corpus']:
            raise ValueError('unbound corpus category')
    selected = lock['selection'].get(row['case']['id'], {})
    if any(digest(row[field]) != selected.get(field + '_sha256') for field in ('case', 'gold')):
        raise ValueError('case/gold content differs from pinned selection')
    functions, catalog_binding = released_catalog(row['case'], catalog_directory)
    # Freeze inputs before invoking caller-supplied transport.
    row = copy.deepcopy(row)
    journal = Journal(output)
    try:
        journal.append({'kind': 'identity', 'benchmark': 'bfcl_v3',
            'instrument': 'native-multi-turn', 'upstream_commit': UPSTREAM,
            'software_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                for name in ('bfcl_capture_run.py', 'bfcl_native.py', 'openai_tool_calls.py')},
            'identity': identity, 'case_id': row['case']['id'], 'category': category,
            'case_sha256': digest(row['case']), 'gold_sha256': digest(row['gold']),
            'catalog': catalog_binding, 'corpus': lock['corpus'],
            'protocol': {'temperature': 0, 'seed': 20261031, 'max_tokens': 4096},
            'limitations': ['official response/order checks disabled',
                           'official irrelevance helper nested-call blind spot'],
            'identity_scope': 'launcher assertions; server residency proof required externally'})
        result = bridge.capture_multi_turn(row['case'], category, model, functions,
                                          query, journal.append, should_stop)
        journal.append({'kind': 'capture_result', 'result': result})
        if result['status'] == 'captured':
            verdict = bridge.score_multi_turn(row['case'], category, row['gold'], result['turns'])
        else:
            verdict = {'status': result['status'], 'valid': None, 'error': result['error']}
        journal.append({'kind': 'verdict', 'verdict': verdict})
        return verdict
    except BaseException as error:
        # An exposure may already have happened; never retry or score missing data.
        if not journal.failed:
            journal.append({'kind': 'aborted', 'error_type': type(error).__name__,
                            'error': str(error), 'valid': None})
        raise
    finally:
        journal.close()

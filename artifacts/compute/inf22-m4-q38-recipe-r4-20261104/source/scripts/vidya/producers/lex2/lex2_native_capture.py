"""Prospective CS-8.LEX2 attempt capture; not a retrospective warrant.

The producer calls start_attempt before exposing audio and finish_attempt after its
child has been reaped.  A start without a finish is an exposed unknown: never retry.
This small module deliberately does not project or grade measurements.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

HEX = re.compile(r'^[0-9a-f]{64}$')


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _write_once(path, value):
    path = Path(path)
    value = dict(value)
    value['record_sha256'] = _hash(value)
    fd, temporary = tempfile.mkstemp(prefix='.lex2-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)
    return value


def _sha(value, name):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError(name + ' must be sha256')


def verify_engine_config(config, expected_binary, expected_model, expected_tokenizer=None):
    """Hash actual instrument files once before any request; callers still prove linkage."""
    for label, expected in (("binary", expected_binary), ("model", expected_model), ("tokenizer", expected_tokenizer), ("source", None), ("ggml", None)):
        if label == "tokenizer" and expected is None:
            continue
        path = Path(config[label + "_path"])
        if expected is not None and path.resolve() != Path(expected).resolve():
            raise ValueError(label + ' path differs from actual request')
        _sha(config.get(label + "_sha256"), label + '_sha256')
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1048576), b''): h.update(block)
        if h.hexdigest() != config[label + "_sha256"]:
            raise ValueError(label + ' digest mismatch')
    if not isinstance(config.get('ggml_version'), str) or not config['ggml_version'].strip():
        raise ValueError('ggml version required')


def start_attempt(path, capture):
    """Persist an immutable attempt before exposure. Missing inputs fail closed."""
    capture = dict(capture)
    for key in ('dev_manifest_sha256', 'test_manifest_sha256', 'overlap_exclusions_sha256',
                'clip_sha256', 'context_sha256',
                'model_sha256', 'source_sha256', 'binary_sha256', 'ggml_sha256',
                'grant_sha256', 'request_sha256'):
        _sha(capture.get(key), key)
    for key in ('dataset_revision', 'clip_id', 'context_id', 'ggml_version', 'grant_id'):
        if not isinstance(capture.get(key), str) or not capture[key].strip():
            raise ValueError(key + ' required')
    if capture.get('split') not in ('dev', 'heldout'):
        raise ValueError('unknown split')
    if capture.get('scope') not in ('global', 'local', 'none'):
        raise ValueError('unknown scope')
    a = capture.get('configured_alpha')
    if capture.get('engine') == 'whisper':
        if a is not None: raise ValueError('whisper has no configured alpha')
    elif isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or a < 0:
        raise ValueError('invalid configured alpha')
    if capture.get('engine') not in ('nemo', 'whisper'):
        raise ValueError('unknown engine')
    if capture['engine'] == 'nemo':
        _sha(capture.get('tokenizer_sha256'), 'tokenizer_sha256')
    if type(capture.get('context_count')) is not int or capture['context_count'] < 0:
        raise ValueError('context count required')
    cpus = capture.get('cpus')
    if not isinstance(cpus, list) or not cpus or any(type(c) is not int or c < 0 for c in cpus) or len(set(cpus)) != len(cpus):
        raise ValueError('actual CPU placement required')
    if capture['split'] == 'heldout':
        _sha(capture.get('dev_selection_sha256'), 'dev_selection_sha256')
        if capture.get('dev_selection_frozen_before_exposure') is not True:
            raise ValueError('heldout requires pre-exposure dev selection')
        if capture.get('excluded_dev_call') is not False:
            raise ValueError('heldout call overlap unknown or excluded')
    capture['schema'] = 'epyc.cs8.lex2.prospective_attempt.v1'
    return _write_once(path, capture)


def finish_attempt(path, attempt, outcome):
    """Persist child disposition and native proof; unknown is preserved explicitly."""
    if not isinstance(attempt, dict):
        raise ValueError('attempt required')
    attempt = dict(attempt)
    recorded = attempt.pop('record_sha256', None)
    if recorded != _hash(attempt):
        raise ValueError('attempt hash mismatch')
    outcome = dict(outcome)
    status = outcome.get('status')
    if status not in ('ok', 'failure', 'unknown'):
        raise ValueError('invalid disposition')
    if status != 'unknown':
        for key in ('result_sha256', 'stdout_sha256', 'stderr_sha256', 'samples_sha256'):
            _sha(outcome.get(key), key)
        if outcome.get('child_reaped') is not True or type(outcome.get('returncode')) is not int:
            raise ValueError('terminal result requires reaped child and return code')
    if status == 'ok' and outcome['returncode'] != 0:
        raise ValueError('successful outcome must have zero return code')
    if status == 'ok' and attempt['engine'] == 'nemo':
        log = Path(outcome.get('stderr_path', '')).read_bytes()
        if hashlib.sha256(log).hexdigest() != outcome['stderr_sha256']:
            raise ValueError('stderr hash mismatch')
        text = log.decode('utf-8', errors='strict')
        if not re.search(r'LEX2 external tokenizer vocabulary verified \([1-9][0-9]* pieces\)', text):
            raise ValueError('native per-ID vocabulary proof missing')
        if attempt['configured_alpha'] > 0 and attempt['context_count'] > 0:
            required = re.escape('{:.6f}'.format(attempt['configured_alpha']))
            if not re.search(r'RNNT word boosting active phrases=[1-9][0-9]* effective_alpha=' + required + r'(?:\s|$)', text):
                raise ValueError('boosted success requires actual native trie and effective alpha')
    if status == 'unknown' and outcome.get('retry_allowed') is not False:
        raise ValueError('exposed unknown may not be redrawn')
    return _write_once(path, {'schema': 'epyc.cs8.lex2.prospective_disposition.v1',
                              'attempt_sha256': recorded, **outcome})


def verify_pair(attempt_path, disposition_path, result_path, binding):
    """Fail closed before reusing a terminal cached result."""
    a = json.loads(Path(attempt_path).read_text())
    d = json.loads(Path(disposition_path).read_text())
    def check(obj):
        obj = dict(obj); saved = obj.pop('record_sha256', None)
        if saved != _hash(obj): raise ValueError('capture hash mismatch')
        return saved
    ah = check(a); check(d)
    if d.get('attempt_sha256') != ah or d.get('status') not in ('ok', 'failure'):
        raise ValueError('capture disposition mismatch')
    for native, capture in (('clip_id','clip_id'),('wav_sha256','clip_sha256'),('context_sha256','context_sha256'),('engine','engine'),('scope','scope'),('configured_alpha','configured_alpha'),('model_sha256','model_sha256'),('runtime_sha256','binary_sha256'),('grant_id','grant_id')):
        if binding.get(native) != a.get(capture): raise ValueError('capture native binding mismatch: '+native)
    if str(Path(result_path)) != d.get('result_path'):
        raise ValueError('capture result path mismatch')
    for label in ('result', 'stdout', 'stderr', 'samples'):
        path=Path(d[label+'_path']);h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1048576),b''):h.update(block)
        if h.hexdigest() != d[label+'_sha256']: raise ValueError('capture artifact drift: '+label)
    native = json.loads(Path(result_path).read_text())
    if native.get('status') != d['status'] or native.get('rc') != d.get('returncode') or native.get('reaped') is not True:
        raise ValueError('capture native disposition mismatch')
    return d

#!/usr/bin/env python3
"""Execution-mode gate for the candidate replay; no server or scheduler ownership.

FILLER_DRYRUN must survive the actual engine. Qualification uses a fresh tiny
control, never the warm-up or 48 target requests. This gate cannot establish
process cleanup or its own mode propagation through a launcher.
"""
import hashlib
import json
import time

CONTROL = {'messages':[{'role':'user','content':'Count from 1 to 20, separated by commas.'}],
           'max_tokens':32,'temperature':0.0,'cache_prompt':False,'ignore_eos':True,
           'chat_template_kwargs':{'enable_thinking':False}}


def mode(raw):
    if raw == '1': return 'qualification'
    if raw == '0': return 'full'
    raise ValueError('missing or invalid FILLER_DRYRUN; refusing work')


def execute(raw, port, stop, abort, deadline, event_path, *, transport, run_full):
    selected=mode(raw)
    if stop.is_set() or abort.is_set() or time.monotonic() >= deadline:
        raise RuntimeError('stopped or deadline reached before work')
    if selected == 'qualification':
        digest=hashlib.sha256(json.dumps(CONTROL).encode()).hexdigest()
        row=transport(port,'qualification-control',CONTROL,digest,stop,abort,deadline)
        if row.get('tag') != 'qualification-control' or row.get('body_sha256') != digest:
            raise RuntimeError('qualification control identity mismatch')
        if row.get('completed') is not True or row.get('http_status') != 200:
            raise RuntimeError('qualification control failed')
        if type(row.get('predicted_n')) is not int or row['predicted_n'] <= 0:
            raise RuntimeError('qualification control did not report positive native predicted tokens')
        if type(row.get('draft_n')) is not int or row['draft_n'] <= 0:
            raise RuntimeError('qualification control did not report positive native draft count')
        if type(row.get('draft_n_accepted')) is not int or not 0 <= row['draft_n_accepted'] <= row['draft_n']:
            raise RuntimeError('qualification control accepted count missing or invalid')
        # Do not publish the rowflow unit here: keeper stops on first unit.
        # The owning runtime writes it only after sampler and server drain.
        return {'mode':selected,'control':row}
    return run_full()

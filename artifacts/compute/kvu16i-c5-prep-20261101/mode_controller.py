#!/usr/bin/env python3
"""Execution-mode gate for the candidate replay; no server or scheduler ownership.

FILLER_DRYRUN must survive the actual engine. Qualification uses a fresh tiny
control, never the warm-up or 48 target requests. This gate cannot establish
process cleanup or its own mode propagation through a launcher.
"""
import hashlib
import json
import time

CONTROL = {'messages':[{'role':'user','content':'Reply with the single word ready.'}],
           'max_tokens':8,'temperature':0.0,'cache_prompt':False,
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
        # Do not publish the rowflow unit here: keeper stops on first unit.
        # The owning runtime writes it only after sampler and server drain.
        return {'mode':selected,'control':row}
    return run_full()

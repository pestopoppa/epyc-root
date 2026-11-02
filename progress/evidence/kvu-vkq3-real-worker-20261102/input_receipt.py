"""Prepare a VKQ3 input receipt before publication, never under a grant.

The receipt is a measurement of this preflight, not an execution authorization:
the caller must independently bind its digest and preserve all input custody.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import signal
import preflight_supervisor

FLAGS = ['--stdin', '--ids', '--no-escape']
CONTEXT = 131072

def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('not a regular file')
        with os.fdopen(fd, 'rb') as f:
            fd = -1
            value = f.read(limit + 1)
        if len(value) > limit:
            raise ValueError('file exceeds limit')
        return value
    finally:
        if fd != -1:
            os.close(fd)

def digest(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('not a regular file')
        h = hashlib.sha256()
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data:
                return h.hexdigest()
            h.update(data)
    finally:
        os.close(fd)

def parse_catalog(raw):
    entries = {}
    for line in raw.decode('utf-8').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (/[^\n]+)', line)
        if not match or match.group(2) in entries:
            raise ValueError('invalid or duplicate catalog entry')
        entries[match.group(2)] = match.group(1)
    if not entries:
        raise ValueError('empty catalog')
    return entries

def check_count(plan, count):
    n_predict = plan['request']['n_predict']
    if type(n_predict) is not int or n_predict <= 0:
        raise ValueError('invalid output budget')
    if type(count) is not int or count <= 65536 or count + n_predict > CONTEXT:
        raise ValueError('token count outside permitted context')

def prepare(plan_path, prompt_path, tokenizer, model, draft, catalog_path, receipt_path):
    if os.environ.get('FILLER_ID') or os.environ.get('FILLER_DRYRUN'):
        raise RuntimeError('input preparation must not run inside a row grant')
    plan_raw = read_regular(plan_path, 1024 * 1024)
    plan = json.loads(plan_raw)
    prompt = read_regular(prompt_path, 64 * 1024 * 1024)
    if hashlib.sha256(prompt).hexdigest() != plan['context']['sha256']:
        raise ValueError('prompt differs from selected plan')
    catalog_raw = read_regular(catalog_path, 1024 * 1024)
    catalog = parse_catalog(catalog_raw)
    if str(model) not in catalog or str(draft) not in catalog:
        raise ValueError('model and draft must both be catalogued')
    # Whole-model hashes are deliberately preflight-only. All catalog entries,
    # including every split shard and the drafter, must match.
    for path, expected in catalog.items():
        if digest(path) != expected:
            raise ValueError('model catalog mismatch: ' + path)
    tokenizer_hash = digest(tokenizer)
    cancelled = False
    def stop(*_):
        nonlocal cancelled
        cancelled = True
    old = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': str(Path(tokenizer).parent),
               'OMP_NUM_THREADS':'1', 'HIP_VISIBLE_DEVICES':'-1', 'ROCR_VISIBLE_DEVICES':'-1'}
        run = preflight_supervisor.supervise([str(tokenizer), '-m', str(model), *FLAGS], prompt, env,
                                              stopped=lambda: cancelled, timeout_s=1800,
                                              stdout_cap=16*1024*1024, stderr_cap=65536)
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
    if run['status'] != 'completed' or not run['cleanup'] or run['input_bytes_written'] != len(prompt):
        raise RuntimeError('tokenizer preflight failed: ' + str(run['status']))
    ids = json.loads(run['stdout'])
    if not isinstance(ids, list) or any(type(i) is not int or i < 0 for i in ids):
        raise ValueError('invalid native tokenizer output')
    check_count(plan, len(ids))
    receipt = {'schema':'kvu-vkq3-preflight-v1', 'plan_sha256':hashlib.sha256(plan_raw).hexdigest(),
               'prompt_sha256':hashlib.sha256(prompt).hexdigest(), 'tokenizer_sha256':tokenizer_hash,
               'model_catalog_sha256':hashlib.sha256(catalog_raw).hexdigest(),
               'tokenizer_path':str(tokenizer), 'model_path':str(model), 'draft_path':str(draft),
               'tokenizer_flags':FLAGS, 'model_shard0_sha256':catalog[str(model)],
               'draft_sha256':catalog[str(draft)], 'token_count':len(ids),
               'native_ids_sha256':hashlib.sha256(run['stdout']).hexdigest()}
    data = (json.dumps(receipt, sort_keys=True) + '\n').encode()
    fd = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    return hashlib.sha256(data).hexdigest()

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','prompt','tokenizer','model','draft','catalog','receipt'):
        parser.add_argument('--'+name, required=True)
    args=parser.parse_args()
    print(prepare(args.plan,args.prompt,args.tokenizer,args.model,args.draft,args.catalog,args.receipt),flush=True)

"""Prospective per-process M4 CPU capture; no retrospective measurement creation."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def capture(*, directory, row, arm, pair, role, model, model_sha, recipe, context, binary, commit, producer, runner, comparator):
    if arm not in ('baseline', 'candidate') or type(pair) is not int or pair not in range(5):
        raise ValueError('invalid process identity')
    value = row['decode_tps']
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('invalid throughput')
    summary = Path(row['summary_path']).resolve()
    digest = hashlib.sha256(summary.read_bytes()).hexdigest()
    if digest != row['summary_sha256']:
        raise ValueError('summary changed before capture')
    plan_digest = hashlib.sha256(summary.with_name('plan.json').read_bytes()).hexdigest()
    prompt_digest = row['prompt_sha256']
    if len(prompt_digest) != 64 or any(c not in '0123456789abcdef' for c in prompt_digest):
        raise ValueError('invalid native prompt digest')
    stamp = datetime.now(timezone.utc).isoformat()
    measurement = {
        'measurement_id': f"m4_cpu_speed_{arm}_pair{pair:02d}_{hashlib.sha256(str(summary).encode()).hexdigest()[:12]}_{digest[:16]}_decode_tps",
        'metric':'decode_tokens_per_s', 'value':float(value), 'unit':'tokens_per_second',
        'category':arm.upper(), 'metric_direction':'higher_better', 'protocol_id':'', 'reps':1,
        'reps_basis':'one fresh-server scored process', 'model_path':model, 'recipe':recipe,
        'attestation_locator':str(summary), 'attestation_sha256':digest, 'recorded_at':stamp,
        'date':stamp[:10], 'role':role,
        'claim':f"{arm} fresh-server process measured {float(value):.9g} decode tokens per second",
        'extra':{'model_sha256':model_sha, 'binary':str(binary), 'context':context,
            'native_scenario':row['scenario'], 'source_commit':commit, 'pair':pair,
            'plan_sha256':plan_digest, 'prompt_sha256':prompt_digest,
            'producer_sha256':hashlib.sha256(Path(producer).read_bytes()).hexdigest(),
            'capture_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'native_runner_sha256':hashlib.sha256(Path(runner).read_bytes()).hexdigest(),
            'native_comparator_sha256':hashlib.sha256(Path(comparator).read_bytes()).hexdigest()}}
    measurement['measurement_sha256'] = hashlib.sha256(canonical(measurement)).hexdigest()
    document = {'schema':'epyc.m4.cpu_speed_process.v1', 'measurement':measurement}
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{arm}-pair-{pair:02d}.json'
    fd, temp = tempfile.mkstemp(prefix='.capture-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(canonical(document) + b'\n'); out.flush(); os.fsync(out.fileno())
        os.link(temp, target)  # atomic, write-once; never overwrite a prior process
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        os.unlink(temp)
    return measurement

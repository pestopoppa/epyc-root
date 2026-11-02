#!/usr/bin/env python3
"""SR-6 block controller seam; model-free, not a grant or executable row.

Injected adapters are untrusted. A real launcher must prove the authoritative
output root and exposure inventory, grant and deadline, binary/model identity,
residency, STOP handling, and descendant drain. A successful return is capture
only, not a valid scientific result. No adapter here starts a real server.
"""
from pathlib import Path

from block_guard import ARMS
from exposure_inventory import inventory
from native_worker import HEX, SAFE_ID, canonical, capture_request, digest, exclusive_json
from server_lifecycle import with_server


class BlockError(RuntimeError):
    pass


def execute_block(*, output, block, sampler, sampler_sha256,
                  admission_check, spawn, verify_ready_and_identity, post):
    """Capture one planned block at most once under injected lifecycle adapters.

    Before any spawn, an exclusive, fsynced block-start marker makes any
    interrupted block non-resumable in this output directory. The caller must
    ensure this directory is the sole authoritative exposure root across all
    windows and retries, and that concurrent writers are excluded. Per-request exposure is also recorded before POST.
    """
    if not isinstance(output, Path) or not output.is_dir() or not isinstance(block, dict):
        raise BlockError('existing output directory and block required')
    window, number, prompts, arms = (block.get('window'), block.get('block'),
                                     block.get('prompts'), block.get('arm_order'))
    if not isinstance(window, str) or not SAFE_ID.fullmatch(window) or type(number) is not int or number < 0:
        raise BlockError('invalid block identity')
    if not isinstance(prompts, list) or not prompts or any(not isinstance(p, dict) for p in prompts):
        raise BlockError('invalid prompts')
    ids = [p.get('id') for p in prompts]
    if any(not isinstance(p, str) or not SAFE_ID.fullmatch(p) for p in ids):
        raise BlockError('invalid prompt identity')
    if (not isinstance(arms, list) or len(arms) != len(ARMS)
            or any(not isinstance(arm, str) for arm in arms) or set(arms) != ARMS):
        raise BlockError('invalid arm order')
    try:
        attempts = inventory(output)
    except (OSError, ValueError) as exc:
        raise BlockError('exposure inventory invalid') from exc
    if any(attempt['prompt_id'] in ids for attempt in attempts):
        raise BlockError('prompt already exposed in this inventory')
    if (not isinstance(sampler, dict) or not sampler or not isinstance(sampler_sha256, str)
            or not HEX.fullmatch(sampler_sha256)):
        raise BlockError('invalid sampler seal')
    try:
        if digest(canonical(sampler)) != sampler_sha256:
            raise BlockError('sampler seal mismatch')
        if set(sampler) & {'prompt', 'seed', 'cache_prompt', 'return_tokens'}:
            raise BlockError('sampler overrides protected request fields')
        for p in prompts:
            if (not isinstance(p.get('rendered'), str) or not p['rendered']
                    or digest(p['rendered'].encode()) != p.get('rendered_sha256')
                    or type(p.get('seed')) is not int or p['seed'] < 0):
                raise BlockError('invalid rendered prompt or seed')
        if len({p['seed'] for p in prompts}) != len(prompts):
            raise BlockError('duplicate prompt seed')
        if not all(callable(x) for x in (admission_check, spawn, verify_ready_and_identity, post)):
            raise BlockError('missing adapter')
        # Check serialization before creating the irreversible attempt marker.
        plan_digest = digest(canonical(block))
        exclusive_json(output / f'{window}-{number}.block-start.json',
                       {'schema': 'sr6.block-start.v1', 'window': window, 'block': number,
                        'plan_sha256': plan_digest, 'sampler_sha256': sampler_sha256})
        count = 0
        for arm in arms:
            def run(server):
                nonlocal count
                server_sha = server.evidence.get('server_record_sha256')
                if not isinstance(server_sha, str) or not HEX.fullmatch(server_sha):
                    raise BlockError('server record identity missing')
                for prompt in prompts:
                    record = capture_request(output, window=window, block=number, arm=arm,
                        prompt=prompt, sampler=sampler, server_record_sha256=server_sha,
                        post=lambda payload: post(server, payload))
                    if record.get('state') != 'raw' or record.get('http_status') != 200:
                        raise BlockError('request failed; entire block abandoned')
                    count += 1
            with_server(arm=arm, admission_check=admission_check, spawn=spawn,
                        verify_ready_and_identity=verify_ready_and_identity, run=run)
        return {'state': 'CAPTURED_ONLY', 'attempts': count, 'verdict': None,
                'limitations': ['adapters, exposure inventory and output root require independent verification',
                                'response validity, token identity, residency and tree drain are unverified']}
    except (OSError, TypeError, ValueError) as exc:
        raise BlockError('block refused or interrupted') from exc

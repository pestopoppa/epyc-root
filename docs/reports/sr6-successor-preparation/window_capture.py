#!/usr/bin/env python3
"""SR-6 sealed-plan window coordinator; not a runnable inference row.

The caller must authenticate the plan digest and output root, provide real
server lifecycle/identity adapters, and establish in-flight STOP, complete
descendant drain, placement and runtime seals. No server starts at import.
"""
import hashlib
from pathlib import Path

from keeper_block import capture_keeper_block
from native_worker import canonical, exclusive_json
from worker import HEX, build_schedule


def capture_window(*, packet, packet_sha256, window, output, keeper_args,
                   spawn, verify_ready_and_identity, port, timeout_s,
                   max_response_bytes, drain=None):
    """Validate all three partitions, capture exactly one sealed window once.

    The exclusive marker makes an interrupted window non-resumable here.
    The output directory must be the sole authoritative exposure root across
    all windows and invocations, with concurrent writers excluded externally.
    """
    if not isinstance(packet_sha256, str) or not HEX.fullmatch(packet_sha256):
        raise ValueError('pinned packet digest required')
    if hashlib.sha256(canonical(packet)).hexdigest() != packet_sha256:
        raise ValueError('packet digest mismatch')
    schedule = build_schedule(packet)
    if not isinstance(window, str) or not window:
        raise ValueError('window required')
    selected = [block for block in schedule['blocks'] if block['window'] == window]
    if not selected:
        raise ValueError('window absent from plan')
    if not isinstance(output, Path) or output.is_symlink() or not output.is_dir():
        raise ValueError('real authoritative output directory required')
    required = {'env', 'row_id', 'grant_path', 'stop_path', 'guard_sha256'}
    if not isinstance(keeper_args, dict) or set(keeper_args) not in (required, required | {'guard_path'}):
        raise ValueError('bound keeper inputs required')
    if not callable(spawn) or not callable(verify_ready_and_identity):
        raise ValueError('lifecycle adapters required')
    # No path supplied by a packet can choose the marker name.
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in window):
        raise ValueError('unsafe window identity')
    exclusive_json(output / (window + '.window-start.json'),
                   {'schema': 'sr6.window-start.v1', 'window': window,
                    'packet_sha256': packet_sha256,
                    'sampler_sha256': schedule['sampler_sha256']})
    for block in selected:
        result = capture_keeper_block(**keeper_args, output=output, block=block,
            sampler=packet['sampler'], sampler_sha256=schedule['sampler_sha256'],
            spawn=spawn, verify_ready_and_identity=verify_ready_and_identity,
            port=port, timeout_s=timeout_s, max_response_bytes=max_response_bytes,
            drain=drain)
        if not isinstance(result, dict) or result.get('state') != 'CAPTURED_ONLY':
            raise ValueError('block not captured; window abandoned')
    return {'state': 'CAPTURED_ONLY', 'window': window, 'blocks': len(selected),
            'verdict': None, 'limitations': ['root, runtime, adapters and cleanup require external proof']}

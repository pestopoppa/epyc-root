#!/usr/bin/env python3
"""Prototype bounded/resumable JetLong request runner; not a row launcher.

Caller supplies a transport callable; no server lifecycle or native entry exists.
Uncertain transport failures remain started-only unknown and halt the segment.
"""
import hashlib
import json
import time
from pathlib import Path
import ledger

class ProtocolError(Exception):
    pass

def load_tokens(item, fixture_root):
    root = Path(fixture_root).resolve()
    path = (root / item['tokens_path']).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ProtocolError('fixture escapes root')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['tokens_sha256']:
        raise ProtocolError('fixture digest mismatch')
    ids = json.loads(raw)
    if not isinstance(ids, list) or not ids or any(type(x) is not int or x < 0 for x in ids):
        raise ProtocolError('fixture must be a nonempty list of token ids')
    if len(ids) != item['length']:
        raise ProtocolError('fixture token count mismatch')
    return ids

def run_segment(plan_path, output_dir, fixture_root, arm, transport, budget_s,
                minimum_cell_s, request_timeout_s, clock=time.monotonic):
    """Return 0 if all selected arm cells finished, 75 if partial, 1 if uncertain.

    transport(prompt_ids, timeout_s) returns {content: str, timings: dict};
    raises TimeoutError only for an observed request timeout. Any uncertain failure
    stops immediately; a started-only record is intentionally never auto-retried.
    This interface assumes caller establishes a fresh isolated server and cleanup.
    """
    if arm not in ledger.ARMS or min(budget_s, minimum_cell_s, request_timeout_s) <= 0:
        raise ValueError('invalid segment configuration')
    if request_timeout_s > minimum_cell_s:
        raise ValueError('cell reservation must cover request timeout')
    plan, pin = ledger.initialize(output_dir, plan_path)
    items = {item['id']: item for item in plan['items']}
    state = ledger.inventory(output_dir, plan, pin)
    if any(a == arm for _, a in state['unknown']):
        return 1
    deadline = clock() + budget_s
    for item_id, a in state['unstarted']:
        if a != arm:
            continue
        if deadline - clock() < minimum_cell_s:
            return 75
        item = items[item_id]
        # Validate before recording a start or making any request.
        tokens = load_tokens(item, fixture_root)
        if deadline - clock() < minimum_cell_s:
            return 75
        ledger.start(output_dir, plan, pin, item_id, arm)
        try:
            result = transport(tokens, request_timeout_s)
            if not isinstance(result, dict) or not isinstance(result.get('content'), str) or not isinstance(result.get('timings'), dict):
                raise ProtocolError('malformed response')
            timing = result['timings']
            if type(timing.get('predicted_n')) is not int or timing['predicted_n'] < 1 or type(timing.get('predicted_ms')) not in (int, float) or not 0 < timing['predicted_ms'] < float('inf'):
                raise ProtocolError('invalid decode timings')
            ledger.finish(output_dir, pin, item_id, arm, 'ok', result['content'], timing)
        except TimeoutError:
            ledger.finish(output_dir, pin, item_id, arm, 'timeout')
            # An HTTP timeout does not prove the server stopped its work.
            return 75
        except Exception:
            # The request may have reached the endpoint. Keep immutable unknown.
            return 1
    return 0

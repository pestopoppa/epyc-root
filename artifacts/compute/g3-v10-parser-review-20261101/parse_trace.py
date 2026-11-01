#!/usr/bin/env python3
"""Parse candidate G3_TRACE_V1 records; structural evidence only, never validates correlation."""
import argparse
import collections
import json
from pathlib import Path

MAX_BYTES = 16 * 1024 * 1024
MAX_LINE = 4096
MAX_DISPATCHES = 20000
KERNELS = {0: 'NONE', 100: 'VEC', 200: 'TILE', 300: 'WMMA_F16', 400: 'MMA_F16'}

class TraceError(ValueError):
    pass

def _record(line, fields):
    pairs = {}
    for item in line:
        if item.count('=') != 1:
            raise TraceError('malformed field')
        key, value = item.split('=', 1)
        if not key or not value or key in pairs:
            raise TraceError('empty or duplicate field')
        pairs[key] = value
    if set(pairs) != fields:
        raise TraceError('unexpected field set')
    return pairs

def _ints(rec, keys):
    for key in keys:
        try:
            value = int(rec[key])
        except ValueError as exc:
            raise TraceError('non-integer field ' + key) from exc
        if str(value) != rec[key]:
            raise TraceError('noncanonical integer ' + key)
        rec[key] = value
    return rec

def parse_bytes(data):
    if len(data) > MAX_BYTES:
        raise TraceError('log exceeds byte limit')
    # Every instrumentation record ends with a newline. Do not accept a
    # superficially complete final marker that could be a truncated write.
    if data and not data.endswith(b'\n') and b'G3_TRACE_V1' in data.rsplit(b'\n', 1)[-1]:
        raise TraceError('unterminated final marker')
    try:
        lines = data.decode('utf-8', errors='strict').splitlines()
    except UnicodeDecodeError as exc:
        raise TraceError('invalid UTF-8') from exc
    epochs = []
    active = None
    last_epoch = 0
    next_dispatch = 0
    unscoped = []
    for line in lines:
        if len(line.encode('utf-8')) > MAX_LINE:
            raise TraceError('line exceeds byte limit')
        if 'G3_TRACE_V1' not in line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[0] != 'G3_TRACE_V1':
            raise TraceError('interleaved or malformed marker')
        kind = parts[1]
        if kind == 'OVERFLOW':
            raise TraceError('instrumentation overflow')
        if kind == 'BEGIN':
            if active is not None:
                raise TraceError('nested epoch')
            rec = _record(parts[2:], {'epoch', 'slot', 'task', 'phase', 'draft', 'rows', 'off'})
            rec = _ints(rec, ('epoch', 'slot', 'task', 'draft', 'rows', 'off'))
            if rec['epoch'] != last_epoch + 1 or rec['slot'] != 0 or rec['rows'] < 1 or rec['off'] < 0 or rec['draft'] < 0:
                raise TraceError('invalid epoch or batch metadata')
            if rec['phase'] not in ('verify', 'other_or_unknown'):
                raise TraceError('invalid phase')
            if rec['phase'] == 'verify' and (rec['task'] < 0 or rec['draft'] < 1 or rec['rows'] < rec['draft'] + 1):
                raise TraceError('invalid verify metadata')
            active = {'begin': rec, 'dispatches': []}
        elif kind == 'DISPATCH':
            fields = {'i', 'device', 'kernel', 'q0', 'q1', 'q2', 'q3', 'k0', 'k1', 'k2', 'ktype', 'vtype'}
            rec = _ints(_record(parts[2:], fields), ('i', 'device', 'kernel', 'q0', 'q1', 'q2', 'q3', 'k0', 'k1', 'k2'))
            if rec['i'] != next_dispatch or rec['i'] >= MAX_DISPATCHES or rec['device'] < 0 or rec['kernel'] not in KERNELS or rec['kernel'] == 0 or any(rec[k] <= 0 for k in ('q0', 'q1', 'q2', 'q3', 'k0', 'k1', 'k2')):
                raise TraceError('invalid dispatch sequence or tensor metadata')
            next_dispatch += 1
            rec['kernel_name'] = KERNELS[rec['kernel']]
            (active['dispatches'] if active is not None else unscoped).append(rec)
        elif kind == 'END':
            rec = _ints(_record(parts[2:], {'epoch', 'rc'}), ('epoch', 'rc'))
            if active is None or rec['epoch'] != active['begin']['epoch']:
                raise TraceError('orphan or mismatched epoch end')
            if rec['rc'] != 0:
                raise TraceError('decode returned nonzero')
            last_epoch = rec['epoch']
            active['end'] = rec
            epochs.append(active)
            active = None
        else:
            raise TraceError('unknown trace marker')
    if active is not None:
        raise TraceError('incomplete epoch')
    if not epochs:
        raise TraceError('no complete epochs')
    scoped = [e for e in epochs if e['begin']['phase'] == 'verify']
    counts = collections.Counter(d['kernel_name'] for e in scoped for d in e['dispatches'])
    return {'schema': 'g3.trace.structural.v1', 'status': 'STRUCTURAL_ONLY',
            'correlation_proven': False, 'runtime_identity_proven': False,
            'note': 'Requires independent epoch-containment controls, loaded-library identity and GPU residency; never infers a global absence.',
            'epochs': epochs, 'verify_epoch_count': len(scoped),
            'verify_epochs_without_dispatch': [e['begin']['epoch'] for e in scoped if not e['dispatches']],
            'nonverify_dispatch_count': sum(len(e['dispatches']) for e in epochs if e['begin']['phase'] != 'verify'),
            'unscoped_dispatch_count': len(unscoped),
            'verify_dispatch_counts': dict(sorted(counts.items())),
            'unscoped_dispatches': unscoped}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log', type=Path)
    args = ap.parse_args()
    try:
        with args.log.open('rb') as handle:
            result = parse_bytes(handle.read(MAX_BYTES + 1))
    except (OSError, TraceError) as exc:
        ap.exit(2, 'REFUSED: ' + str(exc) + '\n')
    print(json.dumps(result, sort_keys=True, indent=2))

if __name__ == '__main__':
    main()

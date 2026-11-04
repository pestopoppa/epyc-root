#!/usr/bin/env python3
"""Fail-closed evaluation of contemporaneous G3 GPU residency evidence.

Inputs are captured observations, not a substitute for device isolation or
per-process VRAM accounting. A positive result only qualifies residency.
"""
import hashlib
import json
import os
from pathlib import Path


def _mapped(maps, path, stat):
    expected_dev = f'{os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x}'
    for line in maps.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6:
            continue
        try:
            device = ':'.join(f'{int(part, 16):x}' for part in fields[3].split(':'))
            if device == expected_dev and int(fields[4]) == stat.st_ino and fields[5] == str(path):
                return True
        except ValueError:
            continue
    return False


def _gpu(sample, card):
    try:
        if sample['rocm_smi_rc'] != 0:
            return None
        data = json.loads(sample['rocm_smi'])[card]
        product = ' '.join(str(v) for k, v in data.items() if 'product' in k.lower() or 'card series' in k.lower())
        used = int(data['VRAM Total Used Memory (B)'])
        return (product, used) if 'MI210' in product.upper() and used >= 0 else None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def analyze_residency(*, baseline, samples, card, pid, backend, expected_sha256, start, end):
    """Return PASS only if one in-window sample carries every residency witness.

    Times are UTC epoch seconds from the same clock. baseline must predate start;
    samples require numeric `time`, `pid`, `alive`, `maps`, `kfd_pid_present`,
    `rocm_smi_rc` and `rocm_smi`. The path's device/inode and digest must match
    the mapped library and build receipt. This does not attribute total VRAM to PID.
    """
    reasons = []
    try:
        path = Path(backend).resolve(strict=True)
        st = path.stat()
        with path.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
    except (OSError, ValueError, TypeError) as exc:
        return {'status': 'UNKNOWN', 'reasons': [f'backend unavailable: {exc}'],
                'backend': str(backend), 'backend_sha256': None, 'card': card,
                'matching_samples': [],
                'limitation': 'VRAM delta is device-wide, not per-process attribution.'}
    if digest != expected_sha256:
        reasons.append('backend digest mismatch')
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start >= end:
        raise ValueError('invalid observation window')
    if type(pid) is not int or pid <= 0 or not isinstance(card, str) or not card:
        raise ValueError('invalid pid or card')
    base = _gpu(baseline, card)
    if base is None or not isinstance(baseline.get('time'), (int, float)) or baseline['time'] >= start:
        reasons.append('missing valid pre-window MI210 baseline')
    matched = []
    if not reasons:
        for sample in samples:
            t = sample.get('time')
            gpu = _gpu(sample, card)
            if (isinstance(t, (int, float)) and start <= t <= end and
                    sample.get('pid') == pid and sample.get('alive') is True and
                    sample.get('kfd_pid_present') is True and gpu is not None and
                    gpu[0] == base[0] and gpu[1] > base[1] and
                    isinstance(sample.get('maps'), str) and _mapped(sample['maps'], path, st)):
                matched.append({'time': t, 'vram_baseline_bytes': base[1],
                                'vram_used_bytes': gpu[1], 'vram_delta_bytes': gpu[1] - base[1]})
        if not matched:
            reasons.append('no single in-window sample has all residency witnesses')
    return {'status': 'PASS' if not reasons else 'UNKNOWN', 'reasons': reasons,
            'backend': str(path), 'backend_sha256': digest, 'card': card,
            'matching_samples': matched,
            'limitation': 'VRAM delta is device-wide, not per-process attribution.'}

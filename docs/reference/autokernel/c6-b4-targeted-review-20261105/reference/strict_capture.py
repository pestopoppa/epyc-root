"""Refuse a native rc1 unless the complete backend summary accounts for real FAIL cases."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'owned-code'))
from scripts.kernel_rnd.autokernel.execution import t0_provider
import re


def read_complete(log_text: str, native_rc: int, backend: str = 'ROCm0'):
    if native_rc not in (0, 1):
        raise ValueError(f'unknown native exit {native_rc}')
    parsed = t0_provider.parse_backend_ops_console(log_text)
    parsed.reconcile()
    selected = [b for b in parsed.backends if b.name == backend and not b.skipped]
    if len(selected) != 1 or selected[0].reported_total is None or selected[0].reported_passed is None:
        raise ValueError('missing native backend terminal summary')
    cases = list(selected[0].cases)
    if not cases:
        raise ValueError('native backend has no cases')
    failed = [case for case in cases if case.status == 'fail']
    if (native_rc == 1 and not failed) or (native_rc == 0 and failed):
        raise ValueError('native exit contradicts case failures')
    clean = re.sub(r'\x1b\[[0-9;]*m', '', log_text)
    verdict = 'FAIL' if native_rc == 1 else 'OK'
    if not re.search(rf'^\s*Backend {re.escape(backend)}: {verdict}\s*$', clean, re.M):
        raise ValueError('native backend terminal verdict absent or mismatched')
    if not re.search(r'^\d+/\d+ backends passed\s*$', clean, re.M):
        raise ValueError('native overall terminal summary absent')
    return cases

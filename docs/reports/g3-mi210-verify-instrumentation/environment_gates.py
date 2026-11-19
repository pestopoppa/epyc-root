"""Independent read-only GPU lease and operating-clock observations.

PASS is bounded to sampled request windows, never a continuous-isolation claim.
Clock limits and maximum sample gap must be declared before capture.
"""
import datetime
import hashlib
import math
import os
from pathlib import Path
import re
import time

GRANTS = Path('/mnt/raid0/llm/tmp/compute-flags/grants')
KFD = Path('/sys/class/kfd/kfd/proc')


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def policy_check(policy):
    for clock in ('sclk', 'mclk'):
        low, high = policy[clock + '_mhz']
        if not all(number(v) for v in (low, high)) or not 0 < low <= high:
            raise ValueError('invalid operating-clock bounds')
    if not number(policy['max_gap_s']) or policy['max_gap_s'] <= 0:
        raise ValueError('invalid maximum sample gap')


def active_clock(path):
    # amdgpu pp_dpm_* marks the active frequency with '*'. No inferred clock.
    active = [line for line in Path(path).read_text().splitlines() if '*' in line]
    if len(active) != 1:
        raise ValueError('missing or ambiguous active GPU clock')
    match = re.fullmatch(r'\s*\d+:\s*(\d+)Mhz\s*\*\s*', active[0], re.IGNORECASE)
    if not match or int(match[1]) <= 0:
        raise ValueError('unreadable active GPU clock')
    return int(match[1])


def grant_fields(path):
    raw = path.read_bytes()
    words = raw.decode('ascii').split()
    fields = dict(word.split('=', 1) for word in words)
    if len(fields) != len(words):
        raise ValueError('duplicate grant fields')
    return fields, hashlib.sha256(raw).hexdigest()


def gpu_lease(fields):
    return 'mi210_0' in fields.get('regions', '').split(',') or bool({'mi210_0', 'gpu-quiet'} & set(fields.get('holds', '').split(',')))


def sample_environment(*, row_id, pid, device, grants=GRANTS, kfd=KFD, env=None):
    """Read scheduler lease and all MI210 KFD allocations separately from traces."""
    env = os.environ if env is None else env
    result = {'start': time.time(), 'row_id': row_id, 'pid': pid,
              'gpu_id': device['gpu_id'], 'bdf': device['bdf']}
    try:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', row_id) or env.get('FILLER_ID') != row_id:
            raise ValueError('row identity mismatch')
        own = Path(grants) / (row_id + '.grant')
        fields, sha = grant_fields(own)
        start, end = [datetime.datetime.strptime(fields[k], '%Y-%m-%dT%H:%MZ').replace(
            tzinfo=datetime.timezone.utc).timestamp() for k in ('start', 'end')]
        if ('mi210_0' not in fields.get('regions', '').split(',') or not start <= result['start'] < end
                or (Path(grants) / (row_id + '.ended')).exists()):
            raise ValueError('no live MI210 lease')
        for other in Path(grants).glob('*.grant'):
            if other == own or other.with_suffix('.ended').exists():
                continue
            foreign, _ = grant_fields(other)
            if gpu_lease(foreign):
                raise ValueError('competing MI210 grant')
        registry = Path(env['FILLER_PIDFILE']).read_text().splitlines()
        if str(pid) not in registry:
            raise ValueError('server missing from row process registry')
        if Path(env['FILLER_STOPFILE']).exists() or result['start'] >= float(env['FILLER_DEADLINE']):
            raise ValueError('row stopped or expired')
        allocations = {}
        for process in Path(kfd).iterdir():
            if not process.name.isdigit():
                continue
            allocation = process / ('vram_' + str(device['gpu_id']))
            if allocation.exists():
                amount = int(allocation.read_text())
                if amount < 0:
                    raise ValueError('negative KFD allocation')
                allocations[process.name] = amount
        if allocations.get(str(pid), 0) <= 0 or any(p != str(pid) for p in allocations):
            raise ValueError('missing own or present foreign MI210 allocation')
        result.update(ownership='PASS', grant_sha256=sha, grant_start=start, grant_end=end,
                      allocations=allocations)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.update(ownership='UNKNOWN', ownership_error=str(exc))
    try:
        dev = Path(device['device_vram']).parent
        result.update(sclk_mhz=active_clock(dev / 'pp_dpm_sclk'),
                      mclk_mhz=active_clock(dev / 'pp_dpm_mclk'))
    except (OSError, ValueError) as exc:
        result['clock_error'] = str(exc)
    result['end'] = time.time()
    return result


def assess_environment(samples, windows, *, policy, row_id, pid, device):
    try:
        policy_check(policy)
        if not windows or not samples:
            raise ValueError('missing environment samples or request windows')
        samples = [s for s in samples if any(a <= s['start'] <= s['end'] <= b for a, b in windows)]
        if not samples:
            raise ValueError('no in-request environment observations')
        sha = None
        previous = None
        for sample in samples:
            a, b = sample['start'], sample['end']
            if (not all(number(v) for v in (a, b)) or a > b or (previous is not None and a < previous)
                    or sample['row_id'] != row_id or sample['pid'] != pid
                    or sample['gpu_id'] != device['gpu_id'] or sample['bdf'] != device['bdf']
                    or sample['ownership'] != 'PASS'):
                raise ValueError('invalid, unordered, foreign or unowned environment sample')
            if b - a > policy['max_gap_s']:
                raise ValueError('environment observation too slow')
            # Re-evaluate the retained KFD observation, even when the sampler's
            # ownership flag claims PASS. Match its strict no-foreign-entry rule.
            allocations = sample['allocations']
            if (not isinstance(allocations, dict) or set(allocations) != {str(pid)}
                    or type(allocations[str(pid)]) is not int or allocations[str(pid)] <= 0):
                raise ValueError('missing own or present foreign MI210 allocation')
            previous = b
            if not re.fullmatch(r'[0-9a-f]{64}', sample['grant_sha256']):
                raise ValueError('invalid grant digest')
            if not sample['grant_start'] <= a <= b < sample['grant_end']:
                raise ValueError('environment observation outside grant')
            if sha is not None and sha != sample['grant_sha256']:
                raise ValueError('grant changed during capture')
            sha = sample['grant_sha256']
            for clock in ('sclk', 'mclk'):
                low, high = policy[clock + '_mhz']
                actual = sample[clock + '_mhz']
                if not number(actual) or not low <= actual <= high:
                    raise ValueError('GPU operating clock outside declared bounds')
        for start, end in windows:
            if not all(number(v) for v in (start, end)) or start >= end:
                raise ValueError('invalid environment request window')
            inside = [s for s in samples if start <= s['start'] <= s['end'] <= end]
            if len(inside) < 2:
                raise ValueError('fewer than two in-request environment samples')
            gaps = [inside[0]['start'] - start, end - inside[-1]['end']]
            gaps += [b['start'] - a['end'] for a, b in zip(inside, inside[1:])]
            if max(gaps) > policy['max_gap_s']:
                raise ValueError('environment sampling gap exceeds declared bound')
        return {'status': 'PASS', 'sample_count': len(samples), 'grant_sha256': sha,
                'policy': policy, 'scope': 'sampled MI210 lease/allocation and operating clocks during request windows'}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {'status': 'UNKNOWN', 'reason': str(exc)}

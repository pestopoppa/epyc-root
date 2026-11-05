"""Prospective fixture marker clock constraints, not token attribution."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'nemo-marker-csv-adapter-20261105'))
from marker_csv import normalize, PREFIX


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def validate_fixture_markers(log_text, marker_csv):
    """Match two fixture host brackets to parsed profiler points.

    The intersection is conditional on a constant clock offset during the two
    brackets; agreement cannot establish clock identity or drift.
    """
    if not isinstance(log_text, str):
        raise ValueError('fixture log must be text')
    host = {}
    for line in log_text.splitlines():
        if not line.startswith('{'):
            continue
        try:
            row = json.loads(line, object_pairs_hook=_unique)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError('malformed fixture JSON') from exc
        if not isinstance(row, dict):
            raise ValueError('invalid fixture record')
        if row.get('event') != 'clock_sync':
            continue
        marker = row.get('marker')
        if marker not in (PREFIX + '0', PREFIX + '1') or marker in host:
            raise ValueError('unexpected or duplicate clock marker')
        values = [row.get(k) for k in ('before_ns', 'after_ns', 'pid', 'tid')]
        if any(type(v) is not int or v <= 0 for v in values):
            raise ValueError('invalid host bracket or identity')
        before, after, pid, tid = values
        if before > after or row.get('schema') != 'epyc.nemo.fixture-event.v1' or row.get('clock_domain') != 'CLOCK_MONOTONIC':
            raise ValueError('invalid host clock envelope')
        host[marker] = (before, after, pid, tid)
    if set(host) != {PREFIX + '0', PREFIX + '1'}:
        raise ValueError('missing host clock markers')
    if host[PREFIX + '0'][1] >= host[PREFIX + '1'][0]:
        raise ValueError('host clock markers out of order')
    if host[PREFIX + '0'][2:] != host[PREFIX + '1'][2:]:
        raise ValueError('host marker identity mismatch')
    profiler = normalize(marker_csv)
    lower, upper = None, None
    previous = None
    for marker in profiler:
        before, after, pid, tid = host[marker['marker']]
        if (marker['pid'], marker['tid']) != (pid, tid):
            raise ValueError('profiler marker identity mismatch')
        stamp = marker['timestamp_ns']
        if previous is not None and stamp <= previous:
            raise ValueError('profiler marker order mismatch')
        previous = stamp
        lo, hi = before - stamp, after - stamp
        lower = lo if lower is None else max(lower, lo)
        upper = hi if upper is None else min(upper, hi)
    if lower > upper:
        raise ValueError('no constant-offset intersection')
    return {'status': 'CONSISTENT_CONDITIONAL_ON_CONSTANT_OFFSET',
            'host_minus_profiler_offset_ns': [lower, upper],
            'width_ns': upper - lower, 'matched_markers': len(profiler),
            'limitations': 'No clock identity, drift bound, graph-to-token attribution or historical boundary established.'}


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: fixture_clock_join.py FIXTURE_LOG MARKER_CSV')
    try:
        result = validate_fixture_markers(Path(sys.argv[1]).read_text(), Path(sys.argv[2]))
    except (OSError, ValueError) as exc:
        raise SystemExit(f'INCONCLUSIVE: {exc}')
    print(json.dumps(result, sort_keys=True))

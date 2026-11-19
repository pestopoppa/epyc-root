"""Project normalized scheduler switches; never an admission predicate."""
from collections import defaultdict


def project_intervals(events, *, cpus, begin_ns, end_ns, allowed_by_tid):
    """Project bracketed, ordered per-CPU switch chains to half-open intervals.

    Owned thread IDs and allowed CPUs are unverified caller assertions.
    """
    if (not isinstance(cpus, (set, frozenset)) or not cpus or
            any(type(cpu) is not int or cpu < 0 for cpu in cpus)):
        raise ValueError('invalid CPUs')
    if type(begin_ns) is not int or type(end_ns) is not int or not 0 < begin_ns < end_ns:
        raise ValueError('invalid interval')
    if not isinstance(allowed_by_tid, dict) or not allowed_by_tid:
        raise ValueError('missing owned thread map')
    for tid, allowed in allowed_by_tid.items():
        if (type(tid) is not int or tid <= 0 or
                not isinstance(allowed, (set, frozenset)) or not allowed or
                any(type(cpu) is not int or cpu < 0 for cpu in allowed)):
            raise ValueError('invalid owned thread map')
    grouped = {cpu: [] for cpu in cpus}
    for event in events:
        if (not isinstance(event, dict) or type(event.get('cpu')) is not int or
                event['cpu'] not in grouped or
                any(type(event.get(k)) is not int for k in ('timestamp_ns', 'prev_tid', 'next_tid')) or
                event['timestamp_ns'] <= 0 or event['prev_tid'] < 0 or event['next_tid'] < 0):
            raise ValueError('invalid switch')
        grouped[event['cpu']].append(event)
    intervals = []
    summary = {str(cpu): {'owned_ns': 0, 'foreign_ns': 0, 'idle_ns': 0,
                          'owned_outside_allowed_ns': 0} for cpu in sorted(cpus)}
    by_tid = defaultdict(list)
    for cpu in sorted(cpus):
        rows = grouped[cpu]
        if len(rows) < 2 or rows[0]['timestamp_ns'] > begin_ns or rows[-1]['timestamp_ns'] < end_ns:
            raise ValueError('window not bracketed')
        for previous, current in zip(rows, rows[1:]):
            if previous['timestamp_ns'] >= current['timestamp_ns']:
                raise ValueError('nonmonotonic switch timestamps')
            if previous['next_tid'] != current['prev_tid']:
                raise ValueError('switch chain discontinuity')
            left, right = max(begin_ns, previous['timestamp_ns']), min(end_ns, current['timestamp_ns'])
            if left >= right:
                continue
            tid = previous['next_tid']
            category = 'idle' if tid == 0 else ('owned' if tid in allowed_by_tid else 'foreign')
            outside = category == 'owned' and cpu not in allowed_by_tid[tid]
            segment = {'cpu': cpu, 'begin_ns': left, 'end_ns': right,
                       'tid': tid, 'category': category, 'outside_allowed': outside}
            intervals.append(segment)
            summary[str(cpu)][category + '_ns'] += right - left
            if outside:
                summary[str(cpu)]['owned_outside_allowed_ns'] += right - left
            if tid:
                by_tid[tid].append(segment)
        totals = summary[str(cpu)]
        if sum(totals[k] for k in ('owned_ns', 'foreign_ns', 'idle_ns')) != end_ns - begin_ns:
            raise ValueError('incomplete projection')
    for runs in by_tid.values():
        runs.sort(key=lambda x: (x['begin_ns'], x['end_ns']))
        if any(a['end_ns'] > b['begin_ns'] for a, b in zip(runs, runs[1:])):
            raise ValueError('overlapping same-TID intervals')
    return {'status': 'observed-only', 'intervals': intervals, 'by_cpu_ns': summary,
            'coverage': 'unknown', 'loss': 'unknown', 'placement': 'unproven',
            'contention': 'unproven', 'measurement_admission': 'none'}

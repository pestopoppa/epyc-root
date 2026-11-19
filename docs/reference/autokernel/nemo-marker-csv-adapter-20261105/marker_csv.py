"""Fail-closed adapter for 0.5-documented rocprof marker CSV; native 0.4 unverified.

Documented example: https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/docs-6.3.0/how-to/using-rocprofv3.html#marker-trace
Marker points must have zero duration. Their profiler time is *not* assumed to
be CLOCK_MONOTONIC; match it with the host brackets using verify.validate.
"""
import csv

PREFIX = 'NEMO_BOUNDARY_FIXTURE_V1_TWO_KERNEL_GRAPH:clock_sync:'
HEADERS = ('Domain', 'Function', 'Process_Id', 'Thread_Id', 'Correlation_Id', 'Start_Timestamp', 'End_Timestamp')

def normalize(path):
    with open(path, newline='') as f:
        reader = csv.DictReader(f, restkey='__extra__', restval=None)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError('unrecognized marker CSV schema')
        markers = []
        for row in reader:
            if '__extra__' in row or any(row.get(h) is None for h in HEADERS):
                raise ValueError('malformed marker CSV row')
            name = row['Function']
            if not name.startswith(PREFIX):
                continue
            if name not in (PREFIX+'0', PREFIX+'1') or row['Domain'] != 'MARKER_CORE_API':
                raise ValueError('unexpected clock marker')
            try:
                pid, tid, corr, start, end = (int(row[k]) for k in HEADERS[2:])
            except ValueError as e:
                raise ValueError('invalid numeric marker field') from e
            if min(pid,tid,corr,start) <= 0 or end != start:
                raise ValueError('invalid marker identity or nonpoint timestamp')
            markers.append({'marker': name, 'pid':pid, 'tid':tid, 'timestamp_ns':start})
    if len(markers) != 2 or {m['marker'] for m in markers} != {PREFIX+'0', PREFIX+'1'}:
        raise ValueError('missing or duplicate clock marker')
    return sorted(markers, key=lambda x: x['marker'])

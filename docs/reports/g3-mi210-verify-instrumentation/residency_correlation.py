"""Conservative time-window join; V3 trace does not supply required timestamps.

Call only with independently verified native timestamps on the same clock as
samples. A time-window match does not establish per-PID VRAM attribution or
simultaneous collection of each witness.
"""
from residency_evidence import analyze_residency


def correlate_residency(*, calls, samples, baseline, card, pid, backend, expected_sha256):
    output = []
    for call in calls:
        result = {'invocation': call.get('invocation'), 'status': 'UNKNOWN', 'matches': []}
        try:
            begin, dispatch, end = call['native_begin'], call['native_dispatch'], call['native_end']
            if any(type(x) not in (int, float) for x in (begin, dispatch, end)) or not begin < dispatch < end:
                raise ValueError('invalid native timing')
        except (KeyError, ValueError):
            result['reason'] = 'missing or invalid native timing; V3 does not provide native timestamps'
            output.append(result)
            continue
        for sample in samples:
            sample_start, sample_end = sample.get('observation_start'), sample.get('observation_end')
            if (type(sample_start) not in (int, float) or type(sample_end) not in (int, float)
                    or not begin <= sample_start <= dispatch <= sample_end <= end):
                continue
            evidence = analyze_residency(baseline=baseline, samples=[sample], card=card,
                                         pid=pid, backend=backend, expected_sha256=expected_sha256,
                                         start=begin, end=end)
            if evidence['status'] == 'PASS':
                result['matches'].append({'observation_start': sample_start, 'observation_end': sample_end,
                                          'native_dispatch': dispatch, 'residency': evidence})
        if result['matches']:
            result['status'] = 'BOUNDED_OBSERVATION'
            result['reason'] = 'dispatch falls inside collection interval; witnesses were sampled sequentially'
        else:
            result['reason'] = 'no qualifying complete observation enclosing dispatch inside invocation'
        output.append(result)
    return output

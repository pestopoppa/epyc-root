"""Independent consistency check for retained CH-26 perf source receipts.

This verifies only internal census and counter consistency. It cannot validate
kernel coverage/loss semantics or establish placement or contention.
"""
EVENTS = frozenset(('sched_switch', 'irq_handler_entry', 'irq_handler_exit',
                    'softirq_entry', 'softirq_exit'))

def validate(doc, cpus):
    if not isinstance(doc, dict) or not isinstance(cpus, (set, frozenset)) or not cpus or any(type(c) is not int or c < 0 for c in cpus):
        raise ValueError('invalid document or expected CPU set')
    if doc.get('errors') != [] or doc.get('status') != 'unproven' or doc.get('coverage') != 'unknown' or doc.get('loss') != 'unknown' or doc.get('measurement_admission') != 'none':
        raise ValueError('capture error or overstated scope')
    markers = doc.get('markers')
    if not isinstance(markers, list) or len(markers) != 2:
        raise ValueError('marker pair missing')
    try:
        begin, end = (x['timestamp_ns'] for x in markers)
        if any(type(x) is not int for x in (begin,end)) or not 0 < begin < end:
            raise ValueError('invalid request interval')
        if [(x['kind'],x['seq']) for x in markers] != [('begin',1),('end',2)]:
            raise ValueError('invalid marker order')
        provenance, rings = doc['source_provenance'], doc['rings']
        if not isinstance(provenance,list) or not isinstance(rings,list):
            raise ValueError('source records missing')
        expected = {(cpu, event) for cpu in cpus for event in EVENTS}
        sources = {}
        event_ids = set()
        for p in provenance:
            key = (p['cpu'], p['name']); eid = p['event_id']
            if key not in expected or key in sources or type(eid) is not int or eid <= 0 or eid in event_ids:
                raise ValueError('duplicate, unexpected or invalid source')
            sources[key] = eid; event_ids.add(eid)
        if set(sources) != expected:
            raise ValueError('incomplete source census')
        seen = set()
        for ring in rings:
            key = (ring['cpu'],ring['name'])
            if key not in sources or key in seen or ring['event_id'] != sources[key]:
                raise ValueError('unmatched or duplicate final counter')
            seen.add(key)
            bounds = [ring[k] for k in ('enable_before_ns','enable_after_ns','disable_before_ns','disable_after_ns')]
            if any(type(x) is not int for x in bounds) or not 0 < bounds[0] <= bounds[1] <= begin < end <= bounds[2] <= bounds[3]:
                raise ValueError('event enable bounds do not contain request')
            enabled, running, lost, count = (ring[k] for k in ('enabled_ns','running_ns','lost_samples','count'))
            if any(type(x) is not int for x in (enabled,running,lost,count)) or enabled <= 0 or running != enabled or lost != 0 or count < 0:
                raise ValueError('counter invalid, multiplexed or lost')
            if ring.get('errors') != [] or not isinstance(ring.get('ring'),dict) or ring['ring'].get('errors') != []:
                raise ValueError('ring errors or missing ring')
        if seen != expected:
            raise ValueError('missing final counter')
    except (KeyError, TypeError) as exc:
        raise ValueError('malformed retained source evidence') from exc
    return {'status':'internally-consistent', 'sources':len(expected), 'cpus':len(cpus),
            'coverage':'unknown', 'loss':'unknown', 'placement':'unproven',
            'contention':'unproven', 'measurement_admission':'none'}

"""Synthetic, fail-closed task/row binding contract; not a native observer."""

class Unknown(ValueError):
    """Capture incomplete or ambiguous; never treat as a match."""


def bind_capture(request, begin, capture, end):
    """Require corroborated, monotonic identity and exactly one target row.

    Each object is a future observer input, not an attestation of its source.
    Real server integration must independently establish event provenance, capture
    completeness, timestamp ordering, actual ABI and exact task/slot identities.
    """
    keys = ('run_id', 'pid', 'birth', 'request_id', 'task_id', 'slot')
    try:
        events = (request, begin, capture, end)
        if any(not isinstance(x, dict) for x in events):
            raise Unknown('missing event')
        for key in keys:
            v = request[key]
            if key in ('pid', 'birth', 'task_id', 'slot'):
                if type(v) is not int or v < (1 if key in ('pid', 'birth') else 0):
                    raise Unknown('invalid identity')
            elif not isinstance(v, str) or not v:
                raise Unknown('invalid identity')
            if any(e[key] != v or type(e[key]) is not type(v) for e in events[1:]):
                raise Unknown('identity mismatch')
        seqs = [e['event_seq'] for e in events]
        if any(type(n) is not int or n < 0 for n in seqs) or not all(a < b for a, b in zip(seqs, seqs[1:])):
            raise Unknown('event ordering')
        if begin['complete_stream'] is not True or end['complete_stream'] is not True:
            raise Unknown('unproved event stream completeness')
        if end['outcome'] != 'completed' or capture['kind'] != 'decode_boundary':
            raise Unknown('incomplete operation')
        rows = capture['rows']
        if not isinstance(rows, list) or not rows:
            raise Unknown('missing batch rows')
        if any(not isinstance(row, dict) or type(row.get('index')) is not int or row['index'] < 0
               or type(row.get('task_id')) is not int or row['task_id'] < 0
               or type(row.get('slot')) is not int or row['slot'] < 0 for row in rows):
            raise Unknown('invalid row')
        if len({row['index'] for row in rows}) != len(rows):
            raise Unknown('duplicate row index')
        matches = [row for row in rows if row['task_id'] == request['task_id'] and row['slot'] == request['slot']]
        if len(matches) != 1:
            raise Unknown('target row ambiguous or absent')
        # A slot or task attributed simultaneously to another identity cannot be disambiguated.
        if any((r['task_id'] == request['task_id'] or r['slot'] == request['slot']) and r is not matches[0] for r in rows):
            raise Unknown('conflicting task or slot')
        return matches[0]['index']
    except (KeyError, TypeError):
        raise Unknown('missing binding field') from None

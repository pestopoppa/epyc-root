"""Check raw tracepoint common_type against the owner-open receipt.

This is structural source binding only: a matching common_type does not prove
that the FD attributes or tracepoint format came from a trusted kernel, or that
all events were delivered. It assumes the host's native perf sample encoding.
"""
import struct
import sys
from perf_ring import decode


def check(ring, *, cpu, event_id, tracepoint_id):
    if type(cpu) is not int or cpu < 0 or type(event_id) is not int or event_id <= 0:
        raise ValueError('invalid CPU or perf event ID')
    if type(tracepoint_id) is not int or not 0 < tracepoint_id <= 65535:
        raise ValueError('invalid tracepoint ID')
    if sys.byteorder != 'little':
        raise ValueError('unsupported host perf byte order')
    if not isinstance(ring, dict) or ring.get('errors') != []:
        raise ValueError('invalid source ring or reported errors')
    parsed = decode(ring.get('snapshot'), head=ring.get('head'), tail=ring.get('tail'))
    if parsed.get('errors'):
        raise ValueError('malformed or lost source ring')
    count = 0
    for event in parsed['events']:
        if event.get('type') != 'sample':
            raise ValueError('unexpected source record')
        body = event['body']
        if len(body) < 54:
            raise ValueError('missing common_type')
        ident, _, _, _, stamp, observed_cpu, reserved, period, rawsize = struct.unpack_from('=QQIIQIIQI',body)
        if ident != event_id or observed_cpu != cpu or reserved != 0 or stamp == 0 or period != 1:
            raise ValueError('sample source identity, period or time mismatch')
        if rawsize < 2 or rawsize > len(body) - 52:
            raise ValueError('invalid tracepoint raw size')
        if struct.unpack_from('=H',body,52)[0] != tracepoint_id:
            raise ValueError('tracepoint common_type does not match open receipt')
        count += 1
    return count

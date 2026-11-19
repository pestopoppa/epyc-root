"""Integration boundary for prospective typed KPF-50 window receipts.

The caller must supply independently produced evidence files. This adapter
does not manufacture cleanup, clock, trace, or scientific assertions.
"""
from receipt import KEYS, ORDER, publish
from cleanup_receipt import Guard


def publish_window(directory, index, lineage, fan_finished, stop_record, cleanup_guard=None):
    if type(index) is not int or not 0 <= index < len(ORDER):
        raise ValueError('invalid window index')
    if fan_finished is not True:
        raise ValueError('fan request sequence incomplete')
    if not isinstance(stop_record, dict) or stop_record.get('verified_dead') is not True:
        raise ValueError('server stop is not verified')
    window = ORDER[index]
    # Require a same-process guard that captured and itself reaped this exact
    # server. An externally supplied JSON or server-only stop is insufficient.
    if type(cleanup_guard) is not Guard:
        raise ValueError('same-process subreaper guard missing')
    pid, ticks = stop_record.get('pid'), stop_record.get('birth_ticks')
    captured = cleanup_guard.captured.get(pid)
    if (type(pid) is not int or type(ticks) is not int or not captured or
        captured.get('birth_ticks') != ticks or captured.get('reaped') is not True):
        raise ValueError('server was not captured and reaped by cleanup guard')
    cleanup_guard.publish(directory, window, lineage)
    files = {key: f'{window}.{key}.json' for key in KEYS}
    return publish(directory, window, lineage, files)

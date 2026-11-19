"""Integration boundary for prospective typed KPF-50 window receipts.

The caller must supply independently produced evidence files. This adapter
does not manufacture cleanup, clock, trace, or scientific assertions.
"""
from receipt import KEYS, ORDER, publish


def publish_window(directory, index, lineage, fan_finished, stop_record):
    if type(index) is not int or not 0 <= index < len(ORDER):
        raise ValueError('invalid window index')
    if fan_finished is not True:
        raise ValueError('fan request sequence incomplete')
    if not isinstance(stop_record, dict) or stop_record.get('verified_dead') is not True:
        raise ValueError('server stop is not verified')
    window = ORDER[index]
    files = {key: f'{window}.{key}.json' for key in KEYS}
    return publish(directory, window, lineage, files)

#!/usr/bin/env python3
"""Match native tensor loads within the mapped serving phase."""
import re

import capture_base as native

LOG_TIME = rb'[0-9]+\.[0-9]{2}\.[0-9]{3}\.[0-9]{3}'
LOAD_START = re.compile(LOG_TIME + rb' I load_tensors: loading model tensors, this can take a while\.\.\. '
                        rb'\(mmap = (true|false), direct_io = (true|false)\)')
CONTEXT_START = re.compile(LOG_TIME + rb' I llama_context: constructing llama_context')


def loader_log_evidence(path, plan, arm):
    raw = path.read_bytes()
    log = raw.split(b'\n')
    starts = {index: match.groups() for index, line in enumerate(log)
              if (match := LOAD_START.fullmatch(line))}
    mapped = [index for index, (mmap, _) in starts.items() if mmap == b'true']
    if len(mapped) != 1:
        raise ValueError(f'{arm} requires one native mmap=true load phase, found {len(mapped)}')
    start, = mapped
    if starts[start] != (b'true', b'false'):
        raise ValueError(f'{arm} native load phase uses unexpected direct I/O')
    end = next((index for index in range(start + 1, len(log)) if CONTEXT_START.fullmatch(log[index])), None)
    if end is None or any(start < index < end for index in starts):
        raise ValueError(f'{arm} native mmap=true load phase lacks an unambiguous context boundary')

    lines, line_numbers = {}, {}
    for name in plan['loader_witness']['tensors']:
        pattern = re.compile(LOG_TIME + rb' D create_tensor: loading tensor ' + re.escape(name.encode('ascii')))
        found = [index for index in range(start + 1, end) if pattern.fullmatch(log[index])]
        if len(found) != 1:
            raise ValueError(f'{arm} requires one native mmap=true load line for {name}, found {len(found)}')
        index, = found
        lines[name], line_numbers[name] = log[index].decode('ascii'), index + 1
    return {
        'native_lines': lines, 'native_line_numbers': line_numbers, 'log_sha256': native.sha(raw),
        'native_load_phase': {
            'start': {'line': log[start].decode('ascii'), 'line_number': start + 1},
            'context_start': {'line': log[end].decode('ascii'), 'line_number': end + 1},
        },
        'stored_dims': plan['loader_witness']['stored_dims'],
        'runtime_dims_from_pinned_source': plan['loader_witness'][f'{arm}_dims'],
    }



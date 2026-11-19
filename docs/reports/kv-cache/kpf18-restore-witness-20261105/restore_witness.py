"""Strict parser for a1f0c8cf9's native SLT_TRC restore line.

Caller must independently bind task_id to the HTTP request. An offset or a
guessed most-recent task is not a binding. This is not a layout witness.
"""
import re
_RE = re.compile(r'slot\s+\S+: id\s+(?P<slot>\d+) \| task\s+(?P<task>\d+) \| restored context checkpoint \(pos_min = (?P<min>-?\d+), pos_max = (?P<max>-?\d+), n_tokens = (?P<tokens>\d+), n_past = (?P<past>\d+), size = [0-9.]+ MiB\)')
_HEADER = re.compile(r'slot[ \t]+\S+: id[ \t]+(?P<slot>\d+) \| task[ \t]+(?P<task>\d+) \| restored context checkpoint')
_SIZE = re.compile(r'\d+(?:\.\d+)?')

def attest(log_text: str, *, task_id: int, slot: int, n_tokens: int) -> dict:
    if type(task_id) is not int or task_id < 0 or type(slot) is not int or slot < 0 or type(n_tokens) is not int or n_tokens < 1:
        raise ValueError('independently bound task and slot and positive token count required')
    own = []
    # Count attributed restore lines before parsing their payload. Otherwise a
    # truncated/malformed second event silently disappears from ambiguity checks.
    for line in log_text.splitlines():
        for header in _HEADER.finditer(line):
            if int(header['slot']) != slot or int(header['task']) != task_id:
                continue
            payload = line[header.start():].rstrip()
            match = _RE.fullmatch(payload)
            size = payload.rsplit('size = ', 1)[-1].removesuffix(' MiB)')
            if match is None or _SIZE.fullmatch(size) is None:
                raise ValueError('malformed restore for request')
            own.append({k: int(v) for k, v in match.groupdict().items()})
    if len(own) != 1:
        raise ValueError('missing or ambiguous restore for request')
    event = own[0]
    if (event['tokens'] != n_tokens or not 0 <= event['past'] <= n_tokens
            or event['max'] + 1 != n_tokens
            or not 0 <= event['min'] <= event['max']):
        raise ValueError('checkpoint identity or past count mismatch')
    return event

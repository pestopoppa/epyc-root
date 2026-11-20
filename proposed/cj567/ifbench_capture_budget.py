"""Explicit wall budget for prospective IFBench capture; no retry or score policy."""
import math
import urllib.request

# A conservative planning floor, not a measured throughput guarantee.
MIN_TOKENS_PER_SECOND = 0.5
PREFILL_SECONDS = 120
CLEANUP_SECONDS = 30


def request_seconds(max_tokens):
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError('max_tokens must be a positive integer')
    return PREFILL_SECONDS + math.ceil(max_tokens / MIN_TOKENS_PER_SECOND)


def can_expose(now, deadline, timeout):
    """Reserve the entire request and cleanup window before creating exposure."""
    return now + timeout + CLEANUP_SECONDS < deadline


def capture_response(url, payload, timeout, *, opener=None):
    """One non-streaming request; failures propagate without retrying."""
    import json
    request = urllib.request.Request(
        url + '/v1/chat/completions', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with (opener or urllib.request.urlopen)(request, timeout=timeout) as response:
        return response.status, response.read()

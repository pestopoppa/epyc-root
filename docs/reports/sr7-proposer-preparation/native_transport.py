"""Single-shot localhost transport for a future SR-7 admitted worker.

The caller must prove port ownership and server identity for the whole request,
record exposure before invoking this function, enforce the grant deadline, and
capture/terminate the server. This transport does not provide these guarantees.
"""
import http.client
import json

MAX_REPLY = 8 * 1024 * 1024


def post_completion(port, payload, timeout_s):
    """POST exactly once to native /completion; return status and raw bytes.

    Non-200 replies remain raw evidence. Redirects are not followed; callers
    must abandon the exposed prompt on any error and must never retry it.
    """
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid port')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 3600:
        raise ValueError('invalid timeout')
    if not isinstance(payload, dict) or not isinstance(payload.get('prompt'), str) or not payload['prompt']:
        raise ValueError('rendered prompt required')
    if payload.get('cache_prompt') is not False or payload.get('stream') is not False:
        raise ValueError('uncached non-streaming request required')
    if type(payload.get('n_predict')) is not int or payload['n_predict'] <= 0:
        raise ValueError('positive n_predict required')
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout_s)
    try:
        conn.request('POST', '/completion', body=body, headers={'Content-Type': 'application/json', 'Connection': 'close'})
        response = conn.getresponse()
        raw = response.read(MAX_REPLY + 1)
        if len(raw) > MAX_REPLY:
            raise ValueError('reply exceeds capture limit')
        if response.length is not None and response.length != 0:
            raise ValueError('response ended before declared content length')
        return response.status, raw
    finally:
        conn.close()

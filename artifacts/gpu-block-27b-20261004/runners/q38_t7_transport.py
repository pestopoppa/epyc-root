"""Strict HTTP/SSE transport for the isolated Q38 successor.

The caller supplies a custody-bound loopback URL and tokenizer function. This
module does not establish process ownership, ggml linkage or tokenizer identity;
the supervisor and tokenizer attestor must do so independently.
"""

import hashlib
import json
import time
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def parse_sse(raw: bytes) -> dict:
    """Parse retained OpenAI chat SSE; reject malformed or incomplete streams."""
    text = raw.decode('utf-8', errors='strict')
    content, reasoning, finish, timings, done = [], [], None, None, False
    payloads = []
    for line in text.splitlines():
        if not line:
            if not payloads:
                continue
            payload = '\n'.join(payloads); payloads = []
            if done:
                raise ValueError('event after DONE')
            if payload == '[DONE]':
                done = True
                continue
            event = json.loads(payload)
            if not isinstance(event, dict) or event.get('error'):
                raise ValueError('invalid or error SSE event')
            if 'timings' in event:
                if not isinstance(event['timings'], dict):
                    raise ValueError('invalid stream timings')
                timings = event['timings']
            choices = event.get('choices') or []
            if not isinstance(choices, list):
                raise ValueError('invalid stream choices')
            for choice in choices:
                if not isinstance(choice, dict) or choice.get('index', 0) != 0:
                    raise ValueError('unexpected stream choice')
                delta = choice.get('delta') or {}
                if not isinstance(delta, dict):
                    raise ValueError('invalid delta')
                for field, target in (('content', content), ('reasoning_content', reasoning)):
                    value = delta.get(field)
                    if value is not None:
                        if not isinstance(value, str):
                            raise ValueError('invalid delta text')
                        target.append(value)
                if choice.get('finish_reason') is not None:
                    finish = choice['finish_reason']
        elif line.startswith('data:'):
            payloads.append(line[5:].lstrip(' '))
        elif not line.startswith(':'):
            raise ValueError('unexpected SSE field')
    if payloads or not done or not isinstance(finish, str) or timings is None:
        raise ValueError('incomplete SSE termination or timings')
    return {'content': ''.join(content), 'reasoning': ''.join(reasoning),
            'finish': finish, 'timings': timings}


class HttpTransport:
    def __init__(self, base_url, tokenize=None, *, timeout=900, max_response_bytes=64 * 1024 * 1024):
        self.base_url, self.tokenize = base_url, tokenize
        self.timeout, self.max_response_bytes = timeout, max_response_bytes

    def send(self, handle, body):
        base = self.base_url(handle)
        if not isinstance(base, str):
            raise ValueError('explicit loopback transport required')
        parsed = urlsplit(base)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port is None
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError('explicit loopback transport required')
        base = base.rstrip('/')
        payload = json.dumps(body, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode()
        request = Request(base + '/v1/chat/completions', data=payload,
                          headers={'Content-Type': 'application/json'})
        t0 = time.monotonic(); ttfb = None; ttft = None; chunks = []; event_lines = []
        with urlopen(request, timeout=self.timeout) as response:
            total = 0
            while True:
                chunk = response.readline() if body.get('stream') else response.read(65536)
                if not chunk:
                    break
                if ttfb is None:
                    ttfb = time.monotonic() - t0
                total += len(chunk)
                if total > self.max_response_bytes:
                    raise ValueError('response exceeds custody limit')
                chunks.append(chunk)
                if body.get('stream') and ttft is None:
                    if chunk.strip():
                        event_lines.append(chunk)
                    elif event_lines:
                        try:
                            data = b'\n'.join(line[5:].strip() for line in event_lines
                                              if line.startswith(b'data:'))
                            event = json.loads(data)
                            choices = event.get('choices') or []
                            if any((choice.get('delta') or {}).get('content')
                                   or (choice.get('delta') or {}).get('reasoning_content')
                                   for choice in choices):
                                ttft = time.monotonic() - t0
                        except (ValueError, TypeError, AttributeError):
                            pass  # strict whole-stream validation follows
                        event_lines = []
            raw = b''.join(chunks)
            result = {'http_status': response.status, 'wall_s': time.monotonic() - t0}
        if body.get('stream'):
            raw_hash = hashlib.sha256(raw).hexdigest()
            try:
                fields = parse_sse(raw)
                result.update(fields, stream_complete=True, raw_stream=raw.decode('utf-8'),
                              raw_stream_sha256=raw_hash, ttfb_s=ttfb, ttft_s=ttft)
            except (ValueError, UnicodeDecodeError) as exc:
                import base64
                result.update(error=f'invalid_stream: {exc}', stream_complete=False,
                              raw_stream_base64=base64.b64encode(raw).decode(),
                              raw_stream_sha256=raw_hash, ttfb_s=ttfb, ttft_s=ttft)
                return result
            text = fields['reasoning'] + '\n' + fields['content']
        else:
            decoded = json.loads(raw)
            result.update(body=decoded, raw_body=raw.decode('utf-8'),
                          raw_body_sha256=hashlib.sha256(raw).hexdigest(),
                          timings=decoded.get('timings') if isinstance(decoded, dict) else None)
            choices = decoded.get('choices') if isinstance(decoded, dict) else None
            message = choices[0].get('message') if isinstance(choices, list) and len(choices) == 1 else None
            text = message.get('content') if isinstance(message, dict) else None
        if isinstance(text, str) and self.tokenize is not None:
            proof = self.tokenize(handle, text)
            if not isinstance(proof, dict):
                raise ValueError('tokenizer proof missing')
            result['token_ids'] = proof.get('token_ids')
            result['tokenizer_provenance'] = {k: proof.get(k) for k in
                                              ('method', 'text_sha256', 'tokenizer_sha256', 'token_ids_sha256')}
        return result

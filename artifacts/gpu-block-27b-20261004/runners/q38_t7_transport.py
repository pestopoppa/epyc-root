"""Strict HTTP/SSE transport for the isolated Q38 successor.

The caller supplies a custody-bound loopback URL and tokenizer function. This
module does not establish process ownership, ggml linkage or tokenizer identity;
the supervisor and tokenizer attestor must do so independently.
"""

import hashlib
import json
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError('redirects are not permitted')


def _local_url(base):
    if not isinstance(base, str):
        raise ValueError('explicit loopback transport required')
    parsed = urlsplit(base)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port is None
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('explicit loopback transport required')
    return base.rstrip('/')


def _bound_url(supervisor, handle):
    """Derive the URL from the captured child's exact recipe and verify owner."""
    from q38_t7_native_verify import NativeIdentityVerifier
    if not isinstance(getattr(supervisor, 'identity_verifier', None), NativeIdentityVerifier):
        raise ValueError('native identity verifier required')
    if supervisor.verify(handle, handle.arm, handle.recipe) is not True:
        raise ValueError('captured server identity unverified')
    args = handle.argv
    def single(flag):
        positions = [i for i, value in enumerate(args) if value == flag]
        if len(positions) != 1 or positions[0] + 1 >= len(args):
            raise ValueError(f'exactly one explicit {flag} is required')
        return args[positions[0] + 1]
    host, port = single('--host'), single('--port')
    if host != '127.0.0.1' or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError('invalid bound listener')
    verifier = supervisor.identity_verifier
    if verifier.host != host or verifier.port != int(port):
        raise ValueError('listener differs from native identity verifier')
    return f'http://{host}:{int(port)}'


class NativeTokenizerAttestor:
    """Call the captured server's tokenizer with exact response text.

    The native model/tokenizer verifier must return a task-bound receipt with
    pid, birth, model and tokenizer digests and a retained evidence digest.
    Paths or the caller's declared digest alone are not such a receipt.
    """
    def __init__(self, supervisor, tokenizer_sha256, model_tokenizer_verifier, *, timeout=300):
        if not callable(model_tokenizer_verifier):
            raise ValueError('native model/tokenizer verifier required')
        self.supervisor, self.tokenizer_sha256 = supervisor, tokenizer_sha256
        self.model_tokenizer_verifier, self.timeout = model_tokenizer_verifier, timeout
        self.opener = build_opener(_NoRedirect())
        self.stop = lambda: False

    def __call__(self, handle, text):
        import re
        if _stopping(self.stop):
            raise ValueError('STOP before tokenizer request')
        if not isinstance(text, str) or not isinstance(self.tokenizer_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', self.tokenizer_sha256):
            raise ValueError('text and pinned tokenizer digest required')
        base = _bound_url(self.supervisor, handle)
        def identity():
            proof = self.model_tokenizer_verifier(handle)
            if (not isinstance(proof, dict) or proof.get('pid') != handle.process.pid
                    or proof.get('birth') != handle.birth
                    or proof.get('model_sha256') != handle.recipe['shape']['model_sha256']
                    or proof.get('tokenizer_sha256') != self.tokenizer_sha256
                    or not isinstance(proof.get('evidence_sha256'), str)
                    or not re.fullmatch(r'[0-9a-f]{64}', proof['evidence_sha256'])):
                raise ValueError('native model/tokenizer identity missing')
            return proof
        before = identity()
        raw_body = json.dumps({'content': text}, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=False).encode()
        request = Request(base + '/tokenize', data=raw_body, headers={'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=self.timeout) as response:
            if response.status != 200:
                raise ValueError('native tokenizer request failed')
            raw = response.read(16 * 1024 * 1024 + 1)
        if _stopping(self.stop):
            raise ValueError('STOP during tokenizer request')
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('tokenizer response exceeds limit')
        data = json.loads(raw)
        tokens = data.get('tokens') if isinstance(data, dict) else None
        if not isinstance(tokens, list) or any(type(token) is not int for token in tokens):
            raise ValueError('invalid native tokenizer response')
        if _bound_url(self.supervisor, handle) != base or identity() != before:
            raise ValueError('native tokenizer identity changed')
        return {'token_ids': tokens, 'method': 'retokenized_text',
                'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'tokenizer_sha256': self.tokenizer_sha256,
                'token_ids_sha256': hashlib.sha256(json.dumps(tokens, separators=(',', ':')).encode()).hexdigest(),
                'model_sha256': before['model_sha256'], 'identity_evidence_sha256': before['evidence_sha256'],
                'pid': before['pid'], 'birth': before['birth'], 'server_url': base,
                'tokenizer_response': raw.decode('utf-8'),
                'tokenizer_response_sha256': hashlib.sha256(raw).hexdigest()}


class OwnedHttpTransport:
    """Require native owner verification before and after transport and tokenization."""
    def __init__(self, supervisor, tokenizer_sha256, model_tokenizer_verifier, *, timeout=900):
        self.supervisor = supervisor
        self.tokenizer = NativeTokenizerAttestor(supervisor, tokenizer_sha256, model_tokenizer_verifier)
        self.transport = HttpTransport(lambda h: _bound_url(supervisor, h), self.tokenizer, timeout=timeout)

    def bind_stop(self, callback):
        self.transport.stop = callback
        self.tokenizer.stop = callback

    def send(self, handle, body):
        before = _bound_url(self.supervisor, handle)
        response = self.transport.send(handle, body)
        try:
            if _bound_url(self.supervisor, handle) != before:
                raise ValueError('server identity changed during request')
        except Exception as exc:
            # Preserve already received native bytes for the journal. The
            # coordinator will fail closed on this typed error.
            response['error'] = f'ownership verification failed: {type(exc).__name__}: {exc}'
        return response


def _stopping(callback):
    try:
        return bool(callback())
    except Exception:
        return True


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
        self.opener = build_opener(_NoRedirect())
        self.stop = lambda: False

    def send(self, handle, body):
        base = _local_url(self.base_url(handle))
        payload = json.dumps(body, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode()
        if _stopping(self.stop):
            raise ValueError('STOP before HTTP dispatch')
        request = Request(base + '/v1/chat/completions', data=payload,
                          headers={'Content-Type': 'application/json'})
        t0 = time.monotonic(); ttfb = None; ttft = None; chunks = []; event_lines = []; stopped = False
        with self.opener.open(request, timeout=self.timeout) as response:
            total = 0
            while True:
                if _stopping(self.stop):
                    stopped = True
                    break
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
        if stopped or _stopping(self.stop):
            import base64
            result.update(error='STOP during HTTP response', response_partial=True,
                          raw_partial_base64=base64.b64encode(raw).decode(),
                          raw_partial_sha256=hashlib.sha256(raw).hexdigest(),
                          ttfb_s=ttfb, ttft_s=ttft)
            return result
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
            try:
                proof = self.tokenize(handle, text)
                if not isinstance(proof, dict):
                    raise ValueError('tokenizer proof missing')
                result['token_ids'] = proof.get('token_ids')
                result['tokenizer_provenance'] = {k: v for k, v in proof.items() if k != 'token_ids'}
            except Exception as exc:
                # Keep the original response for durable partial-run custody.
                result['error'] = f'tokenizer attestation failed: {type(exc).__name__}: {exc}'
        return result

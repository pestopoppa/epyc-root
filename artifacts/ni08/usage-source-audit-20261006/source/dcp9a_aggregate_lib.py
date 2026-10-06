"""Allowlisted JSONL field reader. Content strings are syntax-scanned, never sliced or decoded."""
import json
import re

class Bad(Exception):
    pass

_NUMBER = re.compile(rb'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')
_HEX = frozenset(b'0123456789abcdefABCDEF')
_ESC = frozenset(b'"\\/bfnrt')

class P:
    def __init__(self, b):
        self.b = b
        self.i = 0
        self.n = len(b)

    def ws(self):
        while self.i < self.n and self.b[self.i] in b' \t\r\n':
            self.i += 1

    def string(self, capture=False, limit=4096, overflow_ok=False):
        b, i, n = self.b, self.i, self.n
        if i >= n or b[i] != 34:
            raise Bad()
        i += 1
        start = i
        captured = bytearray() if capture else None
        while i < n:
            c = b[i]
            if c == 34:
                end = i
                self.i = i + 1
                if not capture:
                    return None
                if end - start > limit:
                    if overflow_ok:
                        return None
                    raise Bad()
                raw = bytes(b[start:end])
                try:
                    return json.loads((b'"' + raw + b'"').decode())
                except Exception:
                    raise Bad()
            if c == 92:
                if i + 1 >= n:
                    raise Bad()
                e = b[i + 1]
                if e in _ESC:
                    i += 2
                elif e == 117:
                    if i + 5 >= n or any(x not in _HEX for x in b[i + 2:i + 6]):
                        raise Bad()
                    i += 6
                else:
                    raise Bad()
                continue
            if c < 32:
                raise Bad()
            i += 1
        raise Bad()

    def primitive(self, capture=False):
        self.ws()
        start = self.i
        while self.i < self.n and self.b[self.i] not in b',]} \t\r\n':
            self.i += 1
        end = self.i
        b = self.b
        def equals(literal):
            return end - start == len(literal) and all(b[start + j] == literal[j] for j in range(len(literal)))
        if equals(b'true') or equals(b'false') or equals(b'null'):
            return bytes(b[start:end]) if capture else None
        i = start
        if i < end and b[i] == 45:
            i += 1
        if i >= end:
            raise Bad()
        if b[i] == 48:
            i += 1
            if i < end and 48 <= b[i] <= 57:
                raise Bad()
        elif 49 <= b[i] <= 57:
            i += 1
            while i < end and 48 <= b[i] <= 57:
                i += 1
        else:
            raise Bad()
        if i < end and b[i] == 46:
            i += 1
            first = i
            while i < end and 48 <= b[i] <= 57:
                i += 1
            if i == first:
                raise Bad()
        if i < end and b[i] in b'eE':
            i += 1
            if i < end and b[i] in b'+-':
                i += 1
            first = i
            while i < end and 48 <= b[i] <= 57:
                i += 1
            if i == first:
                raise Bad()
        if i != end:
            raise Bad()
        if capture:
            if end - start > 128:
                raise Bad()
            return bytes(b[start:end])
        return None

    def skip(self):
        self.ws()
        if self.i >= self.n:
            raise Bad()
        c = self.b[self.i]
        if c == 34:
            self.string(capture=False)
            return
        if c == 123:
            self.i += 1
            self.ws()
            if self.i < self.n and self.b[self.i] == 125:
                self.i += 1
                return
            while True:
                self.ws()
                self.string(capture=False)
                self.ws()
                if self.i >= self.n or self.b[self.i] != 58:
                    raise Bad()
                self.i += 1
                self.skip()
                self.ws()
                if self.i >= self.n:
                    raise Bad()
                if self.b[self.i] == 125:
                    self.i += 1
                    return
                if self.b[self.i] != 44:
                    raise Bad()
                self.i += 1
        if c == 91:
            self.i += 1
            self.ws()
            if self.i < self.n and self.b[self.i] == 93:
                self.i += 1
                return
            while True:
                self.skip()
                self.ws()
                if self.i >= self.n:
                    raise Bad()
                if self.b[self.i] == 93:
                    self.i += 1
                    return
                if self.b[self.i] != 44:
                    raise Bad()
                self.i += 1
        self.primitive()

    def scalar(self):
        self.ws()
        if self.i >= self.n:
            raise Bad()
        if self.b[self.i] == 34:
            return self.string(capture=True)
        token = self.primitive(capture=True)
        if token == b'null':
            return None
        if token == b'true':
            return True
        if token == b'false':
            return False
        if b'.' in token or b'e' in token.lower():
            return float(token)
        return int(token)

    def obj(self, kind):
        self.ws()
        if self.i >= self.n or self.b[self.i] != 123:
            raise Bad()
        self.i += 1
        self.ws()
        out = {}
        if self.i < self.n and self.b[self.i] == 125:
            self.i += 1
            return out
        allow_top = {'type', 'sessionId', 'uuid', 'requestId', 'timestamp'}
        allow_usage = {'input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'}
        relevant = (allow_top | {'message'}) if kind == 'top' else ({'role', 'usage'} if kind == 'message' else allow_usage)
        seen_relevant = set()
        while True:
            self.ws()
            key = self.string(capture=True, limit=128, overflow_ok=True)
            self.ws()
            if self.i >= self.n or self.b[self.i] != 58:
                raise Bad()
            self.i += 1
            self.ws()
            if key in relevant:
                if key in seen_relevant:
                    raise Bad()
                seen_relevant.add(key)
            target = ((kind == 'top' and key in allow_top) or
                      (kind == 'message' and key == 'role') or
                      (kind == 'usage' and key in allow_usage))
            nested_message = kind == 'top' and key == 'message' and self.i < self.n and self.b[self.i] == 123
            nested_usage = kind == 'message' and key == 'usage' and self.i < self.n and self.b[self.i] == 123
            if nested_message:
                value = self.obj('message')
            elif nested_usage:
                value = self.obj('usage')
            elif target:
                value = self.scalar()
            else:
                self.skip()
                value = None
            retain = target or nested_message or nested_usage
            if retain:
                if key in out:
                    raise Bad()
                out[key] = value
            self.ws()
            if self.i >= self.n:
                raise Bad()
            if self.b[self.i] == 125:
                self.i += 1
                return out
            if self.b[self.i] != 44:
                raise Bad()
            self.i += 1


def parse(b):
    p = P(b)
    obj = p.obj('top')
    p.ws()
    if p.i != p.n:
        raise Bad()
    return obj

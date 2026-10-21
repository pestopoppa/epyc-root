#!/usr/bin/env python3
"""gguf_meta.py -- read-only GGUF KV-header summary (no tensor data is read, no model is loaded).

Reads only the header/KV region at the START of each file (a few MB). Large arrays (tokenizer tokens, merges,
scores, types) are folded into (count, sha256-of-elements) so two files can be compared for tokenizer identity.

usage: python3 -I gguf_meta.py FILE [FILE ...]   -> JSON on stdout
"""
import hashlib
import json
import struct
import sys

SCALAR = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2), 4: ("<I", 4), 5: ("<i", 4),
          6: ("<f", 4), 7: ("<?", 1), 10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}


def _read(f, n):
    b = f.read(n)
    if len(b) != n:
        raise EOFError("short read")
    return b


def _string(f):
    (n,) = struct.unpack("<Q", _read(f, 8))
    return _read(f, n)


def _value(f, t, big_hash=None):
    if t in SCALAR:
        fmt, size = SCALAR[t]
        return struct.unpack(fmt, _read(f, size))[0]
    if t == 8:
        return _string(f).decode("utf-8", "replace")
    if t == 9:
        (et,) = struct.unpack("<I", _read(f, 4))
        (n,) = struct.unpack("<Q", _read(f, 8))
        h = hashlib.sha256()
        head = []
        for i in range(n):
            if et == 8:
                raw = _string(f)
                h.update(struct.pack("<I", len(raw)))
                h.update(raw)
                v = raw.decode("utf-8", "replace")
            elif et in SCALAR:
                fmt, size = SCALAR[et]
                raw = _read(f, size)
                h.update(raw)
                v = struct.unpack(fmt, raw)[0]
            else:
                raise ValueError(f"unsupported array element type {et}")
            if i < 4:
                head.append(v)
        return {"array_of": et, "count": n, "sha256": h.hexdigest(), "head": head}
    raise ValueError(f"unsupported value type {t}")


def summarize(path):
    with open(path, "rb", buffering=1 << 20) as f:
        magic = _read(f, 4)
        if magic != b"GGUF":
            raise ValueError("not a GGUF")
        (version,) = struct.unpack("<I", _read(f, 4))
        n_tensors, n_kv = struct.unpack("<QQ", _read(f, 16))
        kv = {}
        for _ in range(n_kv):
            key = _string(f).decode()
            (t,) = struct.unpack("<I", _read(f, 4))
            kv[key] = _value(f, t)
        return {"path": path, "version": version, "n_tensors": n_tensors, "n_kv": n_kv, "kv": kv,
                "kv_region_end_offset": f.tell()}


if __name__ == "__main__":
    out = [summarize(p) for p in sys.argv[1:]]
    json.dump(out, sys.stdout, indent=1, sort_keys=True)

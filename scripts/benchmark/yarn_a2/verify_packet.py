#!/usr/bin/env python3
"""Validate a pinned A2 source packet before booking; never inspect model weights."""
import hashlib
import json
from pathlib import Path

class PacketError(ValueError):
    pass

def verify(root, manifest_path, expected_manifest_sha):
    root = Path(root).resolve(strict=True)
    path = Path(manifest_path).resolve(strict=True)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha:
        raise PacketError('manifest digest mismatch')
    entries = json.loads(raw)
    if not isinstance(entries, dict) or not entries:
        raise PacketError('empty packet manifest')
    for name, expected in entries.items():
        if not isinstance(name, str) or not isinstance(expected, str) or len(expected) != 64:
            raise PacketError('invalid entry')
        candidate = Path(name)
        if candidate.is_absolute() or '..' in candidate.parts:
            raise PacketError('packet path escapes root')
        try:
            target = (root / candidate).resolve(strict=True)
            if not target.is_relative_to(root) or not target.is_file():
                raise PacketError('packet path escapes root')
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError as exc:
            raise PacketError('packet file missing or unreadable') from exc
        if digest != expected:
            raise PacketError('packet file digest mismatch: ' + name)
    return len(entries)

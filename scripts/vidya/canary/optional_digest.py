"""Capture file presence and digest without creating absent live telemetry."""
import hashlib
from pathlib import Path


def optional_digest(path: Path) -> dict:
    try:
        with path.open('rb') as source:
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        return {'present': True, 'sha256': digest.hexdigest()}
    except FileNotFoundError:
        return {'present': False, 'sha256': None}

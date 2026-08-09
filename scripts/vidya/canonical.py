"""Canonical JSON serialization and content addressing for Vidya frames.

Spec: docs/design/vidya-pilot-spec.md §3.1 (content addressing), §5.1 (determinism inputs).

Two jobs, both correctness-critical:

1. Produce ONE byte string for a given value, on every platform and every run, so that a frame's
   identity does not depend on how it happened to be stored. The hash is over canonical JSON,
   never over stored bytes — a frame re-serialized by a different writer must keep its id.

2. Enforce the determinism rules mechanically rather than by convention. Floats are rejected
   outright: the spec forbids them in the certified algebra, and they are also the one part of
   RFC 8785 whose number formatting is genuinely hard to reproduce across languages. Rejecting
   them removes both problems at once, so this module implements the JCS rules it needs and
   refuses the input that would require the rest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = [
    "CanonicalizationError",
    "canonical_bytes",
    "content_hash",
    "HASH_ALGORITHM",
]

HASH_ALGORITHM = "sha256"

# Keys stripped before hashing an envelope: a frame's id cannot be an input to its own id, and a
# detached signature must be addable later without changing what the frame is.
_SELF_REFERENTIAL_KEYS = ("frame_id", "signatures")


class CanonicalizationError(TypeError):
    """A value cannot be canonicalized deterministically."""


def _check(value: Any, path: str = "$") -> None:
    """Reject anything whose canonical form is not reproducible.

    Raises with the JSON path of the offending value, because a bare "float not allowed" on a
    deeply nested frame is a poor debugging experience.
    """
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, float):
        raise CanonicalizationError(
            f"{path}: float values are forbidden in the certified path "
            f"(got {value!r}). Use an integer, or a string with an explicit unit/precision."
        )
    if isinstance(value, int):
        return
    if isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _check(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(
                    f"{path}: object keys must be strings (got {type(key).__name__})"
                )
            _check(item, f"{path}.{key}")
        return
    raise CanonicalizationError(f"{path}: unsupported type {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Serialize to canonical JSON bytes.

    Object keys are sorted, separators carry no whitespace, and the output is UTF-8. Non-ASCII
    characters are emitted literally (as JCS requires) rather than escaped.
    """
    _check(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_hash(value: Any, *, algorithm: str = HASH_ALGORITHM) -> str:
    """Return an algorithm-tagged content hash, e.g. ``sha256:1b4f0e...``.

    The tag is not decoration: the spec requires the algorithm to be recorded in every identifier
    so that a later migration to a different hash is legible in the data rather than inferred from
    a length.
    """
    if algorithm != "sha256":
        raise CanonicalizationError(f"unsupported hash algorithm {algorithm!r}")
    digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    return f"{algorithm}:{digest}"


def envelope_hash(envelope: dict, *, algorithm: str = HASH_ALGORITHM) -> str:
    """Content hash of a frame envelope, excluding its own id and any signatures.

    This is what makes an unsigned pilot frame and a later signed production frame the *same*
    frame — the inverse of the nanopublication ordering, which signs first and then addresses over
    the signature.
    """
    if not isinstance(envelope, dict):
        raise CanonicalizationError("envelope must be a mapping")
    stripped = {k: v for k, v in envelope.items() if k not in _SELF_REFERENTIAL_KEYS}
    return content_hash(stripped, algorithm=algorithm)

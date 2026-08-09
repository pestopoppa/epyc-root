"""L1 authentication: RFC 9162 Merkle roots + C2SP signed-note checkpoints.

Spec: docs/design/vidya-pilot-spec.md §11.1.
Pinned formats: c2sp.org/signed-note@v1.0.0, c2sp.org/tlog-checkpoint@v1.0.0.

Where this sits on the ladder: L0 is the ledger's own prev_hash chain, which is tamper-EVIDENT
only -- a rewriter who recomputes the chain leaves no trace. L1 is this module: a Merkle root over
the frame hashes, published as a signed note and committed to git. An externally held checkpoint
is what upgrades tamper-evident to tamper-PROOF for everything before it, because rewriting
history now requires also rewriting a record somebody else holds. L2 (tile materialization) waits
for a real trigger: a second writer, an external verifier, or served proofs.

PIN THE TAGS. Upstream main has already drifted from "SHOULD use Ed25519" toward post-quantum
ML-DSA-44 cosignatures. A naive follow-main implementation would produce checkpoints this verifier
rejects, so the format here is v1.0.0 and the drift is a watch item, not a silent upgrade.

Signing is intentionally optional. The pilot runs unsigned (spec §15 is honest that shadow mode
trusts the local identity); the note format, key-id derivation, and verification path are
implemented now so that turning signing on later changes a config value, not a format.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "merkle_root", "inclusion_proof", "verify_inclusion", "consistency_proof",
    "Checkpoint", "format_checkpoint", "parse_checkpoint", "key_id",
    "CheckpointError",
]

# RFC 9162 domain separation. Without these prefixes a leaf hash and an internal node hash live in
# the same space, which is the classic second-preimage attack on Merkle trees.
_LEAF_PREFIX = b"\x00"
_NODE_PREFIX = b"\x01"

_ED25519_SIG_TYPE = b"\x01"


class CheckpointError(Exception):
    """A checkpoint is malformed or fails verification."""


# -- RFC 9162 tree math --------------------------------------------------

def _leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(_LEAF_PREFIX + data).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(_NODE_PREFIX + left + right).digest()


def _split(n: int) -> int:
    """Largest power of two strictly less than n -- RFC 9162's k."""
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def merkle_root(entries: Sequence[bytes]) -> bytes:
    """MTH(D[n]) per RFC 9162 §2.1. The empty tree hashes to SHA-256 of the empty string."""
    n = len(entries)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return _leaf_hash(entries[0])
    k = _split(n)
    return _node_hash(merkle_root(entries[:k]), merkle_root(entries[k:]))


def inclusion_proof(entries: Sequence[bytes], index: int) -> list[bytes]:
    """PATH(m, D[n]) per RFC 9162 §2.1.3."""
    n = len(entries)
    if not 0 <= index < n:
        raise CheckpointError(f"index {index} out of range for tree of size {n}")
    if n == 1:
        return []
    k = _split(n)
    if index < k:
        return inclusion_proof(entries[:k], index) + [merkle_root(entries[k:])]
    return inclusion_proof(entries[k:], index - k) + [merkle_root(entries[:k])]


def verify_inclusion(
    leaf_data: bytes, index: int, tree_size: int, proof: Sequence[bytes], root: bytes
) -> bool:
    """Recompute the root from a leaf and its audit path."""
    if not 0 <= index < tree_size:
        return False
    node = _leaf_hash(leaf_data)
    fn, sn = index, tree_size - 1
    for sibling in proof:
        if fn % 2 == 1 or fn == sn:
            node = _node_hash(sibling, node)
            while fn % 2 == 0 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            node = _node_hash(node, sibling)
        fn >>= 1
        sn >>= 1
    return fn == 0 and node == root


def consistency_proof(entries: Sequence[bytes], m: int) -> list[bytes]:
    """PROOF(m, D[n]) per RFC 9162 §2.1.4 -- proves the tree at size m is a prefix of size n.

    This is the append-only proof: it is what makes "the log never rewrote history" checkable
    between two checkpoints, rather than merely asserted.
    """
    n = len(entries)
    if not 0 < m <= n:
        raise CheckpointError(f"consistency requires 0 < m <= n (got m={m}, n={n})")
    if m == n:
        return []
    return _subproof(entries, m, n, True)


def _subproof(entries: Sequence[bytes], m: int, n: int, b: bool) -> list[bytes]:
    if m == n:
        return [] if b else [merkle_root(entries[:n])]
    k = _split(n)
    if m <= k:
        return _subproof(entries, m, k, b) + [merkle_root(entries[k:n])]
    return _subproof(entries[k:], m - k, n - k, False) + [merkle_root(entries[:k])]


# -- C2SP signed note / tlog-checkpoint ----------------------------------

def key_id(name: str, public_key: bytes, sig_type: bytes = _ED25519_SIG_TYPE) -> bytes:
    """key ID = SHA-256(name || 0x0A || sig_type || public_key)[:4], per c2sp.org/signed-note."""
    return hashlib.sha256(name.encode("utf-8") + b"\x0a" + sig_type + public_key).digest()[:4]


@dataclass(frozen=True)
class Checkpoint:
    """A tlog-checkpoint note body: origin, tree size, root hash."""

    origin: str
    tree_size: int
    root_hash: bytes

    def __post_init__(self) -> None:
        if not self.origin or " " in self.origin or "+" in self.origin:
            raise CheckpointError(
                f"origin must be non-empty and contain no spaces or '+': {self.origin!r}"
            )
        if self.tree_size < 0:
            raise CheckpointError("tree_size must be >= 0")
        if len(self.root_hash) != 32:
            raise CheckpointError(f"root_hash must be 32 bytes, got {len(self.root_hash)}")

    def note_text(self) -> str:
        """The signed body: three lines, each newline-terminated, no extension lines.

        Extension lines are NOT RECOMMENDED upstream and are unsigned under the cosignature
        formats, so they are omitted entirely rather than left as a trap.
        """
        return (
            f"{self.origin}\n"
            f"{self.tree_size}\n"
            f"{base64.b64encode(self.root_hash).decode('ascii')}\n"
        )


def format_checkpoint(
    checkpoint: Checkpoint,
    signatures: Sequence[tuple[str, bytes]] = (),
) -> str:
    """Render a signed note: body, blank line, then one em-dash signature line each.

    `signatures` are ``(key_name, 4-byte key id || raw signature)`` pairs. An empty sequence
    produces an unsigned note -- valid for the shadow pilot, and byte-compatible with the signed
    form once keys exist.
    """
    lines = [checkpoint.note_text(), "\n"]
    for name, sig_bytes in signatures:
        if " " in name or "+" in name:
            raise CheckpointError(f"key name must not contain spaces or '+': {name!r}")
        lines.append(f"— {name} {base64.b64encode(sig_bytes).decode('ascii')}\n")
    return "".join(lines)


def parse_checkpoint(note: str) -> tuple[Checkpoint, list[tuple[str, bytes]]]:
    """Parse a signed note back into a checkpoint and its signature lines.

    The body/signature split is at the LAST empty line, per the spec -- the body is permitted to
    contain empty lines, so splitting at the first would be wrong.
    """
    if "\n\n" not in note:
        raise CheckpointError("malformed note: no blank line separating body from signatures")
    idx = note.rindex("\n\n")
    body, sig_block = note[: idx + 1], note[idx + 2 :]

    body_lines = body.split("\n")
    if body_lines and body_lines[-1] == "":
        body_lines.pop()
    if len(body_lines) < 3:
        raise CheckpointError(
            f"checkpoint body needs at least 3 lines (origin, size, root); got {len(body_lines)}"
        )
    origin, size_str, root_b64 = body_lines[0], body_lines[1], body_lines[2]
    if size_str != str(int(size_str)):
        raise CheckpointError(f"tree size must be canonical decimal with no leading zeros: {size_str!r}")
    try:
        root = base64.b64decode(root_b64, validate=True)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CheckpointError below
        raise CheckpointError(f"root hash is not valid base64: {root_b64!r}") from exc

    signatures: list[tuple[str, bytes]] = []
    for line in sig_block.split("\n"):
        if not line:
            continue
        if not line.startswith("— "):
            raise CheckpointError(f"signature line must start with an em-dash and a space: {line!r}")
        try:
            name, b64 = line[2:].split(" ", 1)
        except ValueError as exc:
            raise CheckpointError(f"malformed signature line: {line!r}") from exc
        signatures.append((name, base64.b64decode(b64, validate=True)))

    return Checkpoint(origin=origin, tree_size=int(size_str), root_hash=root), signatures


def checkpoint_for(origin: str, frame_hashes: Sequence[str]) -> Checkpoint:
    """Build a checkpoint over a ledger's frame hashes (as ``algorithm:hex`` strings)."""
    leaves = [h.encode("utf-8") for h in frame_hashes]
    return Checkpoint(origin=origin, tree_size=len(leaves), root_hash=merkle_root(leaves))

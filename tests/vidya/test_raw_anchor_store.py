"""Prospective raw-source binding controls for SC76/SC77.

All network responses below are synthetic and injected at the urllib boundary.
"""

from __future__ import annotations

import hashlib
import os
import sys
from email.message import Message
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import machine_anchor  # noqa: E402
from adapters.research_intake import FT_SUPPORT, _frames_for_entry, _t_level  # noqa: E402
from raw_anchor_store import ArtifactUnavailable, read_raw_bytes, store_raw_bytes  # noqa: E402


TEXT = (
    "We introduce a chunked Gated-DeltaNet recurrence for long-context decoding. "
    "The state-recomputation kernel is written to a fixed 64-wide block dimension throughout. "
    "Our evaluation covers three model families and two hardware targets. "
    "Throughput improves by 18 percent on the long-context benchmark relative to the baseline. "
    "We leave multi-node scaling to future work. "
    "The append-only cache stores intermediate recurrence state separately from token outputs."
)
URL = "https://example.org/paper"


def _response(raw: bytes, *, effective_url: str = URL, media_type: str = "text/html"):
    class Response:
        headers = Message()

        def __init__(self):
            self.headers["Content-Type"] = f"{media_type}; charset=utf-8"
            self._raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, size=-1):
            if size < 0:
                size = len(self._raw)
            result, self._raw = self._raw[:size], self._raw[size:]
            return result

        def geturl(self):
            return effective_url

    return Response()


def _anchor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, located_by: str | None = None):
    monkeypatch.setenv("EPYC_VIDYA_RAW_ANCHOR_ROOT", str(tmp_path / "private-vault"))
    raw = f"<html><body><p>{TEXT}</p></body></html>".encode()
    monkeypatch.setattr(machine_anchor.urllib.request, "urlopen", lambda *_a, **_k: _response(raw))
    extracted, artifact = machine_anchor.fetch_document(URL)
    assert artifact is not None
    entry = {"url": URL, "key_claims": ["The state-recomputation kernel uses a fixed 64-wide block dimension."]}
    anchor = machine_anchor.anchor_entry(entry, document=extracted, source_artifact=artifact)[0]
    if located_by:
        anchor["located_by"] = located_by
    return entry, anchor, Path(os.environ["EPYC_VIDYA_RAW_ANCHOR_ROOT"])


def test_response_bytes_are_retained_and_reopened_by_content_identity(tmp_path, monkeypatch):
    _entry, anchor, root = _anchor(tmp_path, monkeypatch, located_by="machine")
    metadata = anchor["source_artifact"]
    retained = read_raw_bytes(metadata, root=root)
    assert hashlib.sha256(retained).hexdigest() == metadata["raw_sha256"]
    assert len(retained) == metadata["byte_length"]
    assert Path(metadata["relative_path"]).name == f"{metadata['raw_sha256']}.raw"
    assert machine_anchor.verify_source_anchor(anchor, entry_url=URL) == (True, "verified")
    assert _t_level({"url": URL}, anchor) == "MachineLocated"


def test_human_tier_requires_valid_retained_source_and_machine_tier_stays_capped(tmp_path, monkeypatch):
    """The human fields below model an explicit reviewer assertion in a synthetic fixture.

    The test exercises the adapter's tier contract; it does not claim that raw-byte integrity
    verification itself makes a semantic judgment about the source.
    """
    entry, machine, _root = _anchor(tmp_path, monkeypatch, located_by="machine")
    human = dict(machine)
    human["located_by"] = "human"
    human["verified_by"] = "synthetic-human-reviewer"
    assert _t_level(entry, human) == "Attested"
    assert _t_level(entry, machine) == "MachineLocated"


def test_legacy_shape_and_unknown_metadata_never_raise_anchor_tier(tmp_path, monkeypatch):
    entry = {"url": URL}
    legacy = {"quote": TEXT, "quote_sha256": "ab" * 32, "source_revision": "v2"}
    assert _t_level(entry, legacy) == "Located"
    _entry, anchor, _root = _anchor(tmp_path, monkeypatch, located_by="machine")
    anchor["source_artifact"]["trust_me"] = True
    valid, status = machine_anchor.verify_source_anchor(anchor, entry_url=URL)
    assert not valid and status.startswith("unknown:")
    assert _t_level({"url": URL}, anchor) == "Located"


def test_frame_retains_the_exact_source_binding_metadata(tmp_path, monkeypatch):
    entry, anchor, _root = _anchor(tmp_path, monkeypatch, located_by="machine")
    entry = dict(entry, id="intake-1234", claim_anchors=[anchor])
    frames = _frames_for_entry(entry, "2026-10-06T12:00:00Z")
    support = next(frame for frame in frames if frame["frame_type"] == FT_SUPPORT)
    projected = support["provenance"]["anchor"]
    assert projected["source_verification"] == "verified"
    assert projected["source_artifact"] == anchor["source_artifact"]


def test_tampered_or_symlinked_artifact_is_unknown(tmp_path, monkeypatch):
    _entry, anchor, root = _anchor(tmp_path, monkeypatch, located_by="machine")
    object_path = root / anchor["source_artifact"]["relative_path"]
    object_path.chmod(0o600)
    original = object_path.read_bytes()
    object_path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    assert machine_anchor.verify_source_anchor(anchor, entry_url=URL)[0] is False

    object_path.unlink()
    outside = tmp_path / "outside.raw"
    outside.write_bytes(original)
    outside.chmod(0o600)
    object_path.symlink_to(outside)
    assert machine_anchor.verify_source_anchor(anchor, entry_url=URL)[0] is False


def test_hardlinked_retained_file_is_unknown(tmp_path, monkeypatch):
    _entry, anchor, root = _anchor(tmp_path, monkeypatch, located_by="machine")
    object_path = root / anchor["source_artifact"]["relative_path"]
    alias = tmp_path / "alias.raw"
    os.link(object_path, alias)
    with pytest.raises(ArtifactUnavailable):
        read_raw_bytes(anchor["source_artifact"], root=root)
    assert machine_anchor.verify_source_anchor(anchor, entry_url=URL)[0] is False


def test_fifo_at_content_path_is_refused_without_blocking(tmp_path):
    root = tmp_path / "vault"
    raw = b"fifo control bytes"
    digest = hashlib.sha256(raw).hexdigest()
    shard = root / "sha256" / digest[:2]
    shard.mkdir(parents=True, mode=0o700)
    os.chmod(root, 0o700)
    os.chmod(root / "sha256", 0o700)
    os.chmod(shard, 0o700)
    fifo = shard / f"{digest}.raw"
    os.mkfifo(fifo, 0o600)
    metadata = {
        "entry_url": URL,
        "requested_url": URL,
        "effective_url": URL,
        "retrieved_at_utc": "2026-10-06T12:00:00Z",
        "media_type": "text/plain",
        "extractor_id": machine_anchor.EXTRACTOR_ID,
        "extractor_sha256": machine_anchor._extractor_sha256(),
    }
    with pytest.raises(ArtifactUnavailable):
        store_raw_bytes(raw, metadata, root=root)


def test_arxiv_verification_requires_three_explicit_exact_revision_urls(tmp_path, monkeypatch):
    _entry, anchor, _root = _anchor(tmp_path, monkeypatch, located_by="machine")
    artifact = dict(anchor["source_artifact"])
    urls = [
        "https://arxiv.org/abs/2604.08224",
        "https://arxiv.org/html/2604.08224",
        "https://arxiv.org/html/2604.08224",
    ]
    for key, url in zip(("entry_url", "requested_url", "effective_url"), urls):
        artifact[key] = url
    anchor["source_artifact"] = artifact
    anchor["source_revision"] = urls[-1]
    assert machine_anchor.verify_source_anchor(anchor, entry_url=urls[0])[0] is False

    artifact["entry_url"] = "https://evil-arxiv.org/abs/2604.08224v2"
    artifact["requested_url"] = "https://example.org/?next=https://arxiv.org/html/2604.08224v2"
    artifact["effective_url"] = "https://arxiv.org/html/2604.08224v2"
    anchor["source_revision"] = artifact["effective_url"]
    assert machine_anchor.verify_source_anchor(anchor, entry_url=artifact["entry_url"])[0] is False

def test_missing_original_wrong_quote_and_wrong_source_revision_are_unknown(tmp_path, monkeypatch):
    entry, anchor, root = _anchor(tmp_path, monkeypatch, located_by="machine")
    missing = {key: value for key, value in anchor.items() if key != "source_artifact"}
    assert machine_anchor.verify_source_anchor(missing, entry_url=URL)[0] is False

    wrong_quote = dict(anchor, quote="quote not found in original")
    assert machine_anchor.verify_source_anchor(wrong_quote, entry_url=URL)[0] is False
    wrong_revision = dict(anchor, source_revision="https://example.org/another-revision")
    assert machine_anchor.verify_source_anchor(wrong_revision, entry_url=URL)[0] is False

    object_path = root / anchor["source_artifact"]["relative_path"]
    object_path.unlink()
    assert machine_anchor.verify_source_anchor(anchor, entry_url=URL)[0] is False
    assert _t_level(entry, anchor) == "Located"


def test_traversal_and_unsafe_root_permissions_refuse(tmp_path, monkeypatch):
    _entry, anchor, root = _anchor(tmp_path, monkeypatch, located_by="machine")
    escaped = dict(anchor["source_artifact"], relative_path="../../outside.raw")
    forged = dict(anchor, source_artifact=escaped)
    assert machine_anchor.verify_source_anchor(forged, entry_url=URL)[0] is False

    root.chmod(0o755)
    assert machine_anchor.verify_source_anchor(anchor, entry_url=URL)[0] is False


def test_symlinked_artifact_root_is_refused(tmp_path):
    target = tmp_path / "real-vault"
    target.mkdir(mode=0o700)
    link = tmp_path / "linked-vault"
    link.symlink_to(target, target_is_directory=True)
    metadata = {
        "entry_url": URL,
        "requested_url": URL,
        "effective_url": URL,
        "retrieved_at_utc": "2026-10-06T12:00:00Z",
        "media_type": "text/plain",
        "extractor_id": machine_anchor.EXTRACTOR_ID,
        "extractor_sha256": machine_anchor._extractor_sha256(),
    }
    with pytest.raises(ArtifactUnavailable):
        store_raw_bytes(b"response", metadata, root=link)


def test_store_is_missing_only_and_conflicting_existing_object_refuses(tmp_path):
    root = tmp_path / "vault"
    root.mkdir(mode=0o700)
    raw = b"one immutable synthetic response"
    metadata = {
        "entry_url": URL,
        "requested_url": URL,
        "effective_url": URL,
        "retrieved_at_utc": "2026-10-06T12:00:00Z",
        "media_type": "text/plain",
        "extractor_id": machine_anchor.EXTRACTOR_ID,
        "extractor_sha256": machine_anchor._extractor_sha256(),
    }
    first = store_raw_bytes(raw, metadata, root=root)
    second = store_raw_bytes(raw, metadata, root=root)
    assert first == second
    object_path = root / first["relative_path"]
    object_path.chmod(0o600)
    object_path.write_bytes(b"conflicting replacement bytes")
    with pytest.raises(ArtifactUnavailable):
        store_raw_bytes(raw, metadata, root=root)


def test_unversioned_arxiv_and_revision_redirect_mismatch_do_not_bind(monkeypatch):
    raw = ("<html><body>" + TEXT + "</body></html>").encode()
    monkeypatch.setattr(machine_anchor.urllib.request, "urlopen", lambda *_a, **_k: _response(raw))
    assert machine_anchor.fetch_document("https://arxiv.org/abs/2604.08224") == (None, None)

    requested = "https://arxiv.org/abs/2604.08224v2"
    wrong_revision = "https://arxiv.org/html/2604.08224v3"
    monkeypatch.setattr(
        machine_anchor.urllib.request,
        "urlopen",
        lambda *_a, **_k: _response(raw, effective_url=wrong_revision),
    )
    text, artifact = machine_anchor.fetch_document(requested)
    assert text is not None and artifact is None


def test_unsupported_media_never_produces_a_retained_anchor(monkeypatch):
    raw = b"%PDF-1.7 " + b"x" * 500
    monkeypatch.setattr(
        machine_anchor.urllib.request,
        "urlopen",
        lambda *_a, **_k: _response(raw, media_type="application/pdf"),
    )
    assert machine_anchor.fetch_document(URL) == (None, None)


def test_no_configured_root_returns_no_source_warrant(tmp_path, monkeypatch):
    monkeypatch.delenv("EPYC_VIDYA_RAW_ANCHOR_ROOT", raising=False)
    raw = b"synthetic source bytes"
    metadata = {
        "entry_url": URL,
        "requested_url": URL,
        "effective_url": URL,
        "retrieved_at_utc": "2026-10-06T12:00:00Z",
        "media_type": "text/plain",
        "extractor_id": machine_anchor.EXTRACTOR_ID,
        "extractor_sha256": machine_anchor._extractor_sha256(),
    }
    assert store_raw_bytes(raw, metadata) is None

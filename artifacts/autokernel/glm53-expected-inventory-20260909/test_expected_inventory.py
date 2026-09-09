"""Hermetic metadata author tests; owning validation reads only six tiny files."""
import base64
import hashlib
import json
import os
from pathlib import Path

import author_expected_inventory as author
import pytest


@pytest.fixture
def inputs(tmp_path):
    cache = tmp_path / "cache"
    (cache / "trees").mkdir(parents=True)
    (cache / "download" / author.QUANTIZATION).mkdir(parents=True)
    model = tmp_path / "tiny-model"
    model.mkdir()
    entries = {}
    for index, name in enumerate(author.BASENAMES, 1):
        content = f"tiny synthetic member {index}\n".encode()
        (model / name).write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()
        entries[f"{author.QUANTIZATION}/{name}"] = {
            "size": len(content), "lfs_size": len(content), "lfs_sha256": sha,
            "blob_id": hashlib.sha1(content).hexdigest(), "xet_hash": sha,
        }
        (cache / "download" / author.QUANTIZATION / f"{name}.metadata").write_text(
            f"{author.REVISION}\n{sha}\n1787946991.752891\n")
    tree = cache / "trees" / f"{author.REVISION}.json"
    tree.write_bytes(author.canonical({"format_version": 1, "files": entries}))
    return cache, model, tree


def rewrite_tree(tree, update):
    value = json.loads(tree.read_bytes())
    update(value)
    tree.write_bytes(author.canonical(value))


def test_exact_expected_packet_never_reads_model_members(inputs, monkeypatch):
    cache, model, tree = inputs
    original_open = os.open

    def checked_open(path, *args, **kwargs):
        # All author reads are descriptor-relative; these basenames must never open.
        assert str(path) not in author.BASENAMES
        assert not str(path).startswith(str(model))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", checked_open)
    first = author.assemble(str(cache), str(model))
    second = author.assemble(str(cache), str(model))
    assert first == second
    assert len(first) == 9
    assert base64.b64decode(first["source-tree.json.base64"].rstrip(b"\n"), validate=True) == tree.read_bytes()
    manifest = json.loads(first["model-identity.expected.json"])
    provenance = json.loads(first["expected-inventory-provenance.json"])
    assert set(manifest) == {"schema", "model_path", "files"}
    assert [row["path"] for row in manifest["files"]] == list(author.BASENAMES)
    assert provenance["local_model_bytes_verified"] is False
    assert provenance["remote_metadata_freshly_authenticated"] is False
    assert provenance["disposition"] == "metadata_declared_expected"
    assert provenance["retained_source_tree"] == "source-tree.json.base64"
    assert provenance["retained_source_tree_encoding"] == "base64"
    assert provenance["source_tree_sha256"] == hashlib.sha256(tree.read_bytes()).hexdigest()
    assert provenance["source_tree_size_bytes"] == len(tree.read_bytes())
    assert provenance["retained_source_tree_sha256"] == hashlib.sha256(first["source-tree.json.base64"]).hexdigest()
    assert provenance["expected_entry_sha256"] == manifest["files"][0]["sha256"]
    assert provenance["expected_entry_sha256"] != provenance["expected_normalized_inventory_sha256"]
    for index, name in enumerate(author.BASENAMES, 1):
        expected = (cache / "download" / author.QUANTIZATION / f"{name}.metadata").read_bytes()
        assert first[f"download/{index:05d}.metadata"] == expected


def test_owning_parser_normalization_and_full_verification_on_tiny_files_only(inputs, tmp_path, monkeypatch):
    cache, model, _ = inputs
    selected_source = os.environ.get("EPYC_RESEARCH_ROOT")
    if selected_source is None:
        pytest.skip("owning validator requires explicit EPYC_RESEARCH_ROOT")
    source = Path(selected_source).resolve(strict=True)
    monkeypatch.syspath_prepend(str(source))
    from scripts.kernel_rnd.autokernel.evaluator import c3_epyc_tensor_capture as owner
    artifacts = author.assemble(str(cache), str(model))
    output = tmp_path / "packet"
    author.write_new_packet(str(output), artifacts)
    provenance = json.loads(artifacts["expected-inventory-provenance.json"])
    manifest = json.loads(artifacts["model-identity.expected.json"])
    material = {"model_path": str(model), "files": manifest["files"]}
    assert author.canonical(material).decode() == owner._canonical(material)
    identity = owner.CaptureModelIdentity(str(model), output / "model-identity.expected.json",
        provenance["expected_manifest_sha256"], provenance["expected_normalized_inventory_sha256"])
    identity.validate()
    # Genuine owning byte verification rejects corruption, independently of metadata authoring.
    (model / author.BASENAMES[2]).write_bytes(b"changed tiny bytes")
    with pytest.raises(owner.TensorCaptureRefusal, match="hash mismatch"):
        identity.validate()
    with pytest.raises(FileExistsError):
        author.write_new_packet(str(output), artifacts)


@pytest.mark.parametrize("mutation", ["hash", "size", "size_bool", "missing", "extra",
    "escape", "uppercase_hash", "blob", "version", "unknown_field"])
def test_tree_one_fact_mutations_refuse(inputs, mutation):
    cache, model, tree = inputs
    key = f"{author.QUANTIZATION}/{author.BASENAMES[0]}"

    def change(value):
        row = value["files"][key]
        if mutation == "hash":
            row["lfs_sha256"] = hashlib.sha256(b"different").hexdigest()
        elif mutation == "size":
            row["lfs_size"] += 1
        elif mutation == "size_bool":
            row["size"] = True
        elif mutation == "missing":
            del value["files"][key]
        elif mutation == "extra":
            value["files"][f"{author.QUANTIZATION}/extra.gguf"] = row
        elif mutation == "escape":
            value["files"][f"{author.QUANTIZATION}/../escape.gguf"] = value["files"].pop(key)
        elif mutation == "uppercase_hash":
            row["lfs_sha256"] = row["lfs_sha256"].upper()
        elif mutation == "blob":
            row["blob_id"] = "wrong"
        elif mutation == "version":
            value["format_version"] = True
        else:
            row["unreviewed"] = "value"

    rewrite_tree(tree, change)
    with pytest.raises(author.AuthoringRefused):
        author.assemble(str(cache), str(model))


@pytest.mark.parametrize("mutation", ["revision", "etag", "extra_line", "timestamp", "nan"])
def test_metadata_one_fact_mutations_refuse(inputs, mutation):
    cache, model, _ = inputs
    path = cache / "download" / author.QUANTIZATION / f"{author.BASENAMES[0]}.metadata"
    lines = path.read_text().splitlines()
    if mutation == "revision":
        lines[0] = "f" * 40
    elif mutation == "etag":
        lines[1] = "f" * 64
    elif mutation == "extra_line":
        lines.append("extra")
    else:
        lines[2] = "NaN" if mutation == "nan" else "not a time"
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(author.AuthoringRefused):
        author.assemble(str(cache), str(model))


@pytest.mark.parametrize("mutation", ["symlink", "parent_symlink", "fifo", "oversize", "duplicate", "json"])
def test_bounded_source_refusals(inputs, tmp_path, mutation):
    cache, model, tree = inputs
    if mutation == "symlink":
        retained = tmp_path / "tree-retained.json"
        tree.rename(retained)
        tree.symlink_to(retained)
    elif mutation == "parent_symlink":
        linked = tmp_path / "linked-cache"
        linked.symlink_to(cache, target_is_directory=True)
        cache = linked
    elif mutation == "fifo":
        tree.unlink()
        os.mkfifo(tree)
    elif mutation == "oversize":
        tree.write_bytes(b" " * (author.TREE_CAP + 1))
    elif mutation == "duplicate":
        tree.write_bytes(b'{"format_version":1,"format_version":1,"files":{}}')
    else:
        tree.write_bytes(b"{")
    with pytest.raises(author.AuthoringRefused):
        author.assemble(str(cache), str(model))


@pytest.mark.parametrize("bad_root", ["relative/model", "/a/../b", "/a//b", "//a/b", "/a/"])
def test_model_root_must_be_lexically_normalized_without_opening_it(inputs, bad_root):
    cache, _, _ = inputs
    with pytest.raises(author.AuthoringRefused):
        author.assemble(str(cache), bad_root)


def test_nonexistent_model_root_allowed_only_as_expected_metadata(inputs):
    cache, model, _ = inputs
    unverified = str(model / "does-not-exist")
    result = author.assemble(str(cache), unverified)
    assert json.loads(result["model-identity.expected.json"])["model_path"] == unverified
    assert json.loads(result["expected-inventory-provenance.json"])["local_model_bytes_verified"] is False


def test_sorted_manifest_ignores_tree_key_order_and_unselected_quantization(inputs):
    cache, model, tree = inputs
    original = author.assemble(str(cache), str(model))["model-identity.expected.json"]
    rewrite_tree(tree, lambda value: value.update(files={"OTHER/ignored": {},
        **dict(reversed(list(value["files"].items())))}))
    assert author.assemble(str(cache), str(model))["model-identity.expected.json"] == original


def test_retained_original_tree_encoding_is_lossless_without_final_newline():
    root = Path(__file__).parent
    encoded = (root / "source-tree.json.base64").read_bytes()
    assert encoded.endswith(b"\n") and encoded.count(b"\n") == 1
    decoded = base64.b64decode(encoded[:-1], validate=True)
    assert len(decoded) == 14118
    assert decoded.endswith(b"}") and not decoded.endswith(b"\n")
    assert hashlib.sha256(decoded).hexdigest() == "4badb4fd6433a833d7ae7525732c865d7d73a7ace347f23e99c56a534e279ba1"
    provenance = json.loads((root / "expected-inventory-provenance.json").read_bytes())
    assert provenance["source_tree_size_bytes"] == len(decoded)
    assert provenance["source_tree_sha256"] == hashlib.sha256(decoded).hexdigest()
    assert provenance["retained_source_tree_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert provenance["local_model_bytes_verified"] is False

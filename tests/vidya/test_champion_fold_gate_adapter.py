"""Strict verifier projection for prospective fold_gate v4 records."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from claim_tuple import ProjectionError, to_frames
from adapters import champion_fold_gate as adapter
from ledger import Ledger
import cli as vidya_cli


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def store(tmp_path, name, manifest):
    path = tmp_path / name
    path.mkdir(exist_ok=True)
    sums = path / "SHA256SUMS"
    sums.write_text(manifest)
    return {"store_path": str(path), "sha256s_path": str(sums),
            "sha256s_sha256": hashlib.sha256(manifest.encode()).hexdigest()}


def library(stem, base, candidate, verdict, code_identical, details, base_store, candidate_store):
    row = {"record_type": "library", "soname_stem": stem, "base_soname": base,
           "candidate_soname": candidate, "verdict_class": verdict,
           "code_identical": code_identical, "differing_sections": details}
    identity = "is identical" if code_identical else "is not established as identical"
    pair = f"{base} -> {candidate}" if base and candidate else stem
    row["decided_proposition"] = (
        f"Fold gate v4 classified {verdict} for {pair}: executable code {identity} "
        f"between base store {base_store['store_path']} and candidate store {candidate_store['store_path']}."
    )
    return row


def document(tmp_path):
    base_store = store(tmp_path, "base-image", "base fixture manifest\n")
    candidate_store = store(tmp_path, "new-image", "candidate fixture manifest\n")
    rows = [
        library("libggml-alpha.so", "libggml-alpha.so.14000", "libggml-alpha.so.15000", "EXPLAINED", True,
                ["build-id differs"], base_store, candidate_store),
        library("libggml-ui.so", "libggml-ui.so.14000", "libggml-ui.so.15000", "EXPLAINED-UI", False,
                ["_GLOBAL__sub_I_ui.cpp: UI asset immediates"], base_store, candidate_store),
    ]
    exc = {"record_type": "accepted_exception", "exception_class": "EXPLAINED-UI",
           "library_stem": "libggml-ui.so", "accepted_by": adapter.ACCEPTOR,
           "decided_proposition": adapter._exception_proposition(rows[1]),
           "differing_sections": rows[1]["differing_sections"]}
    return {"schema": adapter.SCHEMA, "gate_version": adapter.GATE_VERSION,
            "recorded_at": utc_now(), "base": base_store, "candidate": candidate_store,
            "libraries": rows,
            "symlinks": [{"name": "libggml-alpha.so", "base_target": "libggml-alpha.so.14000",
                          "candidate_target": "libggml-alpha.so.15000", "candidate_target_exists": True,
                          "verdict_class": "MATCHED"}],
            "exceptions": [exc], "gate_verdict": "PASS"}


def save(tmp_path, doc=None):
    path = tmp_path / "fold_gate_record.json"
    path.write_text(json.dumps(doc if doc is not None else document(tmp_path)))
    return path


def test_projects_each_library_and_the_accepted_exception(tmp_path):
    path = save(tmp_path)
    native = adapter.native_rows(path)
    assert len(native) == 3
    tuples = [adapter.project(row) for row in native]
    assert all(t.source_class == "verifier" for t in tuples)
    assert all(t.binding_kind == "identity" and t.claim == t.decided_proposition for t in tuples)
    assert [t.metric for t in tuples].count("champion_fold_library_code_identity") == 2
    assert [t.metric for t in tuples].count("champion_fold_exception_acceptance") == 1
    assert tuples[0].value is True and tuples[1].value is False
    assert tuples[2].extra["verdict_class"] == "EXPLAINED-UI"
    assert all(t.attestation_sha256 == hashlib.sha256(path.read_bytes()).hexdigest() for t in tuples)
    frames = to_frames(tuples[0], as_of=utc_now(), adapter_id=adapter.ADAPTER_ID,
                       authority=adapter.AUTHORITY)
    claim = next(frame for frame in frames if frame["frame_type"] == "epyc.vidya/frame/claim_proposed/v1")
    assert claim["assertion"]["display_text"] == tuples[0].claim
    assert claim["assertion"]["decided_proposition"] == tuples[0].decided_proposition
    assert adapter.units(tmp_path) == [path]


@pytest.mark.parametrize("mutation", ["digest", "store-digest-mismatch", "proposition", "gate-verdict",
                                       "exception", "unknown-class"])
def test_refuses_unbound_or_inconsistent_records(tmp_path, mutation):
    doc = copy.deepcopy(document(tmp_path))
    if mutation == "digest":
        doc["base"]["sha256s_sha256"] = "not-a-digest"
    elif mutation == "store-digest-mismatch":
        doc["base"]["sha256s_sha256"] = "c" * 64
    elif mutation == "proposition":
        doc["libraries"][0]["decided_proposition"] = "PASS"
    elif mutation == "gate-verdict":
        doc["gate_verdict"] = "FAIL"
    elif mutation == "exception":
        doc["exceptions"].clear()
    elif mutation == "unknown-class":
        doc["libraries"][0]["verdict_class"] = "SUCCESS"
    with pytest.raises(ProjectionError):
        adapter.native_rows(save(tmp_path, doc))


def test_retains_failed_missing_and_extra_library_findings(tmp_path):
    doc = document(tmp_path)
    doc["libraries"].append(library("libggml-gone.so", "libggml-gone.so.14000", None, "MISSING", False,
                                    ["no candidate library with stem libggml-gone.so"], doc["base"], doc["candidate"]))
    doc["libraries"].append(library("libggml-new.so", None, "libggml-new.so.15000", "EXTRA", False,
                                    ["no base library with stem libggml-new.so"], doc["base"], doc["candidate"]))
    doc["gate_verdict"] = "FAIL"
    tuples = [adapter.project(row) for row in adapter.native_rows(save(tmp_path, doc))]
    failed = [t for t in tuples if t.metric == "champion_fold_library_code_identity" and not t.value]
    assert len(failed) == 3  # EXPLAINED-UI code difference, missing library, and extra library
    assert {t.extra["verdict_class"] for t in failed} == {"EXPLAINED-UI", "MISSING", "EXTRA"}
    assert all(t.extra["gate_verdict"] == "FAIL" for t in failed)


def test_unexplained_with_identical_code_is_a_valid_failed_gate_record(tmp_path):
    doc = document(tmp_path)
    doc["libraries"][0] = library(
        "libggml-alpha.so", "libggml-alpha.so.14000", "libggml-alpha.so.15000",
        "UNEXPLAINED", True, ["unexplained non-code section .vendor"],
        doc["base"], doc["candidate"])
    doc["gate_verdict"] = "FAIL"
    rows = adapter.native_rows(save(tmp_path, doc))
    library_row = next(row for row in rows if row["record_type"] == "library")
    assert adapter.project(library_row).value is True  # executable code identity is independent of gate pass

    doc["gate_verdict"] = "PASS"
    with pytest.raises(ProjectionError, match="overall gate verdict"):
        adapter.native_rows(save(tmp_path, doc))


def test_declines_a_foreign_schema_and_reopens_exact_bytes(tmp_path):
    path = save(tmp_path, {"schema": "some.other.source.v1"})
    assert adapter.native_rows(path) == ()

    path = save(tmp_path)
    native = adapter.native_rows(path)[0]
    changed = document(tmp_path)
    changed["recorded_at"] = "2026-10-25T12:01:00Z"
    save(tmp_path, changed)
    with pytest.raises(ProjectionError, match="changed since reopening"):
        adapter.project(native)


def test_actual_writer_reader_cli_and_only_new_round_trip(tmp_path, monkeypatch, capsys):
    research_root = os.environ.get("EPYC_FOLD_GATE_ROOT")
    if not research_root:
        pytest.skip("cross-repository integration requires EPYC_FOLD_GATE_ROOT from the granted test row")
    writer_path = Path(research_root) / "scripts/kernel_rnd/fold_gate/fold_gate.py"
    spec = importlib.util.spec_from_file_location("granted_fold_gate_writer", writer_path)
    assert spec and spec.loader
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)

    base_bin, candidate_bin = tmp_path / "base-store/bin", tmp_path / "candidate-store/bin"
    base_bin.mkdir(parents=True)
    candidate_bin.mkdir(parents=True)
    (base_bin.parent / "SHA256SUMS").write_text("synthetic base manifest\n")
    (candidate_bin.parent / "SHA256SUMS").write_text("synthetic candidate manifest\n")
    for root, version in ((base_bin, "14000"), (candidate_bin, "15000")):
        (root / f"libggml-core.so.{version}").write_bytes(b"synthetic same-code library")
        (root / f"libggml-ui.so.{version}").write_bytes(b"synthetic UI library")
        (root / "libggml-core.so").symlink_to(f"libggml-core.so.{version}")

    monkeypatch.setattr(writer, "ui_source_identical", lambda *args: (True, "synthetic source proof"))
    monkeypatch.setattr(writer.libcmp, "image_info", lambda *args: writer.libcmp.ImageInfo(known=True))

    def classify(base, candidate, *_args):
        if "libggml-ui.so." in base:
            return "EXPLAINED-UI", ["synthetic _GLOBAL__sub_I_ui.cpp distinction"]
        return "EXPLAINED", ["synthetic build-id distinction"]

    monkeypatch.setattr(writer.libcmp, "classify", classify)
    receipt = tmp_path / "fold_gate_record.json"
    args = writer.argparse.Namespace(base_image=str(base_bin), new_image=str(candidate_bin),
                                     src_repo=None, base_commit=None, cand_commit=None,
                                     expected_changed=[], ui_path=["tools/ui"])
    assert writer.run(args, out=lambda _line: None, record_json=receipt)
    source_doc = json.loads(receipt.read_text())
    expected_claims = len(source_doc["libraries"]) + len(source_doc["exceptions"])
    assert expected_claims == 3

    ledger_path = tmp_path / "belief-ledger.jsonl"
    command = ["--ledger", str(ledger_path), "--json", "ingest", "champion-fold-gate",
               "--path", str(receipt), "--as-of", utc_now(), "--only-new"]
    assert vidya_cli.main(command) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["refused"] == [] and first["rows_projected"] == expected_claims
    assert first["frames_emitted"] > 0
    initial_ledger = Ledger(ledger_path).read_all()
    assert sum(record.frame["frame_type"].endswith("/claim_proposed/v1") for record in initial_ledger) == expected_claims

    assert vidya_cli.main(command) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["refused"] == [] and second["rows_projected"] == expected_claims
    assert second["frames_emitted"] == 0
    assert len(Ledger(ledger_path).read_all()) == len(initial_ledger)


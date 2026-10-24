"""FD-DIV-1a smoke receipt + FD-DIV-1b result -> strict reader -> shared grade (VB-FUSED-DECODE-DIV-WIRE).

Synthetic receipts are built here; the real receipts are read-only when present. No process is touched.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import fused_decode_div as reader  # noqa: E402

REAL_1A = Path("/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/fd_div_1a_receipt.json")
REAL_1B = Path("/mnt/raid0/llm/tmp/fd-div-1b-20261024/out/RESULT.json")
SHA = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731


def _cell(i, rc=0, sha="a", warn=(), prints=0, abort=False):
    return {"id": i, "present": True, "rc": rc, "stdout_sha256": SHA(sha), "eval_ms_per_token": 70.0,
            "warn_tensors": list(warn), "v10_fused_prints": prints, "abort_signature": abort}


def _receipt(tmp_path, s1=True, s2=True, s3=None) -> Path:
    rule = tmp_path / "PREDECLARED.json"
    rule.write_text('{"row":"fd-div-1a"}')
    cells = {}
    for pr in reader.PROMPTS:
        cells[f"g_ref.{pr}"] = _cell(f"g_ref.{pr}", sha=pr)
        cells[f"g_test.{pr}"] = _cell(f"g_test.{pr}", sha=pr if s1 else pr + "x", warn=[reader.GSQ_REFUSAL])
        cells[f"u_ref.{pr}"] = _cell(f"u_ref.{pr}", sha="u" + pr, prints=31)
        cells[f"u_test.{pr}"] = _cell(f"u_test.{pr}", sha="u" + pr if s2 else "z", warn=[])
    cells["g_v10on.paris"] = _cell("g_v10on.paris", rc=134, prints=1, abort=True)
    doc = {"schema": reader.SCHEMA_1A, "time": "2026-10-23T16:43:59Z",
           "predeclared": {"path": str(rule), "sha256": hashlib.sha256(rule.read_bytes()).hexdigest()},
           "subject": {"commit": "14c57cbe9" + "0" * 31, "base": "ffc1bac82 (v10 tip)"}, "cells": cells,
           "propositions": [
               {"id": "S1", "result": s1, "decided_proposition": "GSQ fused-ON equals GGML_FUSED_DECODE_OFF=1 byte for byte"},
               {"id": "S2", "result": s2, "decided_proposition": "UD-IQ4_XS patched equals v10 store byte for byte"},
               {"id": "S3", "result": s3, "decided_proposition": "not decided: smoke 3 SKIPPED"}],
           "protocol_note": "experimental-tree correctness smoke"}
    p = tmp_path / "fd_div_1a_receipt.json"
    p.write_text(json.dumps(doc))
    return p


def test_1a_one_claim_per_decided_smoke_skipped_smoke_projects_nothing(tmp_path):
    natives = reader.native_rows(_receipt(tmp_path))
    assert [n["smoke"] for n in natives] == ["S1", "S2"]
    s1, s2 = (reader.project(n) for n in natives)
    assert s1.source_class == "verifier" and s1.decided_proposition == s1.claim and "byte for byte" in s1.claim
    assert s1.value == 1 and s1.unit == "boolean" and s1.attestation_verified is True
    assert s1.extra["defect_control_v10_fused_on"]["defect_reproduced"] is True
    assert s1.extra["pass_rule"]["rehashed"] is True and s1.extra["base_commit"].startswith("ffc1bac82")
    assert ct.grade(s1)[:2] == ("Judged", "Located") and s1.measurement_id != s2.measurement_id
    # decode ms/token is descriptive only: never the value
    assert s1.value != 70.0 and "decode_ms_per_token_descriptive" in s1.extra["identity_rows"][0]


def test_1a_stated_result_that_cells_contradict_is_refused(tmp_path):
    p = _receipt(tmp_path, s1=False)
    doc = json.loads(p.read_text())
    doc["propositions"][0]["result"] = True            # claims identity, cells differ
    p.write_text(json.dumps(doc))
    with pytest.raises(ct.ProjectionError, match="S1 stated result True"):
        reader.native_rows(p)


def test_1a_false_smoke_projects_value_zero(tmp_path):
    natives = reader.native_rows(_receipt(tmp_path, s1=False))
    assert reader.project(natives[0]).value == 0


def test_1a_pass_rule_that_does_not_re_hash_is_refused(tmp_path):
    p = _receipt(tmp_path)
    (tmp_path / "PREDECLARED.json").write_text('{"row":"tampered"}')
    with pytest.raises(ct.ProjectionError, match="does not re-hash"):
        reader.native_rows(p)


def _result_1b(tmp_path, ctl_clean=True) -> Path:
    out, job = tmp_path / "out", tmp_path / "job"
    out.mkdir(), job.mkdir()
    (job / "PREDECLARED.json").write_text('{"row":"fd-div-1b"}')
    line = lambda v: {"cfg": "native", "fused": 56, "expected": 56, "K_nmse": 1e-9, "idx_nmse": 1e-9,  # noqa: E731
                      "logits_nmse": 1e-11, "line_verdict": v}
    doc = {"schema": reader.SCHEMA_1B, "time": "2026-10-24T08:22:18Z",
           "pred_sha256": SHA('{"row":"fd-div-1b"}') if False else hashlib.sha256(b'{"row":"fd-div-1b"}').hexdigest(),
           "cells": {"ctl": {"id": "ctl", "rc": 0, "configs": [line("OK")], "class": "CLEAN"},
                     "w0.05": {"id": "w0.05", "rc": 1, "configs": [line("FAIL")], "class": "DIVERGE"},
                     "w1.0": {"id": "w1.0", "rc": 134, "configs": [], "class": "ABORT", "abort_line": "fused_moe: non-finite"}},
           "valid": {"control_clean": ctl_clean, "all_cells_present_and_interpretable": True},
           "verdict": "ANOTHER_CAUSE", "why": "fixture is F32/F16 only"}
    p = out / "RESULT.json"
    p.write_text(json.dumps(doc))
    (out / "JOB_META.json").write_text('{"head": "2a2a79bb66c3ffcad7da7585035651b97fe0f09b"}')
    return p


def test_1b_one_claim_per_cell_with_class_and_control(tmp_path):
    ts = {n["cell"]: reader.project(n) for n in reader.native_rows(_result_1b(tmp_path))}
    assert {k: t.value for k, t in ts.items()} == {"ctl": 1, "w0.05": 0, "w1.0": 0}
    assert "ABORT" in ts["w1.0"].claim and "DIVERGE" in ts["w0.05"].claim
    assert ts["ctl"].extra["subject_commit"].startswith("2a2a79bb6")
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in ts.values())


def test_1b_void_control_and_wrong_class_and_foreign_schema(tmp_path):
    assert reader.native_rows(_result_1b(tmp_path, ctl_clean=False)) == ()
    p = _result_1b(tmp_path / "x" if (tmp_path / "x").mkdir() is None else tmp_path)
    doc = json.loads(p.read_text())
    doc["cells"]["w0.05"]["class"] = "CLEAN"
    p.write_text(json.dumps(doc))
    with pytest.raises(ct.ProjectionError, match="stated class CLEAN"):
        reader.native_rows(p)
    p.write_text(json.dumps({"schema": "epyc.fd_div_1a.result.v1"}))
    assert reader.native_rows(p) == ()                 # FD-DIV-1a's analyzer echo is not a receipt


@pytest.mark.skipif(not (REAL_1A.is_file() and REAL_1B.is_file()), reason="real FD-DIV receipts not on this host")
def test_real_receipts_dispatch_through_ingest(tmp_path):
    from ledger import Ledger  # noqa: PLC0415

    a = reader.native_rows(REAL_1A)
    b = reader.native_rows(REAL_1B)
    assert [n["smoke"] for n in a] == ["S1", "S2"] and [n["cell"] for n in b] == ["ctl", "w0.05", "w0.3", "w1.0"]
    assert [reader.project(n).value for n in b] == [1, 0, 0, 0]
    assert reader.native_rows(REAL_1A.parent / "RESULT.json") == ()
    report = ingest_sources.ingest(Ledger(tmp_path / "l.jsonl"), "fused-decode-div", [REAL_1A, REAL_1B],
                                   as_of="2026-10-24T12:00:00Z", dry_run=True)
    assert report["rows_projected"] == 6 and report["refused"] == []


def test_adapter_registers_a_verifier_projection_and_no_ladder():
    assert ct.source_classes()[reader.SOURCE_KIND] == ct.VERIFIER_CLASS
    assert all("fused_decode_div" not in module for module, _ in ct.ladders().values())

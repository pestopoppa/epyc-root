"""AKX-ALL-26 CPU cells -> strict reader -> shared grade. Fixture tree, no inference."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_width_cells_cpu as reader  # noqa: E402

BUILD = "/scratch/build/bin"
REAL = Path("/mnt/raid0/llm/epyc-inference-research/artifacts/akx_all_26_cpu_20261020")


def _cell(op, typ, shape, k, verdict, route="cpu", nth=24, seed=1):
    if verdict == "UNSUPPORTED":
        return {"schema": reader.CELL_SCHEMA, "route": route, "nth": nth, "seed": seed, "op": op, "type": typ,
                "shape": shape, "mode": "-", "k": k, "n_reps": 0, "reps": [], "aa_clean": None,
                "verdict": verdict, "reason": "ne00 not a multiple of block size"}
    ok = verdict == "PASS"
    rep = {"batched_digest": "aa", "serial_digest": "aa" if ok else "bb", "equal": ok}
    return {"schema": reader.CELL_SCHEMA, "route": route, "nth": nth, "seed": seed, "op": op, "type": typ,
            "shape": shape, "mode": "-", "k": k, "n_reps": 3, "reps": [dict(rep)] * 3, "aa_clean": True,
            "verdict": verdict, "reason": ""}


def _header(short, typ, route="cpu", nth=24, seed=1):
    env = {"GGML_IQK": "1" if route == "cpu" else "<unset>", "LD_LIBRARY_PATH": BUILD}
    return {"schema": reader.GROUP_SCHEMA, "backend": "cpu", "route": route, "op": short, "type": typ,
            "nth": nth, "reps": 3, "kmax": 9, "seed": seed, "env": env}


@pytest.fixture
def tree(tmp_path):
    cells = []
    for k in range(1, 10):
        cells.append(_cell("MUL_MAT", "q8_0", "M2048", k, "PASS" if k == 1 else "FAIL"))
        cells.append(_cell("MUL_MAT", "q8_0", "M512", k, "PASS"))
        cells.append(_cell("MUL_MAT", "q8_0", "F640", k, "UNSUPPORTED"))
        cells.append(_cell("CONTROL", "F32", "ctl-bitflip-injection", k, "FAIL"))
        cells.append(_cell("CONTROL", "F32", "ctl-negative-width-independent", k, "PASS"))
        cells.append(_cell("CONTROL", "F32", "ctl-positive-width-dependent", k, "PASS" if k == 1 else "FAIL"))
    with gzip.open(tmp_path / "cells.jsonl.gz", "wt") as f:
        f.write("\n".join(json.dumps(c) for c in cells) + "\n")
    (tmp_path / "group_headers.jsonl").write_text(
        "\n".join(json.dumps(h) for h in (_header("mm", "Q8_0"), _header("ctl", "-"))) + "\n")
    controls = {"ctl-bitflip-injection": "F" * 9, "ctl-negative-width-independent": "P" * 9,
                "ctl-positive-width-dependent": "P" + "F" * 8}
    (tmp_path / "summary.json").write_text(json.dumps({
        "schema": reader.SUMMARY_SCHEMA, "controls": controls, "controls_ok": True, "err_cells": [],
        "nondet_cells": [], "n_aa_unclean": 0, "n_cells": len(cells), "n_cells_with_reps": len(cells) - 9,
        "n_groups": 6, "scoring_counts": {}}))
    add = b"frozen predictions"
    (tmp_path / "cpu_addendum_predictions.md").write_bytes(add)
    (tmp_path / "ADDENDUM.sha256").write_text(hashlib.sha256(add).hexdigest() + "  cpu_addendum_predictions.md\n")
    (tmp_path / "README.md").write_text("AKX-ALL-26 CPU half, 2026-10-20.\n")
    (tmp_path / "binary_sha256.txt").write_text("deadbeef  lib\n")
    (tmp_path / "predicted_fail_list.jsonl").write_text("{}\n")
    return tmp_path


def test_valid_tree_projects_counts_and_grades_by_the_shared_ladder(tree):
    natives = reader.native_rows(tree / "cells.jsonl.gz")
    assert [(n["outcome"], n["value"]) for n in natives] == [("fail", 1), ("pass", 1)]
    assert natives[0]["counts"] == {"fail": 1, "pass": 1, "unsupported": 1}
    tuples = [reader.project(n) for n in natives]
    assert all(t.protocol_id == "" and t.reps is None for t in tuples)
    assert all(len(ct.grade(t)) == 3 for t in tuples)
    assert len({t.measurement_id for t in tuples}) == 2
    # unsupported group stays a row, the controls stay out of the scored counts
    assert any(g["outcome"] == "unsupported" for g in natives[0]["groups"])
    assert natives[0]["controls"]["ctl-bitflip-injection"] == "F" * 9


def _rewrite(tree, fn):
    path = tree / "cells.jsonl.gz"
    cells = [json.loads(l) for l in gzip.open(path, "rt")]
    fn(cells)
    with gzip.open(path, "wt") as f:
        f.write("\n".join(json.dumps(c) for c in cells) + "\n")


def test_flipped_stored_verdict_does_not_rederive(tree):
    def flip(cells):
        next(c for c in cells if c["shape"] == "M512")["verdict"] = "FAIL"
    _rewrite(tree, flip)
    with pytest.raises(ct.ProjectionError, match="re-derive"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_unclean_aa_is_refused(tree):
    def tamper(cells):
        c = next(c for c in cells if c["shape"] == "M512")
        c["reps"][1] = {"batched_digest": "zz", "serial_digest": "zz", "equal": True}
    _rewrite(tree, tamper)
    with pytest.raises(ct.ProjectionError, match="A/A"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_missing_k_row_is_refused(tree):
    def drop(cells):
        cells[:] = [c for c in cells if not (c["shape"] == "M512" and c["k"] == 9)]
    _rewrite(tree, drop)
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_cell_without_header_is_refused(tree):
    (tree / "group_headers.jsonl").write_text(json.dumps(_header("ctl", "-")) + "\n")
    with pytest.raises(ct.ProjectionError, match="header"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_header_missing_route_knob_echo_is_refused(tree):
    h = _header("mm", "Q8_0", route="cpu[GGML_IQK=1,GGML_ROWEXACT_N=9]")
    (tree / "group_headers.jsonl").write_text(json.dumps(h) + "\n" + json.dumps(_header("ctl", "-")) + "\n")
    with pytest.raises(ct.ProjectionError, match="knob"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_summary_count_mismatch_is_refused(tree):
    s = json.loads((tree / "summary.json").read_text())
    s["n_groups"] = 7
    (tree / "summary.json").write_text(json.dumps(s))
    with pytest.raises(ct.ProjectionError, match="summary"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_addendum_hash_mismatch_is_refused(tree):
    (tree / "cpu_addendum_predictions.md").write_bytes(b"edited after the freeze")
    with pytest.raises(ct.ProjectionError, match="addendum"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_failed_control_is_refused(tree):
    def tamper(cells):
        for c in cells:
            if c["shape"] == "ctl-negative-width-independent" and c["k"] == 4:
                c.update(_cell("CONTROL", "F32", c["shape"], 4, "FAIL"))
    _rewrite(tree, tamper)
    with pytest.raises(ct.ProjectionError, match="controls"):
        reader.native_rows(tree / "cells.jsonl.gz")


def test_projection_of_a_forged_native_is_refused(tree):
    native = dict(reader.native_rows(tree / "cells.jsonl.gz")[0], value=0)
    with pytest.raises(ct.ProjectionError, match="differs"):
        reader.project(native)


def test_foreign_file_emits_nothing(tree):
    other = tree / "other.jsonl.gz"
    other.write_bytes(b"")
    assert reader.native_rows(other) == ()


@pytest.mark.skipif(not (REAL / "cells.jsonl.gz").exists(), reason="stored CPU run absent")
def test_real_stored_cpu_record_rederives():
    natives = reader.native_rows(REAL / "cells.jsonl.gz")
    assert len(natives) == 10
    assert sum(n["value"] for n in natives if n["outcome"] == "fail") == 28 + 62 + 7
    assert sum(n["counts"]["unsupported"] for n in natives if n["outcome"] == "fail") == 72
    for n in natives:
        assert ct.grade(reader.project(n))[:2] == ("Judged", "Located")

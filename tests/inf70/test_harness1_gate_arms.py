"""TD-30d item 2: harness1 rows -> coherence_gate paired verdict (fixtures only; no server)."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2] / "scripts" / "inf70" / "harness1"
sys.path.insert(0, str(HARNESS))
gate_arms = importlib.import_module("gate_arms")

_LIB = Path(os.environ.get("COHERENCE_GATE_LIB", "/mnt/raid0/llm/epyc-inference-research/scripts/lib"))
pytestmark = pytest.mark.skipif(not (_LIB / "coherence_gate" / "gate.py").is_file(),
                                reason="coherence_gate library not found")

GOOD = ("Tile the kernel so each core keeps accumulators in registers while weights stream once, "
        "which cuts memory traffic and lifts decode throughput at depth.")
LOOP = "the the the the the the the the " * 20
ANCHOR = {"arm": "A1", "binary_version": "10303"}


def ids(text):
    return [int(hashlib.md5(w.encode()).hexdigest()[:5], 16) % 90000 + 7 for w in text.split()]


def row(i, text, **kw):
    return {"id": i, "text": text, "token_ids": ids(text), "finish": "stop", "verdict": "COHERENT",
            "sha": "0123456789abcdef", **kw}  # the 16-char prefix `sha` must be ignored


def test_identical_arms_pass_and_short_sha_ignored():
    r = gate_arms.gate_arms([row("a", GOOD)], [row("a", GOOD)], anchor=ANCHOR)
    assert r["schema"] == "epyc.coherence_gate.v1"
    assert r["aggregate"]["gate"] == "PASS" and r["gate_with_drops"] == "PASS"
    assert r["anchor"] == ANCHOR and r["dropped_http_error"] == []


def test_candidate_loop_is_a_regression():
    r = gate_arms.gate_arms([row("a", GOOD)], [row("a", LOOP)], anchor=ANCHOR)
    assert r["aggregate"]["gate"] == "FAIL" and r["gate_with_drops"] == "FAIL"


def test_http_error_rows_dropped_from_both_sides_and_block_pass():
    base = [row("a", GOOD), {"id": "b", "verdict": "HTTP-ERROR", "note": "x"}]
    cand = [row("a", GOOD), row("b", GOOD)]
    r = gate_arms.gate_arms(base, cand, anchor=ANCHOR)
    assert r["dropped_http_error"] == ["b"] and r["aggregate"]["n"] == 1
    assert r["aggregate"]["gate"] == "PASS" and r["gate_with_drops"] == "INCOMPLETE"


def test_diverged_without_truth_is_incomplete():
    r = gate_arms.gate_arms([row("a", GOOD)], [row("a", GOOD + " Also unroll.")], anchor=ANCHOR)
    assert r["aggregate"]["gate"] == "INCOMPLETE"


def test_synthetic_ids_refused_not_judged():
    CG = gate_arms._gate()
    bad = row("a", GOOD)
    bad["token_ids"] = list(range(40))  # step-1 range from 0: the old placeholder
    with pytest.raises((CG.TokenProvenanceError, CG.GateInputError)):
        gate_arms.gate_arms([bad], [row("a", GOOD)], anchor=ANCHOR)


def test_cli_exit_codes_and_out_file(tmp_path):
    b, c = tmp_path / "b.jsonl", tmp_path / "c.jsonl"
    b.write_text(json.dumps(row("a", GOOD)) + "\n")
    c.write_text(json.dumps(row("a", GOOD)) + "\n")
    out = tmp_path / "v.json"
    rc = gate_arms.main(["--base", str(b), "--cand", str(c), "--anchor-arm", "A1",
                         "--anchor-binary", "10303", "--out", str(out)])
    assert rc == 0 and json.loads(out.read_text())["aggregate"]["gate"] == "PASS"
    c.write_text(json.dumps(row("a", LOOP)) + "\n")
    assert gate_arms.main(["--base", str(b), "--cand", str(c), "--anchor-arm", "A1",
                           "--anchor-binary", "10303"]) == 1
    assert gate_arms.main(["--base", str(tmp_path / "missing"), "--cand", str(c),
                           "--anchor-arm", "A1", "--anchor-binary", "10303"]) == 3

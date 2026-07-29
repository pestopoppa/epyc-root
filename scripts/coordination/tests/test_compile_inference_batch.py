"""Tests for compile_inference_batch.py (manifest compiler + validator + --simulate).

Run with the orchestrator venv python (needs jsonschema + pyyaml):
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_compile_inference_batch.py -q
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

# Make the sibling modules importable without packaging.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import batch_ledger as bl  # noqa: E402
import compile_inference_batch as cib  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_ENTRY = REPO_ROOT / "coordination" / "inference-batch" / "entries" / "00-example.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _valid_entry(task_id="T1", phase=0, priority="P1", depends_on=None):
    return {
        "task_id": task_id,
        "title": f"entry {task_id}",
        "provenance": {"owning_handoff": "handoffs/active/foo.md", "checkbox": "F-1"},
        "phase": phase,
        "priority": priority,
        "preconditions": {"depends_on": depends_on or []},
        "execution": {"driver": "command", "concurrency_mode": "serial_noninference"},
        "outcomes": {
            "gate_table": [
                {
                    "gate": "does it pass?",
                    "evidence": "metric",
                    "fork": {
                        "pass": {"next": "DONE_PASS"},
                        "fail": {"next": "FAILED_REVERTED"},
                    },
                }
            ]
        },
        "artifacts": {"outputs": []},
        "ledger": {},
    }


@pytest.fixture
def validator():
    return cib.load_schema(cib.DEFAULT_SCHEMA)


def _write_entry(dir_path: Path, name: str, entry: dict) -> Path:
    p = dir_path / name
    p.write_text(yaml.safe_dump(entry, sort_keys=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Schema round-trip
# ---------------------------------------------------------------------------
def test_schema_is_valid_draft7():
    # load_schema calls Draft7Validator.check_schema internally.
    v = cib.load_schema(cib.DEFAULT_SCHEMA)
    assert v is not None


def test_example_entry_validates(validator):
    assert EXAMPLE_ENTRY.is_file(), "shipped example entry must exist"
    entry = yaml.safe_load(EXAMPLE_ENTRY.read_text(encoding="utf-8"))
    assert cib.validate_entry(entry, validator) == []


def test_stamped_manifest_entry_still_validates(validator):
    # A compiled (entry_hash-stamped) entry must round-trip back through the schema.
    manifest = cib.build_manifest([_valid_entry()])
    stamped = manifest["entries"][0]
    assert stamped["entry_hash"].startswith("sha256:")
    assert cib.validate_entry(stamped, validator) == []


def test_build_manifest_hash_excludes_prior_hash():
    e = _valid_entry()
    m1 = cib.build_manifest([e])
    # Re-stamping an already-stamped entry yields the same hash (hash excludes entry_hash).
    m2 = cib.build_manifest(m1["entries"])
    assert m1["entries"][0]["entry_hash"] == m2["entries"][0]["entry_hash"]


# ---------------------------------------------------------------------------
# Lint-rule rejection (schema-valid but lint-invalid)
# ---------------------------------------------------------------------------
def test_lint_rejects_empty_gate_table(validator):
    e = _valid_entry()
    e["outcomes"]["gate_table"] = []  # schema-valid (array present) but lint-invalid
    schema_errs = [x for x in cib.validate_entry(e, validator) if x.startswith("schema:")]
    lint_errs = [x for x in cib.validate_entry(e, validator) if x.startswith("lint:")]
    assert schema_errs == []
    assert any("gate_table" in x for x in lint_errs)


def test_lint_rejects_blank_owning_handoff(validator):
    e = _valid_entry()
    e["provenance"]["owning_handoff"] = "   "  # blank -> lint failure, schema OK
    errs = cib.validate_entry(e, validator)
    assert any("owning_handoff" in x and x.startswith("lint:") for x in errs)


def test_lint_rejects_blank_checkbox(validator):
    e = _valid_entry()
    e["provenance"]["checkbox"] = ""
    errs = cib.validate_entry(e, validator)
    assert any("checkbox" in x and x.startswith("lint:") for x in errs)


def test_lint_rejects_eval_fanout_without_contention_matrix(validator):
    e = _valid_entry()
    e["preconditions"]["topology"] = {
        "required_topology_hash": "8c8cfcbb13d2611d",
        "contention_matrix": "not_required",
    }
    e["execution"]["concurrency_mode"] = "same_trial_eval_fanout"

    errs = cib.validate_entry(e, validator)

    assert any("eval_fanout entries require" in x and x.startswith("lint:") for x in errs)


# ---------------------------------------------------------------------------
# Schema rejection (structurally malformed)
# ---------------------------------------------------------------------------
def test_schema_rejects_bad_enum(validator):
    e = _valid_entry()
    e["execution"]["driver"] = "not_a_driver"
    errs = cib.validate_entry(e, validator)
    assert any(x.startswith("schema:") for x in errs)


def test_schema_rejects_long_topology_digest(validator):
    e = _valid_entry()
    e["preconditions"]["topology"] = {
        "required_topology_hash": "a" * 64,
        "live_affinity_verified": True,
        "contention_matrix": "not_required",
    }
    errs = [x for x in cib.validate_entry(e, validator) if x.startswith("schema:")]
    assert any("required_topology_hash" in x and "does not match" in x for x in errs)


def test_schema_rejects_wrong_type_and_unknown_key(validator):
    e = _valid_entry()
    e["phase"] = "one"  # must be integer
    e["bogus_top_level"] = 1  # additionalProperties: false
    errs = [x for x in cib.validate_entry(e, validator) if x.startswith("schema:")]
    assert len(errs) >= 2


def test_validate_all_flags_duplicate_task_ids(validator):
    entries = [(Path("a.yaml"), _valid_entry("DUP")), (Path("b.yaml"), _valid_entry("DUP"))]
    valid, invalid = cib.validate_all(entries, validator)
    assert len(valid) == 1
    assert any("duplicate" in " ".join(v) for v in invalid.values())


# ---------------------------------------------------------------------------
# --simulate ordering over a synthetic multi-entry manifest
# ---------------------------------------------------------------------------
def test_simulate_orders_by_phase_priority_deps():
    # Diamond DAG: A -> {B,C} -> D, with phase/priority tie-breaks.
    entries = [
        _valid_entry("D", phase=1, priority="P0", depends_on=["B", "C"]),
        _valid_entry("A", phase=0, priority="P1"),
        _valid_entry("C", phase=1, priority="P1", depends_on=["A"]),
        _valid_entry("B", phase=1, priority="P0", depends_on=["A"]),
    ]
    manifest = cib.build_manifest(entries)
    result = bl.simulate(manifest)
    order = [s["task_id"] for s in result["order"]]
    # A first (phase 0). Then B before C (same phase 1; P0 < P1). Then D (needs B and C).
    assert order == ["A", "B", "C", "D"]
    assert result["unscheduled"] == []


def test_simulate_reports_unschedulable_cycle():
    entries = [
        _valid_entry("X", depends_on=["Y"]),
        _valid_entry("Y", depends_on=["X"]),
    ]
    result = bl.simulate(cib.build_manifest(entries))
    assert result["order"] == []
    assert sorted(result["unscheduled"]) == ["X", "Y"]


def test_simulate_cli_on_example(tmp_path, capsys):
    # --simulate over the shipped example (single entry, empty ledger) prints EX-0.
    rc = cib.main(["--entries-dir", str(EXAMPLE_ENTRY.parent), "--simulate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "EX-0-role-aware-ab" in out
    assert "pick-next" in out


# ---------------------------------------------------------------------------
# CLI: validate exit codes + compile emits artifacts
# ---------------------------------------------------------------------------
def test_validate_cli_exit_nonzero_on_bad_entry(tmp_path):
    d = tmp_path / "entries"
    d.mkdir()
    _write_entry(d, "good.yaml", _valid_entry("G1"))
    bad = _valid_entry("B1")
    bad["outcomes"]["gate_table"] = []  # lint failure
    _write_entry(d, "bad.yaml", bad)
    assert cib.main(["--entries-dir", str(d), "validate"]) == 1


def test_validate_cli_exit_zero_all_valid(tmp_path):
    d = tmp_path / "entries"
    d.mkdir()
    _write_entry(d, "a.yaml", _valid_entry("A1"))
    _write_entry(d, "b.yaml", _valid_entry("B1"))
    assert cib.main(["--entries-dir", str(d), "validate"]) == 0


def test_validate_cli_rejects_duplicate_yaml_keys(tmp_path, capsys):
    d = tmp_path / "entries"
    d.mkdir()
    p = d / "dup.yaml"
    p.write_text(
        """
task_id: DUP
title: first
title: second
provenance:
  owning_handoff: handoffs/active/foo.md
  checkbox: F-1
phase: 0
priority: P1
preconditions:
  depends_on: []
execution:
  driver: command
  concurrency_mode: serial_noninference
outcomes:
  gate_table:
    - gate: does it pass?
      evidence: metric
      fork:
        pass:
          next: DONE_PASS
        fail:
          next: FAILED_REVERTED
artifacts:
  outputs: []
ledger: {}
""",
        encoding="utf-8",
    )

    assert cib.main(["--entries-dir", str(d), "validate"]) == 1
    err = capsys.readouterr().err
    assert "duplicate key 'title'" in err


def test_compile_cli_emits_manifest_and_lock(tmp_path):
    d = tmp_path / "entries"
    d.mkdir()
    out = tmp_path / "out"
    # Copy the real example so checkbox resolution can succeed against the tree.
    example = yaml.safe_load(EXAMPLE_ENTRY.read_text(encoding="utf-8"))
    _write_entry(d, "00-example.yaml", example)
    _write_entry(d, "t1.yaml", _valid_entry("T1", phase=0, priority="P0"))

    rc = cib.main(["--entries-dir", str(d), "--out-dir", str(out), "compile"])
    assert rc == 0

    manifest_path = out / "manifest.yaml"
    lock_path = out / "sources.lock.json"
    assert manifest_path.is_file() and lock_path.is_file()

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["entry_count"] == 2
    ids = [e["task_id"] for e in manifest["entries"]]
    # T1 (phase 0, P0) sorts before EX-0 (phase 2).
    assert ids == ["T1", "EX-0-role-aware-ab"]
    assert all("entry_hash" in e for e in manifest["entries"])

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert set(lock["repos"]) == {
        "epyc-root", "epyc-orchestrator", "epyc-inference-research"
    }
    ex_ref = next(r for r in lock["checkbox_refs"] if r["task_id"] == "EX-0-role-aware-ab")
    # The example points at a real handoff + checkbox -> resolved with a line number.
    assert ex_ref["handoff_exists"] is True
    assert ex_ref["resolved"] is True
    assert isinstance(ex_ref["checkbox_line"], int)


def test_resolve_checkbox_refs_requires_unchecked_anchor(tmp_path):
    handoff = tmp_path / "handoff.md"
    handoff.write_text("EV-4 appears in prose only\\n- [ ] **EV-40 sibling\\n", encoding="utf-8")
    entry = _valid_entry("EV4")
    entry["provenance"] = {
        "owning_handoff": "handoff.md",
        "checkbox": "EV-4",
    }

    ref = cib.resolve_checkbox_refs([entry], tmp_path)[0]

    assert ref["handoff_exists"] is True
    assert ref["checkbox_line"] is None
    assert ref["checkbox_anchor_count"] == 0
    assert ref["resolved"] is False
    assert "missing unchecked checkbox anchor" in ref["checkbox_anchor_error"]


def test_compile_cli_refuses_on_invalid(tmp_path, capsys):
    d = tmp_path / "entries"
    d.mkdir()
    out = tmp_path / "out"
    bad = _valid_entry("B1")
    bad["execution"]["concurrency_mode"] = "bogus"  # schema failure
    _write_entry(d, "bad.yaml", bad)
    rc = cib.main(["--entries-dir", str(d), "--out-dir", str(out), "compile"])
    assert rc == 1
    assert not (out / "manifest.yaml").exists()  # fail-closed: nothing emitted

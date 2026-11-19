"""Regression controls for the exact KPF-17 task context."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))

from canary.kpf17_task_context import CLAIM_ID, CONSUMER, TASK_ID, run
from ledger import Ledger
from loop_beliefs import Target, evaluate_frames

PACKAGE = ROOT / "data/vidya/kpf17-native-20261118"
RAW_TARGET = {"scope": "task", "task_id": TASK_ID}
TARGET = Target.from_mapping(RAW_TARGET)


def test_native_task_context_and_unrelated_targets(tmp_path):
    output = tmp_path / "context"
    receipt = run(PACKAGE, output, check_reader_checkout=False)
    assert receipt["status"] == "PASS"
    assert receipt["frame_count"] == 3
    assert receipt["cases"]["exact-task"]["claims"] == 1
    assert receipt["cases"]["exact-task"]["tried"] == 1
    assert all(case["claims"] == case["tried"] == 0
               for name, case in receipt["cases"].items() if name != "exact-task")
    assert f'"target_key":"task:{TASK_ID}"' in (output / "reads.jsonl").read_text()


@pytest.mark.parametrize("raw", [{"scope": "task"}, {**RAW_TARGET, "model_file": "unrelated.gguf"},
                                 {**RAW_TARGET, "task_id": "*"}])
def test_task_target_parser_requires_an_exact_id_and_no_other_dimensions(raw):
    with pytest.raises(ValueError, match="exact task_id"):
        Target.from_mapping(raw)
    assert TARGET.as_dict() == RAW_TARGET


@pytest.fixture
def frames():
    return [record.frame for record in Ledger(PACKAGE / "review/kpf17-canary-ledger.jsonl").read_all()]


def context(frames, targets):
    return evaluate_frames(frames, targets, as_of="2026-11-19T00:00:00Z", consumer=CONSUMER)


@pytest.mark.parametrize("other", [{"scope": "task", "task_id": "VB-UNRELATED-TASK"},
                                    {"model_file": "unrelated.gguf", "backend": "cpu"}])
def test_task_target_must_be_standalone(frames, other):
    evidence = context(frames, [TARGET, Target.from_mapping(other)])
    assert evidence["reasons"] == ["inapplicable_target"]
    assert evidence["claims"] == evidence["tried_index"] == []


@pytest.mark.parametrize("section,key,value", [
    ("provenance", "method", "foreign.adapter/v1"),
    ("assertion", "locator", "https://example.invalid/native.json"),
    ("assertion", "applicability", {"model_file": "unrelated.gguf"}),
])
def test_task_does_not_route_other_sources(frames, section, key, value):
    edited = deepcopy(frames)
    edited[0][section][key] = value
    evidence = context(edited, [TARGET])
    assert evidence["reasons"] == ["no_applicable_claims"]
    assert evidence["claim_ids"] == evidence["tried_index"] == []


def test_task_selection_cannot_override_grade_floor(frames):
    assert context(frames, [TARGET])["claim_ids"] == [CLAIM_ID]
    edited = deepcopy(frames)
    edited[2]["assertion"]["grade"] = {"Q": "Hinted", "T": "Located"}
    evidence = context(edited, [TARGET])
    assert evidence["claim_ids"] == []
    assert any(reason.startswith("gate_refused:") for reason in evidence["reasons"])

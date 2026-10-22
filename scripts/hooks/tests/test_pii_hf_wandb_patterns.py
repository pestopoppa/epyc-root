"""SEC-SECRETS-1: the real pii_precommit.sh blocks Hugging Face and W&B keys and passes the look-alikes."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"
FIXTURE = ROOT / "research/fixtures/pii_secret_tokens_hf_wandb.jsonl"
ROWS = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


def _load_evaluator():
    spec = importlib.util.spec_from_file_location("pii_fixture_eval_hfw", ROOT / "scripts/validate/pii_fixture_eval.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EVAL = _load_evaluator()


def test_fixture_has_both_sides_for_each_family():
    must = [r["text"] for r in ROWS if r["expected_match"]]
    passes = [r["text"] for r in ROWS if not r["expected_match"]]
    for family in (r"hf_", r"api_org_", r"WANDB|wandb_api_key", r"wandb_v1_", r"wandb login"):
        assert any(re.search(family, t) for t in must), f"no must-block row for {family}"
    assert len(passes) >= 8


@pytest.mark.parametrize("row", ROWS, ids=[f"{i:02d}-{'block' if r['expected_match'] else 'pass'}" for i, r in enumerate(ROWS)])
def test_row(row):
    result = EVAL.evaluate([row], HOOK)[0]
    assert result.actual_block == row["expected_match"], row["text"][:40]


def test_no_false_accept_or_reject_on_whole_fixture():
    sides = EVAL.summarize(EVAL.evaluate(ROWS, HOOK))
    assert sides.fa_errors == 0 and sides.fa_denominator >= 10
    assert sides.fr_errors == 0 and sides.fr_denominator >= 8


def test_existing_fixture_unchanged_by_new_patterns():
    base = EVAL.load_rows(EVAL.DEFAULT_FIXTURE)
    sides = EVAL.summarize(EVAL.evaluate(base, HOOK))
    assert sides.fa_errors == 0 and sides.fr_errors == 0

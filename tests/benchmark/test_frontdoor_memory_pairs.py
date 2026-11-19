"""No inference: controls that prevent a spurious paired memory verdict."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "scripts/benchmark/frontdoor_memory_pairs.py"
spec = importlib.util.spec_from_file_location("frontdoor_memory_pairs", SOURCE)
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)


@pytest.fixture
def run():
    suite = [{"id": "q1", "prompt": "Two plus two?", "answers": ["4", "four"], "seeds": [0, 42]}]
    rows = []
    for seed in (0, 42):
        for arm in ("on", "off"):
            rows.append(dict(id="q1", seed=seed, arm=arm, prompt=suite[0]["prompt"],
                             answer="4" if arm == "on" else "5", latency_s=2 if arm == "on" else 1,
                             mock_mode=False, real_mode=True, episodic_lookups_effective=arm == "on",
                             backend_seed=seed, store_sha256="a" * 64, serving_config_sha256="b" * 64,
                             prompt_tokens=10, output_tokens_reported=2))
    return suite, rows


def test_paired_summary_is_order_independent(run):
    suite, rows = run
    result = scorer.score_pairs(suite, list(reversed(rows)))
    assert result == scorer.score_pairs(suite, rows)
    assert result["on_minus_off_accuracy"] == 1
    assert result["on_minus_off_latency_s"] == 1
    assert result["on_only_correct"] == 2
    assert result["off_only_correct"] == 0
    assert result["arms"]["on"]["prompt_tokens_mean"] == 10
    # The treatment may route to a different model; configuration stays pinned.
    rows[0]["routed_to"] = "architect"
    rows[1]["routed_to"] = "worker"
    assert scorer.score_pairs(suite, rows) == result


@pytest.mark.parametrize("field,value", [
    ("prompt", "other"), ("mock_mode", True), ("real_mode", False),
    ("episodic_lookups_effective", False), ("episodic_lookups_effective", 1),
    ("backend_seed", 9), ("backend_seed", None), ("seed", False),
    ("store_sha256", "c" * 64), ("serving_config_sha256", "d" * 64),
    ("store_sha256", None), ("latency_s", float("nan")),
    ("latency_s", -1), ("latency_s", True), ("answer", None),
    ("prompt_tokens", -1), ("output_tokens_reported", 1.5),
])
def test_bad_receipt_refuses_entire_comparison(run, field, value):
    suite, rows = run
    rows[0][field] = value
    with pytest.raises(ValueError):
        scorer.score_pairs(suite, rows)


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra"])
def test_coverage_refuses_cherry_picking(run, change):
    suite, rows = run
    if change == "missing":
        rows.pop()
    else:
        rows.append(copy.deepcopy(rows[0]))
        if change == "extra":
            rows[-1]["id"] = "unplanned"
    with pytest.raises(ValueError):
        scorer.score_pairs(suite, rows)


def test_missing_cost_is_unknown_not_zero(run):
    suite, rows = run
    del rows[0]["prompt_tokens"]
    result = scorer.score_pairs(suite, rows)
    assert result["arms"]["on"]["prompt_tokens_mean"] is None
    assert result["arms"]["on"]["prompt_tokens_missing"] == 1
    assert result["arms"]["off"]["prompt_tokens_mean"] == 10


def test_suite_binding_and_no_empty_suite(run):
    suite, rows = run
    pin = scorer.score_pairs(suite, rows)["suite_sha256"]
    suite[0]["answers"] = ["four"]
    assert scorer.score_pairs(suite, rows)["suite_sha256"] != pin
    with pytest.raises(ValueError):
        scorer.score_pairs([], [])
    with pytest.raises(ValueError):
        scorer.score_pairs(suite + suite, rows)


def test_cli_rejects_incomplete_data_without_summary(run, tmp_path):
    suite, rows = run
    path = tmp_path / "run.json"
    path.write_text(json.dumps(dict(suite=suite, records=rows[:-1])))
    result = subprocess.run([sys.executable, str(SOURCE), str(path)], capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "incomplete paired coverage" in result.stderr

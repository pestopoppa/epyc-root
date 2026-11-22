"""r8c harness fixes from the r8b CPU canary (FIX-HARNESS, 2026-11-22; docs/design/taskflow-stage1-canary-findings.md r8b)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch, schema, verify  # noqa: E402
from taskflow.harness import local_llm as L  # noqa: E402


# ------------------------------------------------------------------------------------- fix 1: wall budget
def test_wall_budget_scales_with_cpu_rate():
    # r8b medians: prefill 111 tok/s, decode 17.4 tok/s; 80k prompt + 6k output -> 1.25*(720.7+344.8)+120
    assert schema.wall_budget_s({"prefill_tok_s": 111, "decode_tok_s": 17.4}) == 1452
    assert schema.wall_budget_s({"prefill_tok_s": 2000, "decode_tok_s": 60}) == 600           # GPU: floor holds
    assert schema.wall_budget_s({"prefill_tok_s": 10, "decode_tok_s": 1}) == 3600             # cap
    assert schema.wall_budget_s(None) is None and schema.wall_budget_s({"prefill_tok_s": 100}) is None


def test_apply_wall_budget_overrides_only_wall():
    t = {"budget": dict(schema.DEFAULT_BUDGET, ctx=65536)}
    out = schema.apply_wall_budget(t, {"prefill_tok_s": 111, "decode_tok_s": 17.4, "expected_output_tokens": 10000})
    assert out["budget"]["wall_s"] == 1739 and out["budget"]["ctx"] == 65536 and t["budget"]["wall_s"] == 600
    assert schema.apply_wall_budget(t, None) is t

"""ETR-4: `_compact_question_result` must not assume `rubric_threshold_source`.

The field was added by RC-12 after the duck-typed recovery path existed
(`run_e8_quality_baseline_v5._merged_retry_sidecar` hands this function a
`types.SimpleNamespace` rebuilt from a journal row). A legacy or foreign row
has no such attribute, so a bare `r.rubric_threshold_source` raised
AttributeError and broke recovery. The guard is a `getattr`; these tests pin
the behaviour and the structure.
"""

from __future__ import annotations

import ast
import inspect
import sys
import textwrap
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "scripts" / "autopilot"), str(_ROOT / "scripts" / "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eval_tower import _compact_question_result  # noqa: E402


def _legacy_row(**extra) -> types.SimpleNamespace:
    fields = dict(
        question_id="q", qid="q", suite="math", prompt="What is 2+2?", expected="4",
        answer="4", correct=True, error=None, elapsed_s=1.0, tokens_generated=4,
        tools_used=0, tools_called=[], eval_partition="core", host_covariates={},
        retrieval_compaction={}, scoring_method="rubric", route_used="",
        confidence=1.0, confidence_source="binary_correctness_proxy", partial=False,
        degraded=False, exogenous_recovered=False, exogenous_unrecovered=False,
        external_restart=False, retry_count=0, rubric_scores={"overall": 0.8},
        rubric_source="judge", failure_provenance=None,
    )
    fields.update(extra)
    return types.SimpleNamespace(**fields)


def test_row_without_the_attribute_compacts_and_omits_the_key():
    row = _legacy_row()
    assert not hasattr(row, "rubric_threshold_source")
    item = _compact_question_result(row)  # must not raise AttributeError
    assert "rubric_threshold_source" not in item
    assert item["rubric_source"] == "judge"  # the rest of the rubric block survives


def test_row_with_the_attribute_still_serializes_it():
    item = _compact_question_result(_legacy_row(rubric_threshold_source="undeclared-default-0.60"))
    assert item["rubric_threshold_source"] == "undeclared-default-0.60"


def test_empty_or_none_value_is_omitted():
    for value in ("", None):
        item = _compact_question_result(_legacy_row(rubric_threshold_source=value))
        assert "rubric_threshold_source" not in item


def test_no_bare_attribute_read_remains():
    """Structural guard: a future edit cannot reintroduce `r.rubric_threshold_source`."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(_compact_question_result)))
    bare = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "rubric_threshold_source"
        and isinstance(node.value, ast.Name)
        and node.value.id == "r"
    ]
    assert bare == []

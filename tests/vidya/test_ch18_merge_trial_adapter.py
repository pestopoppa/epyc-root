"""CH-18 merge-trial strict reader (VB-CH18-MERGE-TRIAL-WIRE): sealed record projects; pre-hook refused."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import ch18_merge_trial as m  # noqa: E402

LEGACY = Path(__file__).resolve().parents[2] / "docs/reports/kv-cache/kpf191a-ch18-pull-trial-20261105/conflicts.json"
PATHS = ["ggml/src/ggml.c", "src/llama-arch.cpp", "common/arg.cpp", "src/llama-graph.cpp"]


def _rec(**over):
    roots = {}
    for p in PATHS:
        roots[p.split("/")[0]] = roots.get(p.split("/")[0], 0) + 1
    rec = {"schema": m.SCHEMA, "kind": "experimental_merge_trial", "production_base": "a" * 40,
           "upstream_tip": "b" * 40, "merge_strategy": "git merge --no-commit --no-ff",
           "tool": {"name": "git", "version": "2.43.0"}, "completed_at": "2026-11-08T01:02:03Z",
           "state": "complete", "conflict_count": len(PATHS), "conflicting_paths": list(PATHS),
           "conflicts_by_root": roots, "cleanup": {"worktree_removed": True, "merge_aborted": True},
           "limitation": "Unresolved trial merge only; contents have not been reconciled, built or promoted.",
           "content_sha256": ""}
    rec.update(over)
    rec["content_sha256"] = m.seal(rec)
    return rec


def _write(tmp_path, rec):
    p = tmp_path / "merge_trial_x.json"
    p.write_text(json.dumps(rec))
    return p


def test_sealed_record_projects_and_grades(tmp_path):
    (row,) = m.native_rows(_write(tmp_path, _rec()))
    tup = m.project(row)
    assert tup.value == 4 and tup.metric == "ch18_merge_conflicted_paths" and tup.protocol_id == ""
    frames = m.frames_for_path(_write(tmp_path, _rec()), as_of="2026-11-08T00:00:00Z")
    assert frames


@pytest.mark.parametrize("mut", [
    {"conflict_count": 3}, {"upstream_tip": "abc"}, {"tool": {"name": "git"}},
    {"cleanup": {"worktree_removed": True}}, {"conflicts_by_root": {"ggml": 9}},
    {"conflicting_paths": ["/abs/x"], "conflict_count": 1, "conflicts_by_root": {"": 1}},
])
def test_negative_controls_refused(tmp_path, mut):
    rec = _rec(**mut)
    with pytest.raises(ct.ProjectionError):
        m.native_rows(_write(tmp_path, rec))


def test_tampered_seal_refused(tmp_path):
    rec = _rec()
    rec["conflict_count"] = 4
    rec["merge_strategy"] = "other"
    with pytest.raises(ct.ProjectionError):
        m.native_rows(_write(tmp_path, rec))


def test_incomplete_trial_projects_nothing(tmp_path):
    assert m.native_rows(_write(tmp_path, _rec(state="incomplete"))) == ()


def test_real_prehook_record_refused():
    if not LEGACY.is_file():
        pytest.skip("legacy conflicts.json absent")
    with pytest.raises(ct.ProjectionError, match="pre-hook"):
        m.native_rows(LEGACY)

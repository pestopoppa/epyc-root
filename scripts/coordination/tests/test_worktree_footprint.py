"""LOOP-37: per-owner worktree footprint — owner rule, bounded du per call, cache reuse, no guessing."""
import importlib.util
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("worktree_footprint", BASE / "worktree_footprint.py")
wf = importlib.util.module_from_spec(_spec)
sys.modules["worktree_footprint"] = wf
_spec.loader.exec_module(wf)


def test_owner_rule():
    assert wf.owner_of("/x/worktrees/codex-ni-20261025-g1") == "NI"
    assert wf.owner_of("/x/worktrees/ni08-apme13-app") == "NI"
    assert wf.owner_of("/x/worktrees/refactor-app-code-01a16fc3") == "refactor"
    assert wf.owner_of("/x/worktrees/codex3-pareval120") == "codex3"
    assert wf.owner_of("/x/worktrees/rtg57-matrix", "ni/rtg57") == "other"
    assert wf.owner_of("/x/worktrees/foo", "ni08/foo") == "NI"
    assert wf.owner_of("/x/worktrees/mains/codex-ni-research") == "NI"


def _fixture(tmp_path, n=6):
    trees = []
    for i in range(n):
        d = tmp_path / ("codex-ni-t%d" % i if i < 4 else "other-t%d" % i)
        d.mkdir()
        trees.append({"path": str(d), "repo": "r", "branch": ""})
    return trees


def test_du_is_bounded_per_call_and_cache_rotates(tmp_path):
    trees = _fixture(tmp_path)
    calls = []
    du = lambda p: calls.append(p) or 2**30
    cache = str(tmp_path / "c.json")
    kw = dict(cache=cache, du=du, lister=lambda _r: trees, max_du=2, ttl_s=3600)
    r1 = wf.collect(now=10000.0, **kw)
    assert len(calls) == 2 and r1["_meta"]["stale_remaining"] == 4
    assert r1["NI"]["trees"] == 4 and r1["other"]["trees"] == 2
    r2 = wf.collect(now=11010.0, **kw)          # next tick measures the NEXT two, not the same two
    assert len(calls) == 4 and len(set(calls)) == 4
    wf.collect(now=11020.0, **kw)
    assert len(set(calls)) == 6 and len(calls) == 6
    r4 = wf.collect(now=11030.0, **kw)          # fully cached and fresh: zero du
    assert len(calls) == 6 and r4["NI"]["bytes"] == 4 * 2**30 and r4["NI"]["sized"] == 4
    assert r4["_meta"]["stale_remaining"] == 0
    r5 = wf.collect(now=10000.0 + 3601 + 30, **kw)   # TTL expiry re-measures, still bounded
    assert len(calls) == 8


def test_unmeasured_is_reported_not_guessed_and_removed_trees_drop(tmp_path):
    trees = _fixture(tmp_path, 3)
    cache = str(tmp_path / "c.json")
    r = wf.collect(cache=cache, du=lambda p: None, lister=lambda _r: trees, now=100000.0)
    assert r["NI"]["bytes"] == 0 and r["NI"]["sized"] == 0
    assert "0/3 sized" in wf.render_lines(r)[0]
    wf.collect(cache=cache, du=lambda p: 7, lister=lambda _r: trees, now=100100.0)
    os.rmdir(trees[0]["path"])
    r = wf.collect(cache=cache, du=lambda p: 7, lister=lambda _r: trees[1:], now=100200.0)
    assert r["NI"]["trees"] == 2 and r["NI"]["bytes"] == 14


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_worktree_footprint.py -q")


def test_total_budget_stops_du_and_is_reported(tmp_path):
    trees = _fixture(tmp_path)
    calls = []
    ticks = iter([0.0, 1.0, 5.0, 29.0, 31.0, 40.0, 50.0, 60.0, 70.0, 80.0])
    clock = lambda: next(ticks)  # noqa: E731
    du = lambda p: calls.append(p) or 2**30
    r = wf.collect(cache=str(tmp_path / "b.json"), du=du, lister=lambda _r: trees, max_du=6, ttl_s=0,
                   now=10000.0, budget_s=30.0, clock=clock)
    assert 0 < len(calls) < 6                 # some work done, the rest cut off by the budget
    assert r["_meta"]["budget_exhausted"] is True and r["_meta"]["stale_remaining"] > 0


def test_budget_not_exhausted_when_work_is_cheap(tmp_path):
    trees = _fixture(tmp_path)
    r = wf.collect(cache=str(tmp_path / "c2.json"), du=lambda p: 1, lister=lambda _r: trees, max_du=2,
                   ttl_s=0, now=10000.0, budget_s=30.0, clock=lambda: 0.0)
    assert r["_meta"]["budget_exhausted"] is False


def test_list_trees_stops_when_budget_spent():
    assert wf.list_trees(["/nonexistent-repo-a"], remaining=lambda: 0.0) == []

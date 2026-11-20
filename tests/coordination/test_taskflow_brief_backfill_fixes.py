"""Brief backfill pilot fixes (coordinator addendum 2026-11-20, from the 19-brief churn-pipeline pilot 6012592b6):
directory where, pytest option parsing, new_tests, tuple-assignment symbols, --author backfill, assign-id."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
from taskflow import brief as B  # noqa: E402
import handoff_box as HB  # noqa: E402
import handoff_ref as HR  # noqa: E402
import task_lint_core as L1  # noqa: E402

BOX = "- [ ] **BF-1** [non-inference] tidy `scripts/pkg/`"


def _tree(tmp_path, done="python3 scripts/pkg/a.py"):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/h.md").write_text(f"# H\n## Track: T\n### Backlog\n{BOX}\n      · done when: `{done}`\n")
    (tmp_path / "scripts/pkg").mkdir(parents=True)
    (tmp_path / "scripts/pkg/a.py").write_text("A, B = 1, 2\n(C, D) = 3, 4\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("def test_foo():\n    pass\n")
    return tmp_path


def _w(root, **kw):
    a = dict(where=["epyc-root:scripts/pkg/"], approach="x", acceptance="python3 scripts/pkg/a.py", non_goals=[],
             root=root, today="2026-11-20")
    a.update(kw)
    return B.write_brief("BF-1", **a)


def _nogn(mp):
    mp.setenv(B.GITNEXUS_ENV, "")
    B._GN_STATUS.clear()


def test_1_directory_where_records_tree_sha_and_drifts(tmp_path, monkeypatch):
    _nogn(monkeypatch)
    root = _tree(tmp_path)
    doc = B.parse_text(_w(root).read_text())
    assert doc["grounded"]["blobs"]["epyc-root:scripts/pkg/"].startswith("tree:")
    assert B.compile_brief("BF-1", root, use_cache=False)["state"] == "fresh"
    (root / "scripts/pkg/b.py").write_text("x = 1\n")
    assert B.compile_brief("BF-1", root, use_cache=False)["state"] == "drift"


def test_2_pytest_options_not_read_as_paths(tmp_path):
    root = _tree(tmp_path)
    for cmd in ("pytest -q -k foo tests/test_a.py", "pytest -m 'not slow' tests/test_a.py::test_foo",
                "python3 -m pytest --deselect tests/test_a.py::test_x -p no:cacheprovider tests/test_a.py"):
        r = B.acceptance_dry(root, cmd)
        assert r["ok"], (cmd, r)
    assert not B.acceptance_dry(root, "pytest -k foo tests/missing.py")["ok"]


def test_3_new_tests_may_not_exist_yet(tmp_path, monkeypatch):
    _nogn(monkeypatch)
    root = _tree(tmp_path)
    _w(root, where=["epyc-root:scripts/pkg/a.py", "epyc-root:tests/test_new.py"],
       acceptance="pytest -q tests/test_new.py::test_it")
    assert B.compile_brief("BF-1", root, use_cache=False)["state"] == "stale"     # not marked -> honest failure
    _w(root, where=["epyc-root:scripts/pkg/a.py", "epyc-root:tests/test_new.py"],
       acceptance="pytest -q tests/test_new.py::test_it", new_tests=["tests/test_new.py"])
    r = B.compile_brief("BF-1", root, use_cache=False)
    assert r["state"] == "fresh", r["stale_list"]
    assert any(c.get("kind") == "pytest-new" for c in r["checks"])
    assert B.parse_text(B.brief_path(root, "BF-1").read_text())["new_tests"] == ["tests/test_new.py"]


def test_4_tuple_assignment_symbols(tmp_path):
    root = _tree(tmp_path)
    for sym in ("A", "B", "C", "D"):
        assert B._grep_symbol(root, "scripts/pkg/a.py", None, sym), sym
    assert not B._grep_symbol(root, "scripts/pkg/a.py", None, "E")


def test_5_author_backfill(tmp_path, monkeypatch):
    _nogn(monkeypatch)
    root = _tree(tmp_path)
    d = B.parse_text(_w(root, author="backfill").read_text())               # literal done-when -> auto
    assert d["accepted"] == "auto" and d["review"] == "backfill"
    d = B.parse_text(_w(root, author="backfill", acceptance="python3 scripts/pkg/a.py --x").read_text())
    assert d["accepted"] == "pending" and d["review"] == "backfill"
    d = B.parse_text(_w(root, author="owner", acceptance="python3 scripts/pkg/a.py --x").read_text())
    assert d["accepted"] == "owner" and "review" not in d


def test_6_assign_id_mints_records_move_and_is_idempotent(tmp_path):
    act = tmp_path / "handoffs/active"
    act.mkdir(parents=True)
    h = act / "h.md"
    h.write_text("# H\n- [ ] **TU-3** a\n- [ ] **TU-7** b\n- [ ] **Sub-quarter routing** c\n- [ ] plain d\n")
    assert L1.suspect_id(L1.head_id("- [ ] **Sub-quarter routing** c")) and not L1.suspect_id("TU-7")
    r = HB.assign_id(h, 4, root=tmp_path, base=None, today="2026-11-20")
    assert r["id"] == "TU-8" and r["changed"]
    r2 = HB.assign_id(h, 5, root=tmp_path, base=None, today="2026-11-20")
    assert r2["id"] == "TU-9"
    lines = h.read_text().split("\n")
    assert lines[3] == "- [ ] **TU-8** **Sub-quarter routing** c" and lines[4] == "- [ ] **TU-9** plain d"
    assert HB.assign_id(h, 4, root=tmp_path, base=None)["changed"] is False                # idempotent
    moves = [json.loads(l) for l in (act / ".moves.jsonl").read_text().splitlines()]
    assert len(moves) == 2 and moves[0]["op"] == "assign-id" and moves[0]["from"] == moves[0]["to"] == "h.md"
    assert HR.sha_aliases(moves[0]["text_sha"], moves) == {moves[0]["text_sha"], moves[0]["new_text_sha"]}
    try:
        HB.assign_id(h, 2 + 3, root=tmp_path, base=None, new_id="TU-3")
    except HB.BoxError:
        pass
    assert HB.main(["assign-id", str(h), "2", "--base", ""]) == 0                         # already has an ID


def test_6_assign_id_checks_base_branch_ids(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    act = tmp_path / "handoffs/active"
    act.mkdir(parents=True)
    (act / "other.md").write_text("- [ ] **TU-20** on main only\n")
    g = lambda *a: subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)  # noqa: E731
    g("-c", "user.email=t@t", "-c", "user.name=t", "add", "."); g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "b")
    g("update-ref", "refs/remotes/origin/main", "HEAD")
    (act / "other.md").unlink()
    h = act / "h.md"
    h.write_text("- [ ] **TU-3** a\n- [ ] plain\n")
    assert HB.assign_id(h, 2, root=tmp_path, base="origin/main")["id"] == "TU-21"


def test_7_digit_free_and_hyphenated_head_ids_are_valid_never_renamed(tmp_path):
    for t in ("VB-TASKFLOW-BRIEF-WIRE", "B5", "KPF-18.3", "E3b", "SC84a", "D-g", "LRC-RI-CONCURRENCY"):
        assert not L1.suspect_id(t), t
    for t in ("Sub-quarter", "First-party", "Layer-3", "1", "2026-11-20", "Foo"):
        assert L1.suspect_id(t), t
    act = tmp_path / "handoffs/active"
    act.mkdir(parents=True)
    h = act / "h.md"
    h.write_text("# H\n- [ ] **VB-TASKFLOW-BRIEF-WIRE** wire it\n- [ ] **Sub-quarter routing** c\n- [ ] **Overview** d\n")
    r = HB.assign_id(h, 2, root=tmp_path, base=None)
    assert r["changed"] is False and h.read_text().split("\n")[1] == "- [ ] **VB-TASKFLOW-BRIEF-WIRE** wire it"
    assert not (act / ".moves.jsonl").exists()
    assert HB.assign_id(h, 3, root=tmp_path, base=None, today="2026-11-20")["changed"]       # title word: renamed
    assert HB.assign_id(h, 4, root=tmp_path, base=None, today="2026-11-20")["changed"]       # bold plain word: renamed


def test_8_id_suspect_lint_follows_the_fixed_rule(tmp_path):
    import box_index as BI
    assert L1.head_has_valid_id("- [ ] **VB-X-WIRE** a") and not L1.head_has_valid_id("- [ ] **1** a")
    assert not L1.head_has_valid_id("- [ ] plain") and not L1.head_has_valid_id("- [ ] **Overview** a")


def test_9_box_text_sha_written_prefixed_old_form_still_read(tmp_path, monkeypatch):
    _nogn(monkeypatch)
    root = _tree(tmp_path)
    p = _w(root)
    raw = B.parse_text(p.read_text())["box_text_sha"]
    sha = B.find_box(root, "BF-1")["text_sha"]
    assert raw == "t:" + sha and not str(raw).isdigit() and B.sha_norm(raw) == B.sha_norm(sha) == sha
    assert B.cached_state(root, "BF-1", sha)["brief"] != "orphaned"
    p.write_text(p.read_text().replace("t:" + sha, sha))                                    # old bare form still reads
    assert B.cached_state(root, "BF-1", sha)["brief"] != "orphaned"
    p.write_text(p.read_text().replace(sha, str(10**15 + 7), 1))
    assert B.cached_state(root, "BF-1", sha)["brief"] == "orphaned"

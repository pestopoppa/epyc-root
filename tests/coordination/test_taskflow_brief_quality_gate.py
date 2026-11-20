"""Brief write-time quality gate (rules a-e + --force-quality), handoff_box add --brief tier mapping, and decorative
box-ID prefixes (`**★★ NOFOLD-1**`)."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
from taskflow import brief as B  # noqa: E402
import handoff_box  # noqa: E402
import task_lint_core as L1  # noqa: E402

BOX = "- [ ] **QG-1** [non-inference] make parse in `scripts/x.py` strip whitespace"
GOOD = dict(where=["epyc-root:scripts/x.py"], approach="strip surrounding whitespace inside parse before returning",
            acceptance="python3 scripts/x.py", author="owner", today="2026-11-20")


def _tree(tmp_path):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/h.md").write_text(
        f"# H\n## Track: T\n### Backlog\n{BOX}\n      · done when: `python3 scripts/x.py`\n      · gate: none\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/x.py").write_text("def parse(s):\n    return s\n")
    return tmp_path


def _w(root, **kw):
    return B.write_brief("QG-1", **{**GOOD, **kw}, root=root)


def _refused(root, rule, **kw):
    with pytest.raises(ValueError) as e:
        _w(root, **kw)
    assert f"({rule})" in str(e.value)
    assert not B.brief_path(root, "QG-1").exists()


def test_good_brief_passes(tmp_path):
    assert _w(_tree(tmp_path)).exists()


def test_a_tick_only_acceptance(tmp_path):
    _refused(_tree(tmp_path), "a", acceptance=r"grep -q '\[x\] \*\*QG-1' handoffs/active/h.md")


def test_b_short_empty_and_copied_approach(tmp_path):
    r = _tree(tmp_path)
    _refused(r, "b", approach="short")
    _refused(r, "b", approach="make parse in scripts/x.py strip whitespace [non-inference] QG-1 make parse")


def test_c_boilerplate_approach(tmp_path):
    for pre in B.BOILERPLATE_APPROACH_PREFIXES:
        _refused(_tree_once(tmp_path, pre), "c",
                 approach=pre.capitalize() + " something quite specific about the parser internals")


def _tree_once(tmp_path, pre):
    d = tmp_path / ("t" + str(abs(hash(pre))))
    d.mkdir()
    return _tree(d)


def test_d_no_where_resolves(tmp_path):
    _refused(_tree(tmp_path), "d", where=["epyc-root:scripts/gone.py"])


def test_e_duplicate_acceptance_only_with_b_or_c(tmp_path):
    root = _tree(tmp_path)
    d = root / B.BRIEF_DIR
    d.mkdir(parents=True)
    for i in range(3):
        (d / f"O-{i}.md").write_text(f"---\nid: O-{i}\nacceptance: python3 scripts/x.py\n---\n")
    _w(root)                                    # shared acceptance alone is fine (good approach)
    B.brief_path(root, "QG-1").unlink()
    with pytest.raises(ValueError) as e:
        _w(root, approach="Parked tracker: keep an eye on it please")
    assert "(c)" in str(e.value) and "(e)" in str(e.value)


def test_force_quality_records_override(tmp_path):
    root = _tree(tmp_path)
    p = _w(root, approach="short", force_quality="legacy import")
    assert B.parse_text(p.read_text())["quality_override"] == "legacy import"


def test_cli_write_refuses_nonzero(tmp_path, capsys):
    root = _tree(tmp_path)
    rc = B.main(["--root", str(root), "write", "QG-1", "--where", "epyc-root:scripts/x.py", "--approach", "x",
                 "--acceptance", "python3 scripts/x.py"])
    assert rc == 1 and "quality gate" in capsys.readouterr().err


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout


def test_add_brief_with_box_tier_sonnet_writes_brief(tmp_path):
    root = _tree(tmp_path)
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.email", "t@t"); _git(root, "config", "user.name", "t")
    _git(root, "add", "."); _git(root, "commit", "-qm", "b"); _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    rc = handoff_box.main(["add", "--file", str(root / "handoffs/active/h.md"), "--track", "T", "--id", "QG-2",
                           "--class", "non-inference", "--text", "add a thing to `scripts/x.py` now",
                           "--done-when", "`python3 scripts/x.py`", "--tier", "sonnet", "--brief",
                           "--where", "epyc-root:scripts/x.py", "--approach",
                           "extend parse with a strict mode that rejects non-string input", "--acceptance",
                           "python3 scripts/x.py", "--brief-author", "owner"])
    p = root / "handoffs/active/briefs/QG-2.md"
    assert rc == 0 and p.exists() and B.parse_text(p.read_text())["tier"] == "luna"


def test_tier_mapping_and_loud_unmapped():
    assert [handoff_box.brief_tier(t) for t in ("haiku", "sonnet", "opus", "luna", "sol", None)] == \
        ["local", "luna", "terra", "luna", "sol", "local"]
    with pytest.raises(ValueError):
        handoff_box.brief_tier("gpt")


def test_decorative_prefix_box_id():
    for line in ("- [ ] **★★ NOFOLD-1 — x**", "- [ ] **☆ NOFOLD-1: x**", "- [ ] **• 🔥 NOFOLD-1** x"):
        assert L1.head_id(line) == "NOFOLD-1"
    assert L1.head_id("- [ ] **(C1) x**") is None

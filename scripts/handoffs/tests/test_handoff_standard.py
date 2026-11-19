"""Stage A of the handoff standard: task_lint dispatch mode, box-index emitter, diff-scoped gate, handoff_box."""
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import box_index as BI  # noqa: E402
import handoff_box as HB  # noqa: E402
import task_lint as TL  # noqa: E402

STD = ("- [ ] **T-1** [non-inference] wire the scorer into run.py\n"
       "      · done when: pytest tests/test_run.py passes\n"
       "      · gate: T-0        · inputs: `scripts/handoffs/task_lint.py`\n"
       "      · tier: haiku   · owner: mainA")

DOC = """# Fixture
**Status**: ACTIVE — fixture

## Track: alpha
<!-- gate: none -->

### Backlog

- [ ] **A-1** [non-inference] wire the scorer into run.py
      · done when: pytest tests/test_run.py passes
      · gate: none
- [ ] legacy box without id that should do something useful eventually

### Done

- [x] **A-0** done thing ✅ 2026-11-01 [belief: cc]

## Track: beta

- [ ] **B-1** [inference] measure decode t/s of Qwen3.8-27B Q8_0 · gate: A-1, ZZZ-9

## History
"""


# ---- task_lint dispatch ---------------------------------------------------------------------------------------------
def test_parse_fields_and_state():
    r = TL.dispatch_result(STD)
    assert r["id"] == "T-1" and r["class"] == "non-inference" and r["standard"]
    assert r["done_when"] == "pytest tests/test_run.py passes"
    assert r["gate"] == ["T-0"] and r["tier"] == "haiku" and r["owner"] == "mainA"
    assert r["inputs"] == ["scripts/handoffs/task_lint.py"] and r["inputs_missing"] == []
    assert r["state"] == "open"


def test_grammar_fails_only_for_standard_boxes():
    assert "g-done-when" in TL.dispatch_result("- [ ] **T-2** [non-inference] wire it\n      · gate: none")["fails"]
    assert "g-gate-prose" in TL.dispatch_result("- [ ] **T-3** [non-inference] x y z w\n      · done when: ok\n"
                                                "      · gate: after the other thing lands")["fails"]
    legacy = "- [ ] wire the scorer into run.py; done when tests pass"
    assert TL.dispatch_result(legacy)["fails"] == TL.score2(legacy)["fails"]


def test_states():
    assert TL.dispatch_result("- [ ] **F-1** [non-inference] x\n      · ❄ frozen until: GPU2")["state"] == "frozen"
    assert TL.dispatch_result("- [ ] ❄ FROZEN 2026-10-01 — resume only once X")["state"] == "frozen"
    assert TL.dispatch_result("- [ ] **R-1** [roll-up] parent")["state"] == "rollup"
    assert TL.dispatch_result("- [ ] **N-1** something NEEDS-OWNER")["state"] == "needs-owner"


def test_dispatch_agrees_with_report_on_legacy(tmp_path):
    f = tmp_path / "h.md"
    f.write_text(DOC)
    for ln, txt, ch in TL.boxes(str(f)):
        r = TL.dispatch_result(txt, ch)
        if not r["standard"]:
            assert r["ok"] == (not TL.score2(txt, ch)["fails"])


# ---- box index ------------------------------------------------------------------------------------------------------
def _build(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True, exist_ok=True)
    f = tmp_path / "handoffs" / "active" / "fx.md"
    f.write_text(DOC)
    prio = {"rows": {"TST-1": {"rank": 7}}}
    return BI.build(tmp_path, {"fx.md": f}, {"fx.md": "TST-1"}, {"TST-1": True}, prio)


def test_box_index_fields_and_determinism(tmp_path):
    d1 = _build(tmp_path)
    d2 = _build(tmp_path)
    assert BI.dumps(d1) == BI.dumps(d2)
    assert d1["schema"] == "epyc.box-index.v1"
    b = d1["boxes"]
    assert set(k for k in b if not k.startswith("handoffs/")) == {"A-1", "B-1"}
    a1 = b["A-1"]
    assert a1["track"] == "alpha" and a1["pos_in_backlog"] == 1 and a1["row"] == "TST-1" and a1["row_rank"] == 7
    assert a1["gate_open"] is False and a1["lint"]["ok"] in (True, False)
    legacy = next(v for k, v in b.items() if k.startswith("handoffs/"))
    assert legacy["pos_in_backlog"] == 2 and len(legacy["text_sha"]) == BI.TEXT_SHA_LEN
    b1 = b["B-1"]
    assert b1["gate"] == ["A-1", "ZZZ-9"] and b1["gate_open"] and b1["gate_unknown"] == ["ZZZ-9"]
    assert b1["pos_in_backlog"] is None
    assert d1["counts"]["total"] == 3  # ticked boxes excluded (INCLUDE_DONE False)


def test_text_sha_ignores_marker_and_tick():
    assert BI.text_sha("- [ ] **X-1** do it") == BI.text_sha("- [x] **X-1** do it ✅ 2026-11-01 [belief: cc]")


def test_holds(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    (tmp_path / "handoffs" / "active" / "holds.yaml").write_text("holds:\n  - id: H-AK\n    rows: [TST-1]\n")
    f = tmp_path / "handoffs" / "active" / "fx.md"
    f.write_text(DOC)
    d = BI.build(tmp_path, {"fx.md": f}, {"fx.md": "TST-1"}, {}, {})
    assert d["boxes"]["A-1"]["holds"] == ["H-AK"]


# ---- diff-scoped gate -----------------------------------------------------------------------------------------------
def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t"})


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    f = tmp_path / "handoffs" / "active" / "fx.md"
    f.write_text("# x\n\n- [ ] legacy box with no condition at all here\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def test_diff_gate_untouched_legacy_not_judged(repo):
    lines, n = TL.diff_gate(repo, None, "default")
    assert n == 0 and "0 touched" in lines[-1]


def test_diff_gate_fails_a_on_touched_box(repo):
    f = repo / "handoffs" / "active" / "fx.md"
    f.write_text(f.read_text() + "- [ ] **N-1** [non-inference] add another thing to the pipeline\n")
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "default")
    assert n == 1 and any("rule a" in l and "done when:" in l for l in lines)
    assert TL.diff_gate(repo, None, "warn")[1] == 0
    assert TL.diff_gate(repo, None, "off")[1] == 0


def test_diff_gate_f_only_warns(repo):
    f = repo / "handoffs" / "active" / "fx.md"
    f.write_text(f.read_text() + "- [ ] **N-2** [non-inference] fix the thing\n      · done when: tests pass\n"
                 "      · inputs: `scripts/does/not/exist.py`\n")
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "default")
    assert n == 0 and any(l.startswith("WARN") and "rule f" in l for l in lines)


def test_diff_gate_passes_good_box_and_needs_owner(repo):
    f = repo / "handoffs" / "active" / "fx.md"
    f.write_text(f.read_text() + "- [ ] **N-3** [non-inference] fix the thing\n      · done when: pytest passes\n"
                 "- [ ] **N-4** [non-inference] draft thing NEEDS-OWNER\n")
    _git(repo, "add", ".")
    assert TL.diff_gate(repo, None, "default")[1] == 0


def test_diff_gate_env(repo, monkeypatch):
    monkeypatch.setenv(TL.DIFF_GATE_ENV, "off")
    assert TL.diff_gate_mode() == "off"
    monkeypatch.setenv(TL.DIFF_GATE_ENV, "bogus")
    assert TL.diff_gate_mode() == TL.DIFF_GATE_DEFAULT


# ---- handoff_box ----------------------------------------------------------------------------------------------------
@pytest.fixture
def hf(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    f = tmp_path / "handoffs" / "active" / "fx.md"
    f.write_text(DOC)
    return tmp_path, f


def _run(root, f, argv):
    a = HB.parser().parse_args(argv + ["--file", str(f)])
    return HB.apply(f, a.op, a, root=root)


def test_add_under_backlog(hf):
    root, f = hf
    _run(root, f, ["add", "--track", "alpha", "--id", "A-9", "--class", "non-inference", "--text", "do the new thing",
                   "--done-when", "pytest x passes", "--gate", "A-1"])
    lines = f.read_text().split("\n")
    i = next(i for i, l in enumerate(lines) if "**A-9**" in l)
    assert lines.index("### Done") > i > lines.index("### Backlog")
    r = TL.dispatch_result("\n".join(lines[i:i + 3]))
    assert r["done_when"] == "pytest x passes" and r["gate"] == ["A-1"] and "g-done-when" not in r["fails"]


def test_add_creates_backlog_and_refuses_dupes(hf):
    root, f = hf
    _run(root, f, ["add", "--track", "beta", "--id", "B-2", "--class", "non-inference", "--text", "x thing",
                   "--done-when", "y"])
    t = f.read_text()
    assert t.index("## Track: beta") < t.index("### Backlog", t.index("## Track: beta")) < t.index("**B-2**")
    with pytest.raises(HB.BoxError):
        _run(root, f, ["add", "--track", "beta", "--id", "B-2", "--class", "non-inference", "--text", "x",
                       "--done-when", "y"])
    with pytest.raises(HB.BoxError):
        _run(root, f, ["add", "--track", "beta", "--id", "B-3", "--class", "non-inference", "--text", "x"])


def test_split_refine_gate_freeze_keep_first_lines(hf):
    root, f = hf
    first = "- [ ] **A-1** [non-inference] wire the scorer into run.py"
    _run(root, f, ["split", "A-1", "--child", "A-1a::part one::test one passes", "--child", "A-1b::part two::t2"])
    _run(root, f, ["gate", "A-1", "--add", "B-1"])
    _run(root, f, ["freeze", "B-1", "--until", "GPU2"])
    _run(root, f, ["refine", "A-1a", "--new-id", "A-1c", "--text", "part one, better", "--done-when", "t1c"])
    _run(root, f, ["freeze", "--track", "beta", "--until", "ops"])
    t = f.read_text()
    assert first in t.split("\n")
    idx = json.loads(BI.dumps(BI.build(root, {"fx.md": f}, {}, {}, {})))["boxes"]
    assert idx["A-1"]["state"] == "rollup" and idx["A-1"]["gate"] == ["B-1"]
    assert idx["B-1"]["state"] == "frozen" and idx["A-1a"]["state"] == "frozen"
    assert "previous_task_text: **A-1a** [non-inference] part one" in t and "supersedes: A-1a" in t
    assert "❄ frozen until: ops" in t


def test_guard_refuses_first_line_change():
    with pytest.raises(HB.BoxError):
        HB.guard_first_lines(["- [ ] **A** x"], ["- [ ] **A** y"])

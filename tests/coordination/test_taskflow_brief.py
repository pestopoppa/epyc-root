"""Task-brief layer P1: `epyc.brief.v1` + `brief.py compile` (docs/design/task-brief-layer.md §4).

States fresh / drift / stale / orphaned / none, the weak grep fallback when gitnexus is stale or unavailable, the
cache hit, and the self-brief backfill-review flag."""
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
from taskflow import brief as B  # noqa: E402

BOX = "- [ ] **BR-1** [non-inference] fix the parser in `scripts/x.py`"
DONE = "`python3 scripts/x.py`"


def _tree(tmp_path, box=BOX):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/h.md").write_text(
        f"# H\n## Track: T\n### Backlog\n{box}\n      · done when: {DONE}\n      · gate: none\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/x.py").write_text("def parse(s):\n    return s\n")
    return tmp_path


def _write(root, **kw):
    args = dict(where=["epyc-root:scripts/x.py::parse"], approach="make parse strict by rejecting non-string input early", acceptance="python3 scripts/x.py",
                non_goals=["no new deps"], tier="local", author="owner", root=root, today="2026-11-20")
    args.update(kw)
    return B.write_brief("BR-1", **args)


def _no_gitnexus(monkeypatch):
    monkeypatch.setenv(B.GITNEXUS_ENV, "")
    B._GN_STATUS.clear()


def test_none_when_no_sidecar(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    assert B.compile_brief("BR-1", _tree(tmp_path))["state"] == "none"


def test_fresh_and_format(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    p = _write(root)
    doc = B.parse_text(p.read_text())
    assert doc["schema"] == "epyc.brief.v1" and B.sha_norm(doc["box_text_sha"]) == B.find_box(root, "BR-1")["text_sha"]
    assert doc["accepted"] == "auto"            # acceptance == the literal done-when command (D3)
    assert set(B.REQUIRED) <= set(doc)
    r = B.compile_brief("BR-1", root)
    assert r["state"] == "fresh", r["stale_list"]
    assert r["acceptance_matches_done_when"] is True


def test_cache_hit(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    _write(root)
    assert B.compile_brief("BR-1", root)["cache"] == "miss"
    r = B.compile_brief("BR-1", root)
    assert r["cache"] == "hit" and r["state"] == "fresh"
    assert B.cached_state(root, "BR-1", r["box"]["text_sha"])["brief"] == "fresh"


def test_drift_when_file_changes_but_checks_pass(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    _write(root)
    (root / "scripts/x.py").write_text("def parse(s):\n    return s.strip()\n")
    r = B.compile_brief("BR-1", root)
    assert r["state"] == "drift" and r["drifted"] == ["epyc-root:scripts/x.py"]


def test_stale_on_missing_symbol_path_or_acceptance(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    _write(root, where=["epyc-root:scripts/x.py::nosuch", "epyc-root:scripts/gone.py"],
           acceptance="pytest -q tests/missing_test.py")
    r = B.compile_brief("BR-1", root)
    assert r["state"] == "stale"
    s = "\n".join(r["stale_list"])
    assert "nosuch" in s and "gone.py" in s and "acceptance" in s
    assert B.main(["--root", str(root), "compile", "BR-1"]) == 1


def test_orphaned_when_box_text_changes(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    _write(root)
    h = root / "handoffs/active/h.md"
    h.write_text(h.read_text().replace("fix the parser", "rewrite the parser"))
    r = B.compile_brief("BR-1", root)
    assert r["state"] == "orphaned" and "box_text_sha" in r["stale_list"][0]


def test_weak_fallback_when_gitnexus_unavailable(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    _write(root)
    r = B.compile_brief("BR-1", root, use_cache=False)
    sym = [c for c in r["checks"] if c.get("where", "").endswith("::parse")][0]
    assert r["state"] == "fresh" and r["weak"] and sym["strength"] == "weak" and "unavailable" in sym["detail"]


def test_weak_fallback_when_gitnexus_stale(tmp_path, monkeypatch):
    fake = tmp_path / "fake-gitnexus"
    fake.write_text("#!/bin/bash\nif [ \"$1\" = status ]; then echo 'Status: stale (re-run gitnexus analyze)'; fi\n"
                    "exit 0\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv(B.GITNEXUS_ENV, str(fake))
    B._GN_STATUS.clear()
    root = _tree(tmp_path / "t")
    _write(root)
    r = B.compile_brief("BR-1", root, use_cache=False)
    sym = [c for c in r["checks"] if c.get("where", "").endswith("::parse")][0]
    assert sym["strength"] == "weak" and "stale" in sym["detail"] and r["state"] == "fresh"


def test_strong_when_gitnexus_fresh(tmp_path, monkeypatch):
    fake = tmp_path / "fake-gitnexus"
    fake.write_text("#!/bin/bash\ncase $1 in status) echo 'Status: up-to-date';; context) echo 'parse scripts/x.py:1';;"
                    " impact) echo 'Risk: LOW';; esac\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv(B.GITNEXUS_ENV, str(fake))
    B._GN_STATUS.clear()
    root = _tree(tmp_path / "t")
    _write(root)
    r = B.compile_brief("BR-1", root, use_cache=False)
    assert not r["weak"] and r["blast_radius"] == {"parse": "LOW"}


def test_self_brief_flagged_for_backfill_review(tmp_path, monkeypatch):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    p = _write(root, author="self")
    doc = B.parse_text(p.read_text())
    assert doc["review"] == "backfill" and doc["accepted"] == "pending"
    B.set_accepted("BR-1", "owner", root)
    doc = B.parse_text(p.read_text())
    assert doc["accepted"] == "owner" and "review" not in doc


def test_sweep_stale_list(tmp_path, monkeypatch, capsys):
    _no_gitnexus(monkeypatch)
    root = _tree(tmp_path)
    _write(root, where=["epyc-root:scripts/gone.py"], force_quality="fixture: deliberately stale where")
    assert B.main(["--root", str(root), "sweep", "--stale-list"]) == 0
    assert "BR-1: stale" in capsys.readouterr().out

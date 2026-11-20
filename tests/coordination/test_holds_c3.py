"""Handoff standard Stage C, C3: holds.yaml is the single exclusion source; every reader derives from it."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "coordination" / "rowflow"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
import holds as H  # noqa: E402
import box_index  # noqa: E402
from taskflow import select as S  # noqa: E402


def _write(root: Path, holds):
    p = root / "handoffs/active/holds.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({"holds": holds}))
    return p


AKAGG = {"id": "akagg", "scope": "loop-launch", "sessions": ["akagg"], "handoffs": ["kc.md"], "reason": "AK held"}


def test_sync_registry_sets_and_clears_cached_gate(tmp_path):
    reg = {"sessions": {"akagg": {}, "other": {}, "legacy": {"operator_gate": {"reason": "old"}}}}
    _write(tmp_path, [AKAGG])
    assert H.sync_registry(reg, H.load(str(tmp_path))) == ["akagg"]
    assert reg["sessions"]["akagg"]["operator_gate"]["hold"] == "akagg"
    assert "operator_gate" not in reg["sessions"]["other"]
    _write(tmp_path, [])
    assert H.sync_registry(reg, H.load(str(tmp_path))) == ["akagg"]
    assert "operator_gate" not in reg["sessions"]["akagg"]
    assert reg["sessions"]["legacy"]["operator_gate"] == {"reason": "old"}   # legacy gates untouched
    assert H.sync_registry(reg, None) == []                                   # no file: no-op


def test_gate_and_unpark_write_holds_yaml(tmp_path):
    root = str(tmp_path)
    (tmp_path / "handoffs/active").mkdir(parents=True)
    H.add_session_hold("h0", "promotion", "2026-11-20T00:00Z", handoff="handoffs/active/h0.md", root=root)
    hl = H.load(root)
    assert [h["id"] for h in hl] == ["h0"] and hl[0]["handoffs"] == ["h0.md"] and not H.validate(hl)
    H.add_session_hold("h0", "again", "x", root=root)                        # idempotent
    assert len(H.load(root)) == 1
    assert H.remove_session_hold("h0", root=root) and H.load(root) == []


def test_handoff_sessions_gate_cli_writes_the_file(tmp_path, monkeypatch):
    import handoff_sessions as hs
    F = tmp_path / "flags"
    F.mkdir()
    (F / "handoff-sessions.json").write_text(json.dumps({"sessions": {"h0": {"handoff": "handoffs/active/h0.md"}}}))
    hroot = tmp_path / "hr"
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(hroot))
    (hroot / "handoffs/active").mkdir(parents=True)
    assert hs.main(["gate", "h0", "--reason", "v11", "--flags", str(F)]) == 0
    assert [h["id"] for h in H.load(str(hroot))] == ["h0"]
    e = json.loads((F / "handoff-sessions.json").read_text())["sessions"]["h0"]
    assert e["operator_gate"]["source"] == "holds.yaml" and hs.tg.is_gated(e)


def test_box_index_holds_match_session_stem_box_id_and_text_sha(tmp_path):
    sha = box_index.text_sha("- [ ] **B-2** two")
    _write(tmp_path, [AKAGG, {"id": "box", "scope": "boxes", "boxes": ["B-1", sha]}])
    hl = box_index.load_holds(tmp_path)
    assert {h["id"]: h["scope"] for h in hl} == {"akagg": "loop-launch", "box": "boxes"}
    assert box_index.holds_on(hl, "akagg.md", None, None, "x") == ["akagg"]      # session slug -> <slug>.md
    assert box_index.holds_on(hl, "kc.md", None, None, "x") == ["akagg"]         # handoff target
    assert box_index.holds_on(hl, "f.md", None, "B-1", "x") == ["box"]
    assert box_index.holds_on(hl, "f.md", None, None, sha) == ["box"]
    assert box_index.holds_on(hl, "f.md", "RTG-1", "Z-1", "y") == []


def test_select_yields_zero_from_a_held_file():
    assert S.EXCLUDE_FILES == ()                                               # no private list
    rec = {"file": "handoffs/active/kc.md", "state": "open", "class": "non-inference", "holds": ["akagg"],
           "lint": {"ok": True}, "line": 1}
    cands, hist = S.candidates({"boxes": {"K-1": rec}})
    assert cands == [] and hist["held"] == 1


def test_publish_row_admits_by_row_owner(tmp_path):
    import publish_row as pr
    _write(tmp_path, [AKAGG])
    h = pr.load_holds(str(tmp_path))[0]
    assert pr.hold_refuses(h, {"id": "r1", "owner": "autokernel", "handoff_task": "kc.md:K-1"}, "kc.md", str(tmp_path)) is None
    assert "akagg" in pr.hold_refuses(h, {"id": "r2", "owner": "handoff-akagg", "handoff_task": "kc.md:K-1"}, "kc.md",
                                      str(tmp_path))


def test_validate_flags_bad_scope_and_empty_targets():
    errs = H.validate([{"id": "a", "scope": "everything", "sessions": ["x"]}, {"id": "b"}, {"id": "a", "rows": "R"}])
    assert any("scope" in e for e in errs) and any("no targets" in e for e in errs)
    assert any("duplicate" in e for e in errs) and any("must be a list" in e for e in errs)


def test_repo_holds_file_is_valid_and_covers_the_former_exclude_list():
    hl = H.load(str(ROOT))
    assert hl and not H.validate(hl)
    covered = {Path(f).name for h in hl for f in h.get("handoffs") or []}
    for f in ("autokernel-loop.md", "autokernel-akx-program.md", "autopilot-program.md",
              "kernel-champion-and-promotion.md", "v11-promotion-checklist.md"):
        assert f in covered
    assert "stack-lifecycle-program" in H.held_sessions(hl)                   # dispatcher-only: a session hold
    assert {p for h in hl for p in h.get("row_prefixes") or []} >= {"v11-", "v12-"}

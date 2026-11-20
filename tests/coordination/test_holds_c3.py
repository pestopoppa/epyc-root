"""Handoff standard Stage C, C3: holds.yaml is the single exclusion source; every reader derives from it."""
import json
import os
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
    assert e["operator_gate"]["source"] == "operator" and hs.tg.is_gated(e)


def test_box_index_holds_match_session_stem_box_id_and_text_sha(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
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
    cands, hist = S.candidates({"boxes": {"K-1": rec}, "holds_source": "handoffs/active/holds.yaml"})
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


# ---- fail-closed requirements (coordinator, 2026-11-20) ----
def _gated_reg():
    return {"sessions": {"akagg": {"operator_gate": {"reason": "AK", "source": "holds.yaml", "hold": "akagg"}},
                         "op": {"operator_gate": {"reason": "v11", "source": "operator"}}}}


def test_missing_file_keeps_the_gates(tmp_path, capsys):
    reg = _gated_reg()
    assert H.load(str(tmp_path)) is None and "HOLDS-SOURCE-MISSING" in capsys.readouterr().err
    assert H.sync_registry(reg, H.load(str(tmp_path))) == []
    assert all(e.get("operator_gate") for e in reg["sessions"].values())


def test_corrupt_file_keeps_the_gates(tmp_path):
    for bad in ("holds: [unterminated", "just a string", "holds: nope"):
        p = tmp_path / "handoffs/active/holds.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(bad)
        reg = _gated_reg()
        assert H.load(str(tmp_path)) is None
        assert H.sync_registry(reg, H.load(str(tmp_path))) == [] and all(e.get("operator_gate") for e in reg["sessions"].values())
        assert box_index.load_holds(tmp_path) is None


def test_select_fails_closed_without_a_holds_source():
    rec = {"file": "handoffs/active/x.md", "state": "open", "class": "non-inference", "holds": [], "lint": {"ok": True}}
    cands, hist = S.candidates({"boxes": {"X-1": rec}, "holds_source": None})
    assert cands == [] and hist["holds-source-missing"] == 1
    assert S.candidates({"boxes": {"X-1": rec}, "holds_source": "handoffs/active/holds.yaml"})[0]


def test_publish_row_missing_file_keeps_registry_gates_and_default_prefixes(tmp_path, monkeypatch, capsys):
    import publish_row as pr
    monkeypatch.setattr(pr, "config_path", lambda rel, repo=None: str(tmp_path / rel))
    assert pr.load_holds() == [] and "HOLDS-SOURCE-MISSING" in capsys.readouterr().err
    reg = {"sessions": {"akagg": {"operator_gate": {"reason": "AK"}, "handoff": "handoffs/active/kc.md"}}}
    h = pr.registry_holds(reg)[0]
    assert pr.hold_refuses(h, {"id": "r", "owner": "akagg"}, "kc.md", str(tmp_path))
    flags = tmp_path / "flags"
    flags.mkdir()
    import rowflow as rf
    try:
        pr.check_operator_gate({"id": "v11-x", "owner": "a", "handoff_task": "y.md:Y-1"}, str(flags))
        raise AssertionError("v11- row admitted without holds.yaml")
    except rf.Refused as ex:
        assert "v11-" in str(ex)


def test_hub_copy_wins_over_a_stale_checkout(tmp_path, monkeypatch):
    import toolroot
    hub, stale = tmp_path / "hub", tmp_path / "stale"
    _write(hub, [AKAGG])
    _write(stale, [])
    monkeypatch.delenv("EPYC_HOLDS_ROOT", raising=False)
    monkeypatch.setattr(toolroot, "HUB", str(hub))
    assert H.path() == str(hub / "handoffs/active/holds.yaml")
    assert [h["id"] for h in H.load()] == ["akagg"]


def _flags_with(tmp_path, sessions):
    F = tmp_path / "flags"
    F.mkdir(exist_ok=True)
    (F / "handoff-sessions.json").write_text(json.dumps({"sessions": sessions}))
    return F


def test_gate_via_subcommand_survives_reload_even_if_hub_file_lacks_it(tmp_path, monkeypatch):
    import handoff_sessions as hs
    F = _flags_with(tmp_path, {"h0": {"handoff": "handoffs/active/h0.md"}})
    write_root, hub = tmp_path / "w", tmp_path / "hub"
    (write_root / "handoffs/active").mkdir(parents=True)
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(write_root))
    assert hs.main(["gate", "h0", "--reason", "v11", "--flags", str(F)]) == 0
    _write(hub, [])                                   # the reader's copy does NOT carry the new hold yet
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(hub))
    reg = json.loads((F / "handoff-sessions.json").read_text())
    hs.sync_holds(str(F), reg)
    assert hs.tg.is_gated(reg["sessions"]["h0"]) and reg["sessions"]["h0"]["operator_gate"]["source"] == "operator"


def test_unpark_still_requires_release_with_allow_unpark(tmp_path, monkeypatch):
    import handoff_sessions as hs
    F = _flags_with(tmp_path, {"h0": {"handoff": "handoffs/active/h0.md"}})
    (tmp_path / "w/handoffs/active").mkdir(parents=True)
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path / "w"))
    assert hs.main(["gate", "h0", "--reason", "v11", "--flags", str(F)]) == 0
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 3
    d = F / "operator-ratify"
    d.mkdir()
    rel = {"slug": "h0", "by": "operator", "at": "2026-11-20T00:00:00Z", "reason": "ok"}
    (d / "h0.json").write_text(json.dumps(rel))
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 3          # release without allow_unpark
    (d / "h0.json").write_text(json.dumps({**rel, "allow_unpark": True}))
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 0
    assert not hs.tg.is_gated(json.loads((F / "handoff-sessions.json").read_text())["sessions"]["h0"])
    assert H.load(str(tmp_path / "w")) == []


# ---- Fable C3 review S1/S2 (2026-11-20) ----
FIX = ("# F\n**Status**: ACTIVE — x\n\n## Track: t\n\n### Backlog\n\n"
       "- [ ] **F-1** [non-inference] fix the parser\n      · done when: pytest b passes\n")


def _build(root: Path):
    (root / "handoffs/active").mkdir(parents=True, exist_ok=True)
    f = root / "handoffs/active/fx.md"
    f.write_text(FIX)
    return box_index.build(root, {"fx.md": f}, {"fx.md": "TST-1"}, {"TST-1": True}, {"rows": {"TST-1": {"rank": 1}}})


def test_corrupt_file_admits_zero_boxes_pops_zero_gates_refuses_v11(tmp_path, monkeypatch):
    import publish_row as pr
    import rowflow as rf
    monkeypatch.delenv("EPYC_HOLDS_ROOT", raising=False)
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/holds.yaml").write_text("holds: [oops")
    doc = _build(tmp_path)
    assert all(r["holds"] == [box_index.HOLDS_UNAVAILABLE] for r in doc["boxes"].values())
    assert S.candidates(doc)[0] == [] and doc["holds_source"] is None
    reg = _gated_reg()
    assert H.sync_registry(reg, H.load(str(tmp_path))) == [] and all(e.get("operator_gate") for e in reg["sessions"].values())
    monkeypatch.setattr(pr, "config_path", lambda rel, repo=None: str(tmp_path / rel))
    flags = tmp_path / "flags"
    flags.mkdir()
    try:
        pr.check_operator_gate({"id": "v11-x", "owner": "a", "handoff_task": "fx.md:F-1"}, str(flags))
        raise AssertionError("v11 admitted with a corrupt holds file")
    except rf.Refused:
        pass


def test_missing_file_admits_zero_boxes(tmp_path, monkeypatch):
    monkeypatch.delenv("EPYC_HOLDS_ROOT", raising=False)
    doc = _build(tmp_path)
    assert all(r["holds"] == [box_index.HOLDS_UNAVAILABLE] for r in doc["boxes"].values())
    assert S.candidates(doc)[0] == []


def test_valid_file_admits(tmp_path, monkeypatch):
    monkeypatch.delenv("EPYC_HOLDS_ROOT", raising=False)
    _write(tmp_path, [])
    doc = _build(tmp_path)
    assert [k for k, _ in S.candidates(doc)[0]] == ["F-1"]


def test_rocm_hold_admits_autokernel_rows_but_select_skips_boxes(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(ROOT))
    import publish_row as pr
    hl = H.load(str(ROOT))
    rocm = next(h for h in hl if h["id"] == "rocm-kernel-authoring")
    assert rocm["scope"] == "loop-launch"
    h = next(x for x in pr.load_holds(str(ROOT)) if x["id"] == "rocm-kernel-authoring")
    spec = {"id": "rk-1", "owner": "autokernel", "handoff_task": "rocm-kernel-authoring.md:RK-1"}
    assert pr.hold_refuses(h, spec, "rocm-kernel-authoring.md", str(ROOT)) is None
    assert pr.hold_refuses(h, {**spec, "owner": "handoff-agentic-rocm-kernel-authoring"}, "rocm-kernel-authoring.md",
                           str(ROOT))
    bh = [x for x in box_index.load_holds(ROOT) if x["id"] == "rocm-kernel-authoring"]
    assert box_index.holds_on(bh, "rocm-kernel-authoring.md", "INF-48", "RK-1", "x") == ["rocm-kernel-authoring"]


def test_index_check_flags_unreadable_holds(tmp_path, monkeypatch):
    import index_state as I
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/holds.yaml").write_text("::: not yaml [")
    monkeypatch.setattr(I, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    assert any("unreadable" in e for e in I.hold_problems({"rows": {}}, {}))
    (tmp_path / "handoffs/active/holds.yaml").unlink()
    assert any("missing" in e for e in I.hold_problems({"rows": {}}, {}))


def test_backlog_row_check_refuses_held_and_unavailable_boxes(tmp_path):
    import backlog_row_check as brc
    act = tmp_path / "handoffs/active"
    act.mkdir(parents=True)
    line = "- [ ] **K-1** [non-inference] fix the thing"
    (act / "kc.md").write_text(f"# K\n\n{line}\n      · done when: pytest passes\n")
    for hold in ("akagg", box_index.HOLDS_UNAVAILABLE):
        brc._BOX_INDEX_CACHE.clear()
        (act / ".box-index.json").write_text(json.dumps({"boxes": {"K-1": {
            "file": "handoffs/active/kc.md", "text_sha": box_index.text_sha(line), "state": "open", "holds": [hold]}}}))
        code, why = brc.classify(act / "kc.md", 3, " ", line[6:], "K")
        assert code == 2 and hold in why[0]


def test_index_check_flags_a_corrupt_hub_copy(tmp_path, monkeypatch):
    """Fable S2: --check validates the hub-first copy the readers resolve, not only the checkout's."""
    import index_state as I
    import toolroot
    repo, hub = tmp_path / "repo", tmp_path / "hub"
    _write(repo, [])
    (hub / "handoffs/active").mkdir(parents=True)
    (hub / "handoffs/active/holds.yaml").write_text("holds: [broken")
    monkeypatch.setattr(I, "REPO_ROOT", repo)
    monkeypatch.delenv("EPYC_HOLDS_ROOT", raising=False)
    monkeypatch.setattr(toolroot, "HUB", str(hub))
    errs = I.hold_problems({"rows": {}}, {})
    assert any("unreadable" in e and str(hub) in e for e in errs)
    (hub / "handoffs/active/holds.yaml").write_text("holds: []\n")
    assert I.hold_problems({"rows": {}}, {}) == []


def test_proposals_pending_event_once_per_day(tmp_path):
    """C1: 0 -> >0 pending proposals queues ONE proposals-pending event; again only after 24 h; retired owners skipped."""
    import handoff_sessions as hs
    S = {"h0": {"handoff": "handoffs/active/h0.md"}, "old": {"handoff": "handoffs/active/h1.md", "status": "retired"}}
    st, F = {}, str(tmp_path)
    pend = {"h0.md": ["A-1.p1", "A-2.p1"], "h1.md": ["B-1.p1"]}
    hs.proposals_events(F, st, S, 1000.0, pend, held=set())
    q = [x for x in st["queue"] if x["kind"] == "proposals-pending"]
    assert [x["slug"] for x in q] == ["h0"] and q[0]["data"]["ids"] == ["A-1.p1", "A-2.p1"]
    st["queue"] = []
    hs.proposals_events(F, st, S, 1000.0 + 3600, pend, held=set())
    assert st["queue"] == []                                   # within 24 h: no second turn
    hs.proposals_events(F, st, S, 1000.0 + 25 * 3600, pend, held=set())
    assert [x["slug"] for x in st["queue"]] == ["h0"]
    p = hs.proposals_prompt("h0", S["h0"], F, {"ids": ["A-1.p1"]})
    assert "accept / edit" in p.lower() or "Accept / edit" in p
    hs.proposals_events(F, st, S, 1000.0 + 26 * 3600, {}, held=set())
    assert "h0" not in st["proposals_seen"]                    # cleared when nothing is pending



# ---- owner spawn for ownerless handoffs (operator 2026-11-20: ownership belongs to the handoff) ----
def _flags(tmp_path):
    (tmp_path / "f").mkdir()
    return str(tmp_path / "f")


def test_retired_owner_leads_to_a_spawn_queued_and_logged(tmp_path, monkeypatch):
    import handoff_sessions as hs
    F = _flags(tmp_path)
    st, S = {}, {"old": {"handoff": "handoffs/active/h1.md", "status": "retired"}}
    hs.proposals_events(F, st, S, 1000.0, {"h1.md": ["B-1.p1"]}, held=set())
    ev = st["unowned"]["handoffs/active/h1.md"]
    assert ev[0]["kind"] == "proposals-pending" and ev[0]["data"]["ids"] == ["B-1.p1"]
    assert "OWNER-SPAWN-QUEUED handoffs/active/h1.md" in open(os.path.join(F, "handoff-sessions.log")).read()
    # start_handoff: the new session's FIRST prompt is the proposals review; the event is consumed; OWNER-SPAWNED logged
    sent = []
    monkeypatch.setattr(hs, "free_gib", lambda: 10 ** 6)
    monkeypatch.setattr(hs, "brief_text", lambda slug, e, flags: "BRIEF")

    def fake_go(flags, slug, e, prompt, runner, sid, fresh=False):
        sent.append(prompt)
        e["status"] = "live"
        return True
    monkeypatch.setattr(hs, "_go", fake_go)
    reg = {"sessions": dict(S)}
    slug = hs.start_handoff(F, reg, {"handoff": "handoffs/active/h1.md"}, None, st, 0, 2)
    assert slug and "NEEDS-OWNER proposal" in sent[0] and "accept / edit" in sent[0].lower().replace("accept / edit /", "accept / edit")
    assert st["unowned"]["handoffs/active/h1.md"] == []
    assert f"OWNER-SPAWNED {slug} handoff=handoffs/active/h1.md reason=proposals-pending" in \
        open(os.path.join(F, "handoff-sessions.log")).read()


def test_held_handoff_no_spawn(tmp_path):
    import handoff_sessions as hs
    F = _flags(tmp_path)
    st = {}
    hs.proposals_events(F, st, {}, 1000.0, {"autokernel-loop.md": ["AK-1.p1"]}, held={"autokernel-loop.md"})
    assert not (st.get("unowned") or {}).get("handoffs/active/autokernel-loop.md")
    assert "OWNER-SPAWN-REFUSED" in open(os.path.join(F, "handoff-sessions.log")).read()
    st2 = {}
    hs.proposals_events(F, st2, {}, 1000.0, {"x.md": ["X-1.p1"]}, held={"*"})     # unknown hold state: fail closed
    assert not (st2.get("unowned") or {}).get("handoffs/active/x.md")


def test_suspended_owner_is_woken_not_replaced(tmp_path):
    import handoff_sessions as hs
    F = _flags(tmp_path)
    st = {}
    S = {"h0": {"handoff": "handoffs/active/h0.md", "parked": {"reason": "no progress evidence: x"}}}
    hs.proposals_events(F, st, S, 1000.0, {"h0.md": ["A-1.p1"]}, held=set())
    assert [x["slug"] for x in st["queue"] if x["kind"] == "proposals-pending"] == ["h0"]
    assert not (st.get("unowned") or {}).get("handoffs/active/h0.md")


def test_owner_spawn_daily_cap(tmp_path):
    import handoff_sessions as hs
    F = _flags(tmp_path)
    st = {}
    hs.proposals_events(F, st, {}, 1000.0, {"h9.md": ["Z-1.p1"]}, held=set())
    st["unowned"]["handoffs/active/h9.md"] = []          # the spawn happened (event consumed), owner later retired
    hs.proposals_events(F, st, {}, 1000.0 + 3600, {"h9.md": ["Z-1.p1"]}, held=set())
    assert st["unowned"]["handoffs/active/h9.md"] == []   # within 24 h: no second spawn
    hs.proposals_events(F, st, {}, 1000.0 + 25 * 3600, {"h9.md": ["Z-1.p1"]}, held=set())
    assert len(st["unowned"]["handoffs/active/h9.md"]) == 1

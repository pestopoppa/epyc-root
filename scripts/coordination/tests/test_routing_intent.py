#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Routing-intent tests: needs_routing_to / action_required / triage / prose lint.

Why these exist (2026-07-29): two routed messages were missed because routing
intent lived as PROSE inside payload — "FOR FABLE-AUDITOR RELEVANT TO THE C9
REVIEW IN FLIGHT" inside a defect_3 string, and an "action: DOC FIX requested …
operator-directed relay" — and a context-economy payload truncation cut exactly
the sentences carrying the intent. These tests pin the structural replacement:

  1. schema + append accept and enforce the two top-level fields;
  2. `triage` prints routed messages IN FULL, survives cursor advancement, sees
     undelivered outbox-only messages, and clears only on corr_id disposition
     (bare ack clears reach-only, never action_required);
  3. `validate` warns on the exact prose shapes that failed.

Every case runs against a throwaway copy of the real bus (real schema, real
roster) — the live bus is never touched.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination.session_bus import main  # noqa: E402

BUS_SRC = REPO_ROOT / "coordination" / "session-bus"

# Real roster ids (from the copied config.yaml) so validate's roster checks work.
SENDER = "claude-gpu-lane"
TARGET = "fable-auditor"
OTHER = "codex"
DAEMON = "coordinator-daemon"

LONG_MARKER = "NEEDLE-" + "x" * 3000 + "-ENDNEEDLE"


def make_bus(tmp_path: Path) -> Path:
    root = tmp_path / "bus"
    shutil.copytree(BUS_SRC, root)
    (root / "queue.jsonl").write_text("")
    for area in ("inbox", "outbox", "heartbeats", "cursors"):
        for f in (root / area).glob("*"):
            f.unlink()
    for agent in (SENDER, TARGET, OTHER):
        (root / "inbox" / f"{agent}.jsonl").touch()
        (root / "outbox" / f"{agent}.jsonl").touch()
    return root


def run(root: Path, capsys, *argv: str) -> tuple[int, str, str]:
    code = main(["--bus-root", str(root), *argv])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def append_msg(root: Path, capsys, agent: str, target: str, msg: dict,
               to: str | None = None) -> tuple[int, str, str]:
    argv = ["append", "--agent", agent, "--target", target, "--json", json.dumps(msg)]
    if to:
        argv += ["--to", to]
    return run(root, capsys, *argv)


def last_id(root: Path, area: str, agent: str) -> str:
    lines = (root / area / f"{agent}.jsonl").read_text().strip().splitlines()
    return json.loads(lines[-1])["id"]


# ------------------------------------------------------------ 1. schema/append


def test_schema_accepts_routing_fields_and_they_round_trip(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "coordinator-agent",
        "needs_routing_to": [TARGET], "action_required": True,
        "payload": {"summary": "structural intent"}})
    assert code == 0, err
    row = json.loads((root / "outbox" / f"{SENDER}.jsonl").read_text().strip().splitlines()[-1])
    assert row["needs_routing_to"] == [TARGET]
    assert row["action_required"] is True
    code, out, err = run(root, capsys, "validate")
    assert code == 0, out + err
    assert "schema violation" not in out


def test_append_refuses_unknown_routing_target_and_empty_list(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "*", "needs_routing_to": ["no-such-agent"],
        "payload": {}})
    assert code == 1
    assert "non-roster" in err
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "*", "needs_routing_to": [], "payload": {}})
    assert code == 1  # schema minItems 1
    assert (root / "outbox" / f"{SENDER}.jsonl").read_text().strip() == ""


def test_append_refuses_action_required_with_no_addressee(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "*", "action_required": True, "payload": {}})
    assert code == 1
    assert "no concrete addressee" in err
    # A concrete `to` is a valid addressee without needs_routing_to.
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": TARGET, "action_required": True, "payload": {}})
    assert code == 0, err


# ----------------------------------------------------------------- 2. triage


def test_triage_prints_in_full_and_survives_drain(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, DAEMON, "inbox", {
        "kind": "nudge", "to": TARGET, "needs_routing_to": [TARGET],
        "payload": {"detail": LONG_MARKER}}, to=TARGET)
    assert code == 0, err

    code, out, _err = run(root, capsys, "drain", "--agent", TARGET)
    assert code == 0

    # The cursor has advanced past the message; triage must still list it, whole.
    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert code == 0
    assert LONG_MARKER in out, "routed message must be printed IN FULL, never truncated"

    # drain --triage: inbox is drained (nothing new) but the queue still shows.
    code, out, _err = run(root, capsys, "drain", "--agent", TARGET, "--triage")
    assert code == 0
    assert "no new messages" in out and LONG_MARKER in out


def test_triage_discovers_undelivered_outbox_only_routing(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "coordinator-agent", "needs_routing_to": [TARGET],
        "payload": {"detail": "never relayed to the target inbox"}})
    assert code == 0, err
    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert code == 0
    assert "never relayed to the target inbox" in out
    assert "NOT in your inbox" in out
    # It is routed to TARGET only — OTHER's triage must not list it.
    code, out, _err = run(root, capsys, "triage", "--agent", OTHER)
    assert "never relayed" not in out


def test_bare_ack_clears_reach_only_but_not_action_required(tmp_path, capsys):
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "*", "needs_routing_to": [TARGET],
        "payload": {"which": "reach-only"}})
    reach_id = last_id(root, "outbox", SENDER)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "*", "needs_routing_to": [TARGET], "action_required": True,
        "payload": {"which": "act-on-this"}})
    act_id = last_id(root, "outbox", SENDER)

    for mid in (reach_id, act_id):
        code, _out, err = append_msg(root, capsys, TARGET, "outbox", {
            "kind": "ack", "to": SENDER, "corr_id": mid, "payload": {}})
        assert code == 0, err

    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert "reach-only" not in out, "bare ack IS the contract for reach-only routing"
    assert "act-on-this" in out
    assert "ACKED but NOT actioned" in out


def test_substantive_response_or_terminal_disposition_clears_action(tmp_path, capsys):
    root = make_bus(tmp_path)
    for which in ("via-status", "via-disposition"):
        append_msg(root, capsys, SENDER, "outbox", {
            "kind": "nudge", "to": "*", "needs_routing_to": [TARGET],
            "action_required": True, "payload": {"which": which}})
    ids = [json.loads(l)["id"]
           for l in (root / "outbox" / f"{SENDER}.jsonl").read_text().strip().splitlines()]

    append_msg(root, capsys, TARGET, "outbox", {
        "kind": "status", "to": SENDER, "corr_id": ids[0],
        "payload": {"note": "done the work"}})
    append_msg(root, capsys, TARGET, "outbox", {
        "kind": "ack", "to": SENDER, "corr_id": ids[1],
        "payload": {"disposition": "declined"}})

    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert code == 0
    assert "via-status" not in out and "via-disposition" not in out
    assert "no routed messages awaiting" in out


def test_relay_copy_and_original_are_one_message_and_either_id_clears(tmp_path, capsys):
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": TARGET, "needs_routing_to": [TARGET], "action_required": True,
        "payload": {"detail": "relayed twice"}})
    orig_id = last_id(root, "outbox", SENDER)
    copy_id = f"msg-20260729T000000Z-1-{DAEMON}"
    code, _out, err = append_msg(root, capsys, DAEMON, "inbox", {
        "kind": "nudge", "id": copy_id, "from": SENDER, "to": TARGET,
        "needs_routing_to": [TARGET], "action_required": True,
        "relayed_src": orig_id, "payload": {"detail": "relayed twice"}}, to=TARGET)
    assert code == 0, err

    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert out.count("relayed twice") == 1, "outbox original + inbox copy must dedupe"

    # Responding to the RELAY COPY's id must clear the logical message.
    append_msg(root, capsys, TARGET, "outbox", {
        "kind": "status", "to": SENDER, "corr_id": copy_id, "payload": {"note": "handled"}})
    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert "relayed twice" not in out


# ---------------------------------------------------------- 3. validate lint


def test_validate_warns_on_the_gpu_lane_prose_shape(tmp_path, capsys):
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "defect", "to": "coordinator-agent",
        "payload": {"defect_3": "… FOR FABLE-AUDITOR RELEVANT TO THE C9 REVIEW IN FLIGHT …"}})
    code, out, _err = run(root, capsys, "validate")
    assert code == 0
    warned = [l for l in out.splitlines() if "WARN" in l and "needs_routing_to is unset" in l]
    assert warned and TARGET in warned[0]

    # Same message WITH the structural field: the prose lint stays quiet.
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "defect", "to": "coordinator-agent", "needs_routing_to": [TARGET],
        "payload": {"defect_3": "… FOR FABLE-AUDITOR RELEVANT TO THE C9 REVIEW IN FLIGHT …"}})
    fixed_id = last_id(root, "outbox", SENDER)
    code, out, _err = run(root, capsys, "validate")
    assert not [l for l in out.splitlines() if fixed_id in l and "needs_routing_to is unset" in l]


def test_validate_warns_on_the_action_key_prose_shape(tmp_path, capsys):
    root = make_bus(tmp_path)
    append_msg(root, capsys, TARGET, "outbox", {
        "kind": "nudge", "to": SENDER,
        "payload": {"action": "DOC FIX requested in scripts/... — operator-directed relay"}})
    code, out, _err = run(root, capsys, "validate")
    assert code == 0
    warned = [l for l in out.splitlines() if "WARN" in l and "action_required is unset" in l]
    assert warned

    append_msg(root, capsys, TARGET, "outbox", {
        "kind": "nudge", "to": SENDER, "action_required": True, "needs_routing_to": [SENDER],
        "payload": {"action": "DOC FIX requested in scripts/... — operator-directed relay"}})
    fixed_id = last_id(root, "outbox", TARGET)
    code, out, _err = run(root, capsys, "validate")
    assert not [l for l in out.splitlines() if fixed_id in l and "action_required is unset" in l]


def test_append_warns_at_authoring_time_too(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "coordinator-agent",
        "payload": {"note": "please relay this to fable-auditor for action"}})
    assert code == 0, "prose lint is advisory — the append itself succeeds"
    assert "WARN" in err and "needs_routing_to" in err


# ------------------------------------------------- 4. daemon relay preservation


def test_daemon_relay_preserves_routing_fields_verbatim(tmp_path, capsys):
    """Adoption note 1 of 407d715f, verified end to end: relay_outbox_messages
    re-stamps only the envelope (id, ts) — needs_routing_to, action_required,
    the original author, and the payload must all survive delivery unmodified.
    A routing field that vanishes in transit is worse than no field, because
    the sender believes it was routed."""
    import yaml
    from scripts.coordination.session_bus_coordinator import relay_outbox_messages

    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": TARGET, "needs_routing_to": [TARGET],
        "action_required": True, "payload": {"detail": "must survive transit"}})
    assert code == 0, err
    original = json.loads(
        (root / "outbox" / f"{SENDER}.jsonl").read_text().strip().splitlines()[-1])

    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    advisory = relay_outbox_messages(root, roster, epoch=0)

    inbox_rows = [json.loads(line) for line in
                  (root / "inbox" / f"{TARGET}.jsonl").read_text().strip().splitlines()]
    delivered = [r for r in inbox_rows if r.get("relayed_src") == original["id"]]
    assert delivered, f"relay did not deliver the routed message; advisory: {advisory}"
    row = delivered[0]
    assert row["needs_routing_to"] == [TARGET], "needs_routing_to dropped in transit"
    assert row["action_required"] is True, "action_required dropped in transit"
    assert row["from"] == SENDER, "author must be preserved, only the envelope is new"
    assert row["payload"] == original["payload"]
    assert row["id"] != original["id"], "delivered copy gets a fresh envelope id"

    # Idempotent across ticks: a second relay adds nothing.
    relay_outbox_messages(root, roster, epoch=1)
    again = (root / "inbox" / f"{TARGET}.jsonl").read_text().strip().splitlines()
    assert len(again) == len(inbox_rows)

    # And triage folds the outbox original + delivered copy into ONE logical
    # message, dispositionable by the copy's id.
    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert out.count("must survive transit") == 1


def test_daemon_relay_fans_out_needs_routing_to_in_addition_to_to(tmp_path, capsys):
    """Regression for the 2026-07-29T09:50Z miss: a finding with
    to=coordinator-agent and needs_routing_to=[codex] reached codex NEVER,
    because the relay fanned out on `to` alone. The routed recipient must now
    receive delivery IN ADDITION to `to` — never instead — with both fields
    verbatim and per-recipient idempotence."""
    import yaml
    from scripts.coordination.session_bus_coordinator import relay_outbox_messages

    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, TARGET, "outbox", {
        "kind": "finding", "to": "coordinator-agent", "needs_routing_to": [OTHER],
        "action_required": True, "payload": {"headline": "the 0950 shape"}})
    assert code == 0, err
    original = json.loads(
        (root / "outbox" / f"{TARGET}.jsonl").read_text().strip().splitlines()[-1])

    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    relay_outbox_messages(root, roster, epoch=0)

    def inbox(agent: str) -> list[dict]:
        path = root / "inbox" / f"{agent}.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().strip().splitlines() if line]

    routed = [r for r in inbox(OTHER) if r.get("relayed_src") == original["id"]]
    assert routed, "the routed recipient received NOTHING — the 09:50 defect"
    assert routed[0]["needs_routing_to"] == [OTHER]
    assert routed[0]["action_required"] is True
    assert routed[0]["payload"] == original["payload"]
    assert routed[0]["from"] == TARGET
    addressed = [r for r in inbox("coordinator-agent") if r.get("relayed_src") == original["id"]]
    assert addressed, "fan-out must be IN ADDITION to `to`, never instead"

    # Per-recipient idempotence: a second tick delivers nothing new anywhere.
    before = {a: len(inbox(a)) for a in (OTHER, "coordinator-agent")}
    relay_outbox_messages(root, roster, epoch=1)
    assert {a: len(inbox(a)) for a in (OTHER, "coordinator-agent")} == before


def test_daemon_relay_flags_unreachable_routing_recipient_never_drops_silently(tmp_path, capsys):
    """A needs_routing_to entry whose roster row is gone (post-authoring drift)
    or retired must produce a defect advisory naming message and recipient —
    once, not once per tick — while the addressable recipients still get their
    delivery."""
    import yaml
    from scripts.coordination.session_bus import MSG_SCHEMA_VERSION, _append_jsonl
    from scripts.coordination.session_bus_coordinator import relay_outbox_messages

    root = make_bus(tmp_path)
    # Direct outbox writes simulate authoring BEFORE the roster drifted:
    # append would refuse both targets today (non-roster / retired).
    for seq, routed_to in enumerate(["ghost-agent-removed", "claude-main"], start=1):
        _append_jsonl(root / "outbox" / f"{SENDER}.jsonl", {
            "schema_version": MSG_SCHEMA_VERSION, "ts": "2026-07-29T09:00:00+00:00",
            "id": f"msg-20260729T090000Z-{seq}-{SENDER}", "from": SENDER,
            "to": "coordinator-agent", "kind": "finding",
            "needs_routing_to": [routed_to], "payload": {"n": seq}})

    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    assert any(r.get("id") == "claude-main" and r.get("role") == "retired" for r in roster), \
        "fixture assumption: claude-main is the rostered-but-retired case"

    advisory = relay_outbox_messages(root, roster, epoch=0)
    defects = {a["unreachable"]: a for a in advisory
               if a.get("kind") == "defect" and a.get("unreachable")}
    assert set(defects) == {"ghost-agent-removed", "claude-main"}
    assert "not a roster id" in defects["ghost-agent-removed"]["detail"]
    assert "retired" in defects["claude-main"]["detail"]
    assert defects["ghost-agent-removed"]["relayed_src"] == f"msg-20260729T090000Z-1-{SENDER}"
    assert not (root / "inbox" / "ghost-agent-removed.jsonl").exists()
    assert not (root / "inbox" / "claude-main.jsonl").exists()
    coord = (root / "inbox" / "coordinator-agent.jsonl").read_text().strip().splitlines()
    assert len(coord) == 2, "addressable recipients still get their delivery"

    # Once per (msg, recipient): with the first advisories persisted (as the
    # daemon tick does), a second tick re-flags nothing.
    for row in advisory:
        _append_jsonl(root / "advisory.jsonl", row)
    second = relay_outbox_messages(root, roster, epoch=1)
    assert not [a for a in second if a.get("unreachable")]


def test_append_refuses_routing_to_a_retired_roster_row(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "coordinator-agent",
        "needs_routing_to": ["claude-main"], "payload": {}})
    assert code == 1
    assert "retired" in err


# ------------------------------------------------- 5. truncation-evident output


def test_triage_output_is_truncation_evident(tmp_path, capsys):
    """Adoption note 2 of 407d715f: a truncated copy of the triage report must
    be VISIBLY wrong (unbalanced BEGIN/END fences, missing COMPLETE trailer),
    never quietly lossy."""
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "*", "needs_routing_to": [TARGET],
        "payload": {"detail": LONG_MARKER}})

    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert code == 0
    assert out.count("BEGIN ROUTED MESSAGE") == 1
    assert out.count("END ROUTED MESSAGE") == 1
    assert "TRIAGE REPORT COMPLETE" in out
    assert "DO NOT TRUNCATE" in out
    assert LONG_MARKER in out

    # A context-economy cut (the 2026-07-29 failure shape) is now self-evident:
    # the long body dominates the report, so any prefix cut strands a BEGIN
    # fence without its END and drops the trailer.
    cut = out[: len(out) // 2]
    assert cut.count("BEGIN ROUTED MESSAGE") > cut.count("END ROUTED MESSAGE")
    assert "TRIAGE REPORT COMPLETE" not in cut

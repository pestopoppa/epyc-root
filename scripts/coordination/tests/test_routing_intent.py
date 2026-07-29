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

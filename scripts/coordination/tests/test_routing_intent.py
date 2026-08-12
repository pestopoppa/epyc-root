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
#
# 2026-07-29: these were `claude-gpu-lane` / `fable-auditor` / `codex` and the roster
# rename to model-agnostic ids turned this ENTIRE FILE red — 16 failed, 0 passed —
# without anyone noticing, because nothing runs it on a schedule and `append` had
# already started enforcing the roster. A suite that is red for an unrelated reason
# stops being read at all, so `make_bus` now asserts these against the copied config
# and fails with one pointed message instead of sixteen confusing ones.
SENDER = "mainB"
TARGET = "auditor"
OTHER = "inference"
RETIRED = "codex-bus-tests"      # rostered but role: retired — a distinct case from absent
DAEMON = "coordinator-daemon"

LONG_MARKER = "NEEDLE-" + "x" * 3000 + "-ENDNEEDLE"


def make_bus(tmp_path: Path) -> Path:
    root = tmp_path / "bus"
    shutil.copytree(BUS_SRC, root)
    (root / "queue.jsonl").write_text("")
    for area in ("inbox", "outbox", "heartbeats", "cursors"):
        for f in (root / area).glob("*"):
            f.unlink()
    import yaml as _yaml
    roster = (_yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}).get("roster") or []
    by_id = {str(r.get("id")): r for r in roster if isinstance(r, dict)}
    missing = [a for a in (SENDER, TARGET, OTHER, RETIRED) if a not in by_id]
    assert not missing, (
        f"fixture ids {missing} are no longer on the roster in {BUS_SRC}/config.yaml "
        f"(have: {sorted(by_id)}). A roster RENAME silently reddens this whole file; "
        f"update the SENDER/TARGET/OTHER/RETIRED constants above.")
    assert by_id[RETIRED].get("role") == "retired", (
        f"fixture assumption: {RETIRED!r} is the rostered-but-RETIRED case, but its role "
        f"is {by_id[RETIRED].get('role')!r}. Pick another retired row or the "
        f"retired-vs-absent distinction stops being tested.")
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
    for seq, routed_to in enumerate(["ghost-agent-removed", RETIRED], start=1):
        _append_jsonl(root / "outbox" / f"{SENDER}.jsonl", {
            "schema_version": MSG_SCHEMA_VERSION, "ts": "2026-07-29T09:00:00+00:00",
            "id": f"msg-20260729T090000Z-{seq}-{SENDER}", "from": SENDER,
            "to": "coordinator-agent", "kind": "finding",
            "needs_routing_to": [routed_to], "payload": {"n": seq}})

    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    assert any(r.get("id") == RETIRED and r.get("role") == "retired" for r in roster), \
        f"fixture assumption: {RETIRED} is the rostered-but-retired case"

    advisory = relay_outbox_messages(root, roster, epoch=0)
    defects = {a["unreachable"]: a for a in advisory
               if a.get("kind") == "defect" and a.get("unreachable")}
    assert set(defects) == {"ghost-agent-removed", RETIRED}
    assert "not a roster id" in defects["ghost-agent-removed"]["detail"]
    assert "retired" in defects[RETIRED]["detail"]
    assert defects["ghost-agent-removed"]["relayed_src"] == f"msg-20260729T090000Z-1-{SENDER}"
    assert not (root / "inbox" / "ghost-agent-removed.jsonl").exists()
    assert not (root / "inbox" / f"{RETIRED}.jsonl").exists()
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
        "needs_routing_to": [RETIRED], "payload": {}})
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


# =========================================================== 6. ADDRESSING (2026-08-12)
#
# The measured problem these pin: 499 `action_required` rows across the fleet's
# inboxes, only 86 sole-target — 83% of what an agent had to triage was not its
# own (73-89% per agent). Two compounding causes, one test section each:
#   (1) the schema had no FYI concept: one boolean applied to every member of
#       `needs_routing_to`, so a fleet-wide report marked EVERYONE as owing;
#   (2) the relay rewrote `to` on each fan-out copy, so 100% of delivered rows
#       looked directly addressed and a CC was indistinguishable from a job.


def test_append_refuses_action_required_with_more_than_one_target(tmp_path, capsys):
    """THE refusal. Same fail-closed shape as the to='*' refusal beside it."""
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "coordinator-agent", "action_required": True,
        "needs_routing_to": [TARGET, OTHER], "payload": {"ask": "everyone do this"}})
    assert code == 1
    assert "one assignee per action" in err
    assert "N agents each owing a distinct action = N messages" in err
    assert "`cc`" in err
    assert (root / "outbox" / f"{SENDER}.jsonl").read_text().strip() == ""

    # The compliant rewrite the error names: one assignee, the rest reach-only.
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "coordinator-agent", "action_required": True,
        "assignee": TARGET, "cc": [OTHER], "payload": {"ask": "you do this"}})
    assert code == 0, err
    # A single-target legacy row is still fine — history keeps working.
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "coordinator-agent", "action_required": True,
        "needs_routing_to": [TARGET], "payload": {"ask": "legacy single"}})
    assert code == 0, err


def test_append_refuses_unresolvable_or_contradictory_addressing(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "*", "cc": ["no-such-agent"], "payload": {}})
    assert code == 1 and "non-roster" in err
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "status", "to": "*", "assignee": RETIRED, "payload": {}})
    assert code == 1 and "retired" in err
    # Both assignee AND cc for one agent = two contradictory obligations.
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "*", "assignee": TARGET, "cc": [TARGET], "payload": {}})
    assert code == 1 and "contradictory obligations" in err


def test_cc_delivery_preserves_to_while_the_assignee_copy_is_addressed(tmp_path, capsys):
    """The relay half of the fix. Before this, `msg["to"] = target` on every
    fan-out copy made a CC structurally indistinguishable from an assignment."""
    import yaml
    from scripts.coordination.session_bus_coordinator import relay_outbox_messages

    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "coordinator-agent", "action_required": True,
        "assignee": TARGET, "cc": [OTHER], "payload": {"detail": "one owner, one reader"}})
    assert code == 0, err
    src = last_id(root, "outbox", SENDER)

    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    relay_outbox_messages(root, roster, epoch=0)

    def copy(agent):
        path = root / "inbox" / f"{agent}.jsonl"
        rows = [json.loads(l) for l in path.read_text().strip().splitlines() if l]
        got = [r for r in rows if r.get("relayed_src") == src]
        assert got, f"{agent} received nothing"
        return got[0]

    assignee_copy = copy(TARGET)
    assert assignee_copy["to"] == TARGET, "the assignee copy IS addressed to them"
    assert "cc_delivery" not in assignee_copy

    cc_copy = copy(OTHER)
    assert cc_copy["to"] == "coordinator-agent", \
        "a CC copy must PRESERVE the original `to` — rewriting it is what made every " \
        "delivered row look directly addressed"
    assert cc_copy["cc_delivery"] is True
    assert cc_copy["payload"] == assignee_copy["payload"], "same message, different standing"

    # The transport addressee keeps its own `to` and is not marked cc.
    addressed = copy("coordinator-agent")
    assert addressed["to"] == "coordinator-agent"
    assert "cc_delivery" not in addressed


def test_triage_splits_must_act_from_fyi(tmp_path, capsys):
    """MUST-ACT: full detail, disposition required. FYI: one line, nothing owed."""
    import yaml
    from scripts.coordination.session_bus_coordinator import relay_outbox_messages

    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": "coordinator-agent", "action_required": True,
        "assignee": TARGET, "cc": [OTHER], "payload": {"detail": "MINE-" + LONG_MARKER}})
    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    relay_outbox_messages(root, roster, epoch=0)

    code, out, _err = run(root, capsys, "triage", "--agent", TARGET)
    assert code == 0
    assert "MUST-ACT (1)" in out
    assert "MINE-" + LONG_MARKER in out, "the assignee gets the FULL body"
    assert "BEGIN ROUTED MESSAGE" in out

    # The cc'd agent: one line, no fence, no disposition instruction.
    code, out, _err = run(root, capsys, "triage", "--agent", OTHER)
    assert code == 0
    assert "FYI (1)" in out
    assert "NO disposition owed" in out
    assert "BEGIN ROUTED MESSAGE" not in out, "an FYI is one line, not a fenced body"
    assert LONG_MARKER not in out, "an FYI is summarised; only MUST-ACT is reproduced in full"
    assert "nothing requires your action" in out

    # And a cc is cleared by ADVANCING A CURSOR — no ack, no corr_id.
    run(root, capsys, "drain", "--agent", OTHER, "--no-boundary-checks")
    code, out, _err = run(root, capsys, "triage", "--agent", OTHER)
    assert "no routed messages awaiting" in out


def test_legacy_multi_target_action_row_becomes_fyi_for_everyone(tmp_path, capsys):
    """The 83%: a request N agents share is a request none of them owns. Such a
    row is history now (append refuses it), but 499 of them are on the live bus
    and must still deliver, still validate, and stop occupying MUST-ACT."""
    import yaml
    from scripts.coordination.session_bus import MSG_SCHEMA_VERSION, _append_jsonl
    from scripts.coordination.session_bus_coordinator import relay_outbox_messages

    root = make_bus(tmp_path)
    _append_jsonl(root / "outbox" / f"{SENDER}.jsonl", {
        "schema_version": MSG_SCHEMA_VERSION, "ts": "2026-08-11T09:00:00+00:00",
        "id": f"msg-20260811T090000Z-1-{SENDER}", "from": SENDER, "to": "coordinator-agent",
        "kind": "status", "action_required": True, "needs_routing_to": [TARGET, OTHER],
        "payload": {"detail": "the fleet-wide report shape"}})

    code, out, _err = run(root, capsys, "validate")
    assert code == 0, out          # legacy rows WARN, never FAIL
    assert "looks like FYI" in out, "the opposite-polarity lint must fire on it"

    roster = yaml.safe_load((root / "config.yaml").read_text())["roster"]
    relay_outbox_messages(root, roster, epoch=0)
    for agent in (TARGET, OTHER):
        rows = [json.loads(l) for l in
                (root / "inbox" / f"{agent}.jsonl").read_text().strip().splitlines() if l]
        assert [r for r in rows if r.get("relayed_src") == f"msg-20260811T090000Z-1-{SENDER}"], \
            f"pre-migration row must STILL DELIVER to {agent}"
        code, out, _err = run(root, capsys, "triage", "--agent", agent)
        assert "FYI (1)" in out and "0 MUST-ACT item(s)" in out
        assert "BEGIN ROUTED MESSAGE" not in out


def test_ack_quoting_its_request_is_not_flagged_as_a_new_request(tmp_path, capsys):
    """Linter symmetry, half 1. The prose lint fired on any payload matching
    'action required' — including a disposition QUOTING the request it answers —
    and then told the author to SET the bit, re-arming the item it was clearing."""
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": TARGET, "action_required": True, "assignee": TARGET,
        "payload": {"ask": "do the thing"}})
    req = last_id(root, "outbox", SENDER)

    quoting = {"disposition": "done",
               "note": "re: your message — 'ACTION REQUIRED: do the thing' — done."}
    code, _out, err = append_msg(root, capsys, TARGET, "outbox", {
        "kind": "ack", "to": SENDER, "corr_id": req, "payload": quoting})
    assert code == 0, err
    assert "action_required is unset" not in err, \
        "a disposition quoting its request is not a new request"

    code, out, _err = run(root, capsys, "validate")
    assert code == 0
    assert not [l for l in out.splitlines() if "action_required is unset" in l]

    # The exemption is scoped: the SAME prose with no corr_id and a non-ack kind
    # still warns, so the lint has not simply been switched off.
    code, _out, err = append_msg(root, capsys, TARGET, "outbox", {
        "kind": "status", "to": SENDER, "payload": quoting})
    assert code == 0
    assert "action_required is unset" in err


def test_fyi_shaped_lint_fires_on_report_kinds(tmp_path, capsys):
    """Linter symmetry, half 2 — the missing opposite polarity. The old lint only
    ever pushed the bit ON, which is how 499 rows accumulated with 86 sole targets."""
    from scripts.coordination.session_bus import prose_routing_warnings
    for kind in ("finding", "status", "task-complete"):
        warnings = prose_routing_warnings(
            {"kind": kind, "from": SENDER, "to": "coordinator-agent",
             "action_required": True, "needs_routing_to": [TARGET, OTHER],
             "payload": {"headline": "swept the queue"}}, {SENDER, TARGET, OTHER})
        assert any("looks like FYI" in w and "`cc`" in w for w in warnings), kind
    # A single-target report is somebody's job and must NOT be flagged.
    assert not [w for w in prose_routing_warnings(
        {"kind": "finding", "from": SENDER, "to": TARGET, "action_required": True,
         "assignee": TARGET, "payload": {"headline": "your bug"}}, {SENDER, TARGET})
        if "looks like FYI" in w]
    # And a non-report kind broadcast is out of scope for THIS lint (append refuses it).
    assert not [w for w in prose_routing_warnings(
        {"kind": "nudge", "from": SENDER, "to": "*", "action_required": True,
         "needs_routing_to": [TARGET, OTHER], "payload": {}}, {SENDER, TARGET, OTHER})
        if "looks like FYI" in w]


# ============================================================ 7. AUD-2 typed task-assign


def _assign(**payload):
    return {"kind": "task-assign", "to": TARGET, "task_id": "T-1",
            "payload": {"lane": "none", "epoch": 0,
                        "lease_expires_ts": "2026-08-12T23:00:00+00:00", **payload}}


def test_task_assign_without_task_text_is_refused(tmp_path, capsys):
    """`row_ref` is a hint; anchor rot ran 34.5% queue-wide. The TEXT is identity."""
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox",
                                 _assign(row_ref="handoffs/active/x.md:412"))
    assert code == 1
    assert "task_text" in err and "identity" in err.lower()
    assert (root / "outbox" / f"{SENDER}.jsonl").read_text().strip() == ""

    code, _out, err = append_msg(root, capsys, SENDER, "outbox", _assign(
        task_text="Wire the E5 re-measurement into the belief kernel",
        row_ref="handoffs/active/x.md:412",
        screened_by="backlog_row_check.py@2026-08-12T09:14Z:WELL-FORMED",
        expected_occupancy={"est_h": 3.0, "basis": "prior run 2026-08-05"},
        constraints=[{"constraint": "GPU only", "source": "config.yaml:roster/mainC"}]))
    assert code == 0, err
    # Fully typed: no vocabulary, occupancy, screening or F-20 warnings.
    for noise in ("outside the typed vocabulary", "expected_occupancy", "screened_by",
                  "not a constraint"):
        assert noise not in err, err


def test_task_assign_warns_but_does_not_refuse_the_untyped_shapes(tmp_path, capsys):
    """171 distinct payload keys across 55 dispatches is a habit, not a bug to
    fail closed on mid-flight. WARN — refusing would just move the failure."""
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", _assign(
        task_text="do the thing", improvised_key="whatever the author felt like",
        constraints="GPU only - no CPU region, no stack reload"))
    assert code == 0, err
    assert "outside the typed vocabulary" in err and "improvised_key" in err
    assert "not a constraint" in err          # F-20: a constraint cites its source
    assert "expected_occupancy" in err        # F-14: how long will this hold the card?
    assert "screened_by" in err


def test_oversized_task_assign_payload_without_brief_path_is_refused(tmp_path, capsys):
    from scripts.coordination.session_bus import TASK_ASSIGN_PAYLOAD_MAX_BYTES
    root = make_bus(tmp_path)
    wall = "x" * (TASK_ASSIGN_PAYLOAD_MAX_BYTES + 100)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox",
                                 _assign(task_text="big one", inline_spec={"body": wall}))
    assert code == 1
    assert "brief_path" in err and str(TASK_ASSIGN_PAYLOAD_MAX_BYTES) in err

    code, _out, err = append_msg(root, capsys, SENDER, "outbox", _assign(
        task_text="big one", inline_spec={"body": wall},
        brief_path="handoffs/active/briefs/T-1.md"))
    assert code == 0, err


def test_other_kinds_are_unaffected_by_the_task_assign_gate(tmp_path, capsys):
    """Gated on kind == task-assign, so nothing else acquires a task_text duty."""
    root = make_bus(tmp_path)
    for kind in ("status", "finding", "nudge", "defect"):
        code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
            "kind": kind, "to": TARGET, "payload": {"note": "no task_text here"}})
        assert code == 0, f"{kind}: {err}"


def test_daemon_task_assign_is_typed_from_the_queue_row(tmp_path, capsys):
    """The daemon emits task-assign too (authority `assign`). A typed dispatch
    only humans have to fill in is a rule with a hole exactly where the volume is."""
    from datetime import datetime, timezone
    from scripts.coordination.session_bus_coordinator import _task_assign_payload

    expires = datetime(2026, 8, 12, 23, 0, tzinfo=timezone.utc)
    payload = _task_assign_payload(
        {"task_id": "T-9", "lane": "gpu", "gating": "gpu", "spec_ref": "h.md#L4",
         "task_text": "Re-measure E5 at NPS4", "screened_by": "backlog_row_check:OK",
         "est_wall_clock_h": 4.5}, epoch=7, expires=expires)
    assert payload["task_text"] == "Re-measure E5 at NPS4"
    assert payload["row_ref"] == "h.md#L4"          # demoted to a hint
    assert payload["screened_by"] == "backlog_row_check:OK"
    assert payload["expected_occupancy"]["est_h"] == 4.5   # F-14
    assert "not measured" in payload["expected_occupancy"]["basis"]
    assert payload["lane"] == "gpu" and payload["epoch"] == 7

    # No task_text on the row: the fallback SAYS it is a fallback rather than
    # letting a task id pass as a row text.
    bare = _task_assign_payload({"task_id": "T-9", "lane": "none"}, 7, expires)
    assert "no task_text" in bare["task_text"] and "T-9" in bare["task_text"]

    # And what it emits passes the authoring gate it asks of everyone else.
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, DAEMON, "inbox", {
        "kind": "task-assign", "to": TARGET, "task_id": "T-9", "assignee": TARGET,
        "action_required": True, "payload": payload}, to=TARGET)
    assert code == 0, err


def test_intake_carries_task_text_onto_the_queue_row(tmp_path, capsys):
    from scripts.coordination.session_bus_coordinator import intake_proposals
    rows, _adv = intake_proposals(tmp_path, {}, {"T-2": [{
        "kind": "task-propose", "from": SENDER, "task_id": "T-2",
        "payload": {"lane": "none", "gating": "none", "spec_ref": "h.md",
                    "summary": "Close the FYI gap in the bus schema"}}]}, epoch=0)
    assert rows[0]["task_text"] == "Close the FYI gap in the bus schema"


# ================================================================ 8. AUD-4 corrections


def test_corrections_are_generated_from_typed_finding_rows(tmp_path, capsys):
    """Five corrections went missing from the 2026-08-12 wrap-up because a
    correction looked like any other finding, so nothing could enumerate them."""
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "coordinator-agent", "payload": {"headline": "ordinary"}})
    target_id = last_id(root, "outbox", SENDER)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "coordinator-agent",
        "payload": {"corrects": target_id, "provenance": "operator-verbatim",
                    "correction": "the operator said 'this should ALWAYS be the case'"}})
    assert code == 0, err
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": "coordinator-agent",
        "payload": {"corrects": target_id, "correction": "no provenance stated"}})
    assert code == 0, err

    code, out, _err = run(root, capsys, "corrections", "--agent", SENDER)
    assert code == 0
    assert "## Corrections (2)" in out
    assert "operator-verbatim" in out and target_id in out
    assert "ordinary" not in out, "a finding that corrects nothing is not a correction"
    assert "1 of these state no `provenance`" in out

    code, out, _err = run(root, capsys, "corrections", "--agent", TARGET)
    assert code == 0 and "no corrections recorded" in out


def test_finding_provenance_enum_is_enforced(tmp_path, capsys):
    root = make_bus(tmp_path)
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": TARGET,
        "payload": {"corrects": "msg-20260812T000000Z-1-mainB", "provenance": "vibes"}})
    assert code == 1 and "provenance" in err
    # `corrects` must look like a msg id, not a description of one.
    code, _out, err = append_msg(root, capsys, SENDER, "outbox", {
        "kind": "finding", "to": TARGET,
        "payload": {"corrects": "that thing mainB said yesterday"}})
    assert code == 1


# ========================================================== 9. AUD-3 drain boundary


def test_drain_prints_the_three_boundary_readings(tmp_path, capsys):
    """`drain` is the role's ONE proven checkpoint (Guardrail 1 makes it mandatory
    at every task boundary), so these three readings live where they cannot be missed."""
    root = make_bus(tmp_path)
    append_msg(root, capsys, SENDER, "outbox", {
        "kind": "nudge", "to": TARGET, "assignee": TARGET, "action_required": True,
        "payload": {"ask": "owed by the drainer"}})
    append_msg(root, capsys, DAEMON, "inbox", {
        "kind": "nudge", "to": TARGET, "assignee": TARGET, "action_required": True,
        "from": SENDER, "ts": "2026-07-01T00:00:00+00:00",
        "relayed_src": last_id(root, "outbox", SENDER),
        "payload": {"ask": "owed by the drainer"}}, to=TARGET)

    code, _out, err = run(root, capsys, "drain", "--agent", TARGET)
    assert code == 0
    assert "boundary: 1 action_required row(s) OWED BY YOU" in err
    assert "d old" in err, "age is the point — a two-week-old ask read like this minute's"
    assert "boundary: scripts/" in err
    assert "boundary: occupancy" in err


def test_drain_never_reports_a_stale_fleet_watch_line_as_current(tmp_path, capsys):
    """MANDATORY guard: fleet_watch runs unsupervised, so its log going quiet is
    indistinguishable from a busy fleet. A measurement whose window does not
    overlap the phenomenon is not evidence about the phenomenon."""
    import os
    import time as _time
    from scripts.coordination.session_bus import _print_fleet_watch_occupancy

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "coordination" / "session-bus").mkdir(parents=True)
    (repo / "logs").mkdir()
    log = repo / "logs" / "fleet_watch.log"
    log.write_text("noise\n2026-08-12T03:00:00Z COMPUTE-IDLE gpu=0% for 3h47m\nmore noise\n")
    bus = repo / "coordination" / "session-bus"

    old = _time.time() - 4 * 3600
    os.utime(log, (old, old))
    capsys.readouterr()
    _print_fleet_watch_occupancy(bus)
    err = capsys.readouterr().err
    assert "STALE" in err and "do NOT relay it as current" in err
    assert "COMPUTE-IDLE gpu=0% for 3h47m" in err, "verbatim, with its path"
    assert str(log) in err

    now = _time.time()
    os.utime(log, (now, now))
    capsys.readouterr()
    _print_fleet_watch_occupancy(bus)
    err = capsys.readouterr().err
    assert "STALE" not in err and "COMPUTE-IDLE gpu=0% for 3h47m" in err

    # A missing log says UNKNOWN — it must never render as a clean reading.
    log.unlink()
    capsys.readouterr()
    _print_fleet_watch_occupancy(bus)
    assert "occupancy UNKNOWN" in capsys.readouterr().err

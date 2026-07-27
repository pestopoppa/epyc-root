#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""unblock_artifact.py — the consolidated operator unblock artifact (rider R8).

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md §Rider R8
Policy:         agents/shared/MEASUREMENT_POLICY.md §Consolidated apply-time ratification

THE PROBLEM. Pending operator gates accumulate while the operator is away. Handled
badly, returning means a relay session: read each gate, work out what it wants,
run a command per gate. Handled well, returning costs ONE command.

THE DESIGN, AND WHY IT IS SMALL. Granting is flipping `- [ ]` to `- [x]` in
`tokens/token-queue.md` — the mechanism BUS_PROTOCOL rule 1 already establishes,
where a checkbox in an operator-owned file IS the grant. This deliberately adds no
new grammar, no typed secret, and no revision-pinned applier chain:

  * A typed token preimage was considered and rejected. It would be typed into a
    machine-generated script, so it defends against nothing an agent could do
    while adding a ceremony to every return. The checkbox has the same real
    security properties — only the operator writes that file — and already exists.
  * Per-line pins, NEVER a whole-bundle hash. A bundle-wide integrity assertion
    hard-fails the instant the operator strikes one line, which is the one thing
    they are explicitly invited to do.
  * Repair re-presents the SAME artifact with updated pins. No revision-suffixed
    files, because a new file per repair is a new ratification chain in all but
    name, and the ratified rule forbids restarting a chain on repair.
  * No repo-HEAD pin. Parallel sessions commit continuously here, so a HEAD pin
    refuses spuriously. HEAD is recorded for forensics, not enforced.
  * No dwell-time metric. It would measure the operator, not the machine.

INVARIANTS THIS UPHOLDS
  * Only the operator escalates a glyph. This tool may de-escalate `[x]` → `[ ]`
    ONLY when a pinned command changed under a granted gate, and says so loudly.
  * A struck gate returns to `HELD_OP_GATE` — held, not dropped, not requeued —
    and is re-presented unchanged next time.
  * The applier never commits, never `git add`s, and never writes a bus file
    other than its own receipt. Single-writer stays intact; the coordinator-daemon
    transcribes the outcome on its next tick.
  * A command that fails when the operator runs it is an AGENT defect: it should
    have been caught by pre-validation.

Exit codes:
    0   nothing to do, or everything applied cleanly
    2   at least one gate failed to apply (details + receipt path on stdout)
    3   the artifact is unusable (missing, or a pin no longer matches)
    64  usage

Usage:
    unblock_artifact.py generate                  # (re)write the artifact
    unblock_artifact.py show                      # what is pending, no writes
    unblock_artifact.py apply --plan              # what WOULD run; no execution
    unblock_artifact.py apply                     # THE one command
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Where this code lives, versus where the data lives. These are NOT the same
# thing: the package location is fixed by the file's own path, while the data root
# is redirectable (tests point it at a throwaway tree). Conflating them made the
# module unimportable under a redirected root.
_CODE_ROOT = Path(__file__).resolve().parents[2]
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

REPO_ROOT = Path("/workspace")
BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"
TOKEN_QUEUE = BUS_ROOT / "tokens" / "token-queue.md"
ARTIFACT = BUS_ROOT / "tokens" / "unblock.md"
PINS = BUS_ROOT / "tokens" / "unblock.pins.json"
RECEIPTS = REPO_ROOT / "artifacts" / "operator" / "unblock-receipts"

EX_FAILED = 2
EX_UNUSABLE = 3
EX_USAGE = 64

# A gate line: `- [ ] **GATE-ID** — summary` or `- [x] GATE-ID GRANTED 2026-07-27 — note`.
# gate_id is captured independently of the dash character, so an em dash, a double
# hyphen or a single hyphen all parse. STRUCK is accepted anywhere on the line.
_GATE_LINE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s*\**(?P<gate>[A-Za-z0-9][A-Za-z0-9._-]*)")
_STRUCK = re.compile(r"\bSTRUCK\b\s*(?P<date>\d{4}-\d{2}-\d{2})?", re.I)
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _head() -> str:
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True, timeout=15)
    return out.stdout.strip() or "unknown"


# --------------------------------------------------------------------- reading


def parse_token_queue() -> list[dict]:
    """Every gate line in the token queue, with its mark and adjudication."""
    if not TOKEN_QUEUE.exists():
        return []
    gates: list[dict] = []
    for lineno, line in enumerate(TOKEN_QUEUE.read_text(encoding="utf-8").splitlines(), 1):
        m = _GATE_LINE.match(line)
        if not m:
            continue
        struck = _STRUCK.search(line)
        marked = m.group("mark").lower() == "x"
        state = "struck" if struck else ("granted" if marked else "pending")
        # A verb without an ISO date is malformed rather than silently honoured:
        # an undated grant leaves no audit trail of when it was given.
        malformed = None
        if state in {"granted", "struck"} and not _ISO_DATE.search(line):
            malformed = "adjudicated without an ISO date"
        gates.append({"gate_id": m.group("gate"), "line_no": lineno, "line": line.rstrip(),
                      "state": state, "malformed": malformed})
    return gates


def held_tasks() -> dict[str, list[str]]:
    """gate_id -> task_ids currently held on it."""
    from scripts.coordination.session_bus import fold_queue
    out: dict[str, list[str]] = {}
    for tid, row in fold_queue(BUS_ROOT).items():
        if row.get("status") != "HELD_OP_GATE":
            continue
        for gate in row.get("operator_gates") or []:
            out.setdefault(gate, []).append(tid)
    return out


def token_commands() -> dict[str, dict]:
    """gate_id -> the pre-validated command relayed with it.

    Read from agent outboxes, which is where the requesting agent recorded the
    dry-run evidence. A gate with no validated command is reported, never guessed
    at: presenting a command nobody validated is the defect this avoids.
    """
    from scripts.coordination.session_bus import _read_jsonl
    out: dict[str, dict] = {}
    for path in sorted((BUS_ROOT / "outbox").glob("*.jsonl")):
        rows, _ = _read_jsonl(path)
        for row in rows:
            if row.get("kind") != "token-request":
                continue
            payload = row.get("payload") or {}
            gate = payload.get("gate_id")
            validated = payload.get("validated") or {}
            if gate and validated.get("cmd"):
                out[gate] = {"cmd": validated["cmd"],
                             "dry_run_exit": validated.get("dry_run_exit"),
                             "evidence": validated.get("dry_run_evidence"),
                             "requested_by": row.get("from"),
                             "task_id": row.get("task_id")}
    return out


# ------------------------------------------------------------------ generating


def build_artifact() -> tuple[str, dict]:
    gates = parse_token_queue()
    held = held_tasks()
    cmds = token_commands()
    pending = [g for g in gates if g["state"] == "pending"]
    granted = [g for g in gates if g["state"] == "granted"]
    struck = [g for g in gates if g["state"] == "struck"]
    malformed = [g for g in gates if g["malformed"]]

    pins = {"generated_at": _now(), "head": _head(), "gates": {}}
    lines = [
        "# Consolidated unblock",
        "",
        f"generated {pins['generated_at']}  ·  epyc-root @ {pins['head']}",
        f"pending {len(pending)} · granted {len(granted)} · struck {len(struck)}"
        f" · malformed {len(malformed)}",
        "",
        "## The one command",
        "",
        "    bash /workspace/artifacts/operator/unblock.sh",
        "",
        "It applies every gate you ticked, skips the rest, and reports what it did.",
        "Add `--plan` to see what it would run without running anything.",
        "",
        "## How to adjudicate",
        "",
        "Edit `coordination/session-bus/tokens/token-queue.md` — the only file whose",
        "checkboxes you own:",
        "",
        "    - [x] **GATE-ID** … GRANTED 2026-07-27      apply it",
        "    - [ ] **GATE-ID** … STRUCK 2026-07-27 — why  decline this round; stays held",
        "",
        "Leave a line untouched to decide later. Never delete a line: a missing gate",
        "reads as *absent*, not as *declined*. An ISO date is required — an undated",
        "grant leaves no record of when you gave it.",
        "",
    ]

    if malformed:
        lines += ["## Malformed — not actionable until fixed", ""]
        for g in malformed:
            lines.append(f"- `{g['gate_id']}` (line {g['line_no']}): {g['malformed']}")
        lines.append("")

    lines += ["## Awaiting your decision", ""]
    if not pending:
        lines += ["_Nothing pending._", ""]
    for g in pending:
        cmd = cmds.get(g["gate_id"])
        blocked = held.get(g["gate_id"]) or []
        lines.append(f"### {g['gate_id']}")
        lines.append("")
        lines.append(f"- holds: {', '.join(f'`{t}`' for t in blocked) if blocked else '_no task currently held_'}")
        if cmd:
            lines.append(f"- requested by `{cmd['requested_by']}` for `{cmd['task_id']}`")
            lines.append(f"- pre-validated (dry-run exit `{cmd['dry_run_exit']}`): "
                         f"{cmd['evidence']}")
            lines.append("- command:")
            lines.append("")
            lines.append(f"      {cmd['cmd']}")
            pins["gates"][g["gate_id"]] = {"cmd_sha256": _sha256(cmd["cmd"]), "cmd": cmd["cmd"]}
        else:
            lines.append("- **no pre-validated command recorded** — this gate cannot be applied")
            lines.append("  automatically. The requesting agent owes dry-run evidence; presenting")
            lines.append("  an unvalidated command is an agent defect, so nothing is guessed here.")
        lines.append("")

    if granted:
        lines += ["## Ticked, awaiting the next apply", ""]
        for g in granted:
            lines.append(f"- `{g['gate_id']}`")
        lines.append("")
    if struck:
        lines += ["## Struck — held, not dropped; re-presented unchanged next time", ""]
        for g in struck:
            lines.append(f"- `{g['gate_id']}`")
        lines.append("")

    return "\n".join(lines) + "\n", pins


def cmd_generate(args: argparse.Namespace) -> int:
    text, pins = build_artifact()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(text, encoding="utf-8")
    PINS.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {ARTIFACT.relative_to(REPO_ROOT)} ({len(pins['gates'])} applicable gate(s))")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    gates = parse_token_queue()
    held = held_tasks()
    cmds = token_commands()
    if not gates:
        print("no gates in the token queue")
        return 0
    for g in gates:
        blocked = ", ".join(held.get(g["gate_id"]) or []) or "-"
        has_cmd = "cmd" if g["gate_id"] in cmds else "NO CMD"
        flag = f"  [{g['malformed']}]" if g["malformed"] else ""
        print(f"  {g['state']:<8} {g['gate_id']:<34} holds={blocked:<28} {has_cmd}{flag}")
    return 0


# -------------------------------------------------------------------- applying


def already_applied(gate_id: str, cmd_sha256: str) -> str | None:
    """The receipt of a prior SUCCESSFUL apply of this exact command, if any.

    A gate stays ticked after it is applied, so a second `apply` would otherwise
    re-run the command. Most pre-validated commands are ratify-style and idempotent,
    but relying on that convention when a cheap check exists is not good enough —
    one non-idempotent command would double-apply. Keyed on the command hash, so a
    *changed* command under the same gate is correctly treated as not-yet-applied.
    """
    if not RECEIPTS.exists():
        return None
    for path in sorted(RECEIPTS.glob("unblock_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("results") or []:
            if r.get("gate_id") == gate_id and r.get("ok") and _sha256(r.get("cmd", "")) == cmd_sha256:
                return path.name
    return None


def cmd_apply(args: argparse.Namespace) -> int:
    if not PINS.exists():
        print(f"REFUSING: no pins at {PINS}. Run `generate` first.", file=sys.stderr)
        return EX_UNUSABLE
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    gates = {g["gate_id"]: g for g in parse_token_queue()}
    cmds = token_commands()

    granted = [gid for gid, g in gates.items() if g["state"] == "granted"]
    if not granted:
        print("Nothing ticked — no gate to apply.")
        return 0

    plan: list[tuple[str, str]] = []
    drifted: list[str] = []
    skipped: list[str] = []
    for gid in sorted(granted):
        pinned = (pins.get("gates") or {}).get(gid)
        live = cmds.get(gid)
        if not live:
            drifted.append(f"{gid}: granted but no validated command is recorded")
            continue
        if not pinned:
            drifted.append(f"{gid}: granted but was not in the artifact when it was generated")
            continue
        if _sha256(live["cmd"]) != pinned["cmd_sha256"]:
            drifted.append(f"{gid}: the command CHANGED after you granted it "
                           f"(pinned {pinned['cmd_sha256'][:12]}…, now {_sha256(live['cmd'])[:12]}…)")
            continue
        prior = already_applied(gid, pinned["cmd_sha256"])
        if prior:
            skipped.append(f"{gid}: already applied successfully ({prior})")
            continue
        plan.append((gid, live["cmd"]))

    if drifted:
        print("Refusing to apply — these need attention first:\n", file=sys.stderr)
        for d in drifted:
            print(f"  · {d}", file=sys.stderr)
        print("\nA command that changed under a grant you already gave is exactly what the pin",
              file=sys.stderr)
        print("is for. Re-run `generate` to re-present it, then look again before ticking.",
              file=sys.stderr)
        return EX_UNUSABLE

    for s in skipped:
        print(f"  skip · {s}")
    if skipped and not plan:
        print("\nEverything ticked has already been applied. Nothing to do.")
        return 0

    if args.plan:
        print(f"Would apply {len(plan)} gate(s):\n")
        for gid, cmd in plan:
            print(f"  {gid}\n      {cmd}\n")
        print("Nothing executed (--plan).")
        return 0

    RECEIPTS.mkdir(parents=True, exist_ok=True)
    receipt = {"applied_at": _now(), "head": _head(), "results": []}
    failures = 0
    for gid, cmd in plan:
        print(f"── {gid}\n   {cmd}")
        out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        ok = out.returncode == 0
        failures += 0 if ok else 1
        print(f"   {'OK' if ok else f'FAILED rc={out.returncode}'}")
        if not ok:
            tail = (out.stderr or out.stdout).strip().splitlines()[-6:]
            for t in tail:
                print(f"     {t}")
        receipt["results"].append({"gate_id": gid, "cmd": cmd, "rc": out.returncode,
                                   "ok": ok, "stdout_tail": (out.stdout or "")[-2000:],
                                   "stderr_tail": (out.stderr or "")[-2000:]})

    # Filename-safe compact stamp: the ISO form carries ':' and a '+00:00' offset.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RECEIPTS / f"unblock_{stamp}_{os.getpid()}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"\nreceipt: {path.relative_to(REPO_ROOT)}")

    if failures:
        print(f"\n{failures} gate(s) FAILED. Each is an AGENT defect, not an operator problem:",
              file=sys.stderr)
        print("pre-validation should have caught it. The coordinator-daemon will attribute it on",
              file=sys.stderr)
        print("its next tick. Repair and re-present the SAME gate — do not open a new one.",
              file=sys.stderr)
        return EX_FAILED
    print(f"\nApplied {len(plan)} gate(s) cleanly. The coordinator-daemon picks the outcome up on")
    print("its next tick — this command deliberately does not commit or write bus files.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="unblock_artifact.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="(re)write the artifact and its per-gate pins")
    g.set_defaults(func=cmd_generate)
    s = sub.add_parser("show", help="list gates and their state; writes nothing")
    s.set_defaults(func=cmd_show)
    a = sub.add_parser("apply", help="apply every ticked gate")
    a.add_argument("--plan", action="store_true", help="show what would run; execute nothing")
    a.set_defaults(func=cmd_apply)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

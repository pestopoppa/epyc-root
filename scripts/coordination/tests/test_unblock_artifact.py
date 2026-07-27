#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/coordination/unblock_artifact.py (rider R8).

Runs against a throwaway tree with REPO_ROOT redirected, so the real bus, real
token queue and real receipts are never touched.

The cases that matter are the adversarial ones the R8 design review surfaced:
per-line independence (striking one line must not invalidate the others), command
drift after a grant, a failing command being attributed to the AGENT, undated
adjudication being malformed, and applying twice not re-running anything.

Usage: scripts/coordination/tests/test_unblock_artifact.py
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

REAL_ROOT = Path(__file__).resolve().parents[3]
MODULE = REAL_ROOT / "scripts" / "coordination" / "unblock_artifact.py"

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, why: str) -> None:
    RESULTS.append((bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {why}")


def fresh(tmp: Path):
    """Load the module with every path redirected into `tmp`."""
    spec = importlib.util.spec_from_file_location(f"ua_{tmp.name}", MODULE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.REPO_ROOT = tmp
    m.BUS_ROOT = tmp / "coordination" / "session-bus"
    m.TOKEN_QUEUE = m.BUS_ROOT / "tokens" / "token-queue.md"
    m.ARTIFACT = m.BUS_ROOT / "tokens" / "unblock.md"
    m.PINS = m.BUS_ROOT / "tokens" / "unblock.pins.json"
    m.RECEIPTS = tmp / "artifacts" / "operator" / "unblock-receipts"
    for d in ("tokens", "outbox", "heartbeats", "cursors", "inbox"):
        (m.BUS_ROOT / d).mkdir(parents=True, exist_ok=True)
    (m.BUS_ROOT / "queue.jsonl").write_text("")
    # held_tasks()/token_commands() import the real session_bus; give them a bus.
    m.held_tasks = lambda: {}
    return m


def write_gates(m, lines: list[str]) -> None:
    m.TOKEN_QUEUE.write_text("# tokens\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


def write_request(m, agent: str, gate: str, cmd: str) -> None:
    p = m.BUS_ROOT / "outbox" / f"{agent}.jsonl"
    with p.open("a") as fh:
        fh.write(json.dumps({
            "schema_version": "session_bus.msg.v1", "id": f"msg-20260727T000000Z-1-{agent}",
            "ts": "2026-07-27T00:00:00+00:00", "from": agent, "to": "coordinator-daemon",
            "kind": "token-request", "task_id": f"task-for-{gate}",
            "payload": {"gate_id": gate, "block_ref": "x",
                        "validated": {"cmd": cmd, "dry_run_exit": 0,
                                      "dry_run_evidence": "dry run clean"}}}) + "\n")


class Args:
    def __init__(self, plan=False):
        self.plan = plan


def main() -> int:
    # ---- generate + pending presentation ----
    print("== generate ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        write_gates(m, ["- [ ] **G-1** — first gate", "- [ ] **G-2** — second gate"])
        write_request(m, "codex", "G-1", "true")
        m.cmd_generate(Args())
        text = m.ARTIFACT.read_text()
        check("pending 2" in text, "counts pending gates")
        check("G-1" in text and "G-2" in text, "lists both gates")
        check("no pre-validated command recorded" in text,
              "G-2 reported as unapplicable rather than guessed at")
        pins = json.loads(m.PINS.read_text())
        check(list(pins["gates"]) == ["G-1"], "only the validated gate is pinned")

    # ---- grant -> apply ----
    print("\n== grant then apply ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        marker = Path(d) / "ran.txt"
        write_gates(m, ["- [ ] **G-1** — first gate"])
        write_request(m, "codex", "G-1", f"touch {marker}")
        m.cmd_generate(Args())
        write_gates(m, [f"- [x] **G-1** — first gate GRANTED 2026-07-27"])
        rc = m.cmd_apply(Args())
        check(rc == 0, f"apply returns 0 (got {rc})")
        check(marker.exists(), "the granted command actually ran")
        receipts = list(m.RECEIPTS.glob("unblock_*.json"))
        check(len(receipts) == 1, "one receipt written")
        r = json.loads(receipts[0].read_text())
        check(r["results"][0]["ok"] is True, "receipt records success")

        # applying again must NOT re-run it
        marker.unlink()
        rc2 = m.cmd_apply(Args())
        check(rc2 == 0 and not marker.exists(),
              "second apply skips an already-applied gate (no double-run)")

    # ---- regenerating AFTER a tick must not orphan the grant ----
    print("\n== generate after the tick (deadlock regression) ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        marker = Path(d) / "regen.txt"
        write_gates(m, ["- [ ] **G-1** — one"])
        write_request(m, "codex", "G-1", f"touch {marker}")
        m.cmd_generate(Args())
        write_gates(m, ["- [x] **G-1** — one GRANTED 2026-07-27"])
        m.cmd_generate(Args())          # coordinator-agent regenerates periodically
        rc = m.cmd_apply(Args())
        check(rc == 0, f"grant survives a regenerate (got rc={rc})")
        check(marker.exists(), "the command still applied after regeneration")
        pins = json.loads(m.PINS.read_text())
        check("G-1" in pins["gates"], "a granted gate stays pinned, not only pending ones")

    # ---- struck stays held, and per-line independence ----
    print("\n== struck + per-line independence ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        a, b = Path(d) / "a.txt", Path(d) / "b.txt"
        write_gates(m, ["- [ ] **G-1** — one", "- [ ] **G-2** — two"])
        write_request(m, "codex", "G-1", f"touch {a}")
        write_request(m, "codex", "G-2", f"touch {b}")
        m.cmd_generate(Args())
        write_gates(m, ["- [x] **G-1** — one GRANTED 2026-07-27",
                        "- [ ] **G-2** — two STRUCK 2026-07-27 — not this round"])
        rc = m.cmd_apply(Args())
        check(rc == 0, "striking one line does not fail the apply")
        check(a.exists(), "the granted gate applied")
        check(not b.exists(), "the struck gate did NOT run")
        m.cmd_generate(Args())
        text = m.ARTIFACT.read_text()
        check("Struck" in text and "G-2" in text, "struck gate is re-presented, not dropped")
        check("held, not dropped" in text, "artifact states that a struck gate stays held")

    # ---- command drift after a grant ----
    print("\n== command drift after the grant ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        bad = Path(d) / "should-not-exist.txt"
        write_gates(m, ["- [ ] **G-1** — one"])
        write_request(m, "codex", "G-1", "true")
        m.cmd_generate(Args())
        write_gates(m, ["- [x] **G-1** — one GRANTED 2026-07-27"])
        # the agent swaps the command AFTER the operator granted it
        (m.BUS_ROOT / "outbox" / "codex.jsonl").write_text("")
        write_request(m, "codex", "G-1", f"touch {bad}")
        rc = m.cmd_apply(Args())
        check(rc == 3, f"refuses with rc 3 on drift (got {rc})")
        check(not bad.exists(), "the swapped command did NOT run")

    # ---- a failing command is an AGENT defect ----
    print("\n== failing command ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        write_gates(m, ["- [ ] **G-1** — one"])
        write_request(m, "codex", "G-1", "exit 7")
        m.cmd_generate(Args())
        write_gates(m, ["- [x] **G-1** — one GRANTED 2026-07-27"])
        rc = m.cmd_apply(Args())
        check(rc == 2, f"apply returns 2 on failure (got {rc})")
        r = json.loads(next(iter(m.RECEIPTS.glob("unblock_*.json"))).read_text())
        check(r["results"][0]["rc"] == 7, "receipt records the real exit code")
        check(r["results"][0]["ok"] is False, "receipt marks it failed")

    # ---- undated adjudication is malformed ----
    print("\n== undated adjudication ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        write_gates(m, ["- [x] **G-1** — one GRANTED"])
        gates = m.parse_token_queue()
        check(gates[0]["malformed"] is not None, "an undated grant is malformed")
        m.cmd_generate(Args())
        check("Malformed" in m.ARTIFACT.read_text(), "malformed gates surface in the artifact")

    # ---- --plan executes nothing ----
    print("\n== --plan ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        marker = Path(d) / "planned.txt"
        write_gates(m, ["- [ ] **G-1** — one"])
        write_request(m, "codex", "G-1", f"touch {marker}")
        m.cmd_generate(Args())
        write_gates(m, ["- [x] **G-1** — one GRANTED 2026-07-27"])
        rc = m.cmd_apply(Args(plan=True))
        check(rc == 0 and not marker.exists(), "--plan runs nothing")
        check(not m.RECEIPTS.exists() or not list(m.RECEIPTS.glob("*")),
              "--plan writes no receipt")

    # ---- dash-character independence ----
    print("\n== dash variants parse identically ==")
    with tempfile.TemporaryDirectory() as d:
        m = fresh(Path(d))
        write_gates(m, ["- [ ] **G-1** — em dash", "- [ ] **G-2** -- double hyphen",
                        "- [ ] **G-3** - single hyphen"])
        ids = [g["gate_id"] for g in m.parse_token_queue()]
        check(ids == ["G-1", "G-2", "G-3"], f"all three dash forms parse (got {ids})")

    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for w in failed:
        print(f"  FAILED: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

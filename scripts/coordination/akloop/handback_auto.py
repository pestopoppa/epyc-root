#!/usr/bin/env python3
"""handback_auto.py - AK parallel-loop P5(a) wiring: stamp every AK subagent hand-back automatically.

handback_verify.py is the verifier; this is the thin adapter that runs it on each hand-back without the owner
remembering to. It is called from the PostToolUse(Agent|Task) hook scripts/hooks/posttool_handback_sweep.py, which
already fires on every subagent hand-back and receives the returned text as `tool_response`.

WHY THIS HOOK POINT (least invasive of the three considered):
  * hook already registered for exactly this event -> no .claude/settings.json edit, no new trust-boundary surface;
  * a file watcher would need a hand-back FILE, but subagent reports only exist as the Agent tool result;
  * wrapping brief.py would only cover briefs the owner generated, not the report that comes back.

AK hand-back = the dispatch prompt carries the brief.py STAMP_CONTRACT (the `CLAIMS:` instruction) or the report itself
has a `CLAIMS:` line. Other subagents (Explore, clerk, ...) are left alone. An AK hand-back with no CLAIMS block gets
an UNVERIFIED stamp (handback_verify: no checkable claim). Read-only: git queries and file stats, no fetch, no rerun,
never raises. The context line carries only the stamp, the verifier's own reason and claim TYPES -- never
subagent-authored text (sweep hook rule P5-1). Every stamp is also appended to STAMP_LEDGER for audit.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handback_verify as hv  # noqa: E402

STAMP_LEDGER = os.environ.get("HANDBACK_STAMP_LEDGER") or "/mnt/raid0/llm/" + "tmp/handback-stamps/stamps.jsonl"
CONTRACT_MARK = "end with a `CLAIMS:` block"      # brief.py STAMP_CONTRACT[0]
CLAIMS_LINE = re.compile(r"^\s*\**CLAIMS\**\s*:", re.M | re.I)


def _text(x):
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "\n".join(_text(i) for i in x)
    if isinstance(x, dict):
        return _text(x.get("text") if "text" in x else x.get("content"))
    return ""


def is_ak_handback(prompt, report):
    return CONTRACT_MARK in (prompt or "") or bool(CLAIMS_LINE.search(report or ""))


def stamp_payload(payload, repo=None, ledger=STAMP_LEDGER):
    """Hook payload -> one context line, or None when this is not an AK hand-back. Never raises."""
    try:
        if payload.get("hook_event_name") != "PostToolUse" or payload.get("tool_name") not in ("Agent", "Task"):
            return None
        prompt = _text((payload.get("tool_input") or {}).get("prompt"))
        report = _text(payload.get("tool_response"))
        if not is_ak_handback(prompt, report):
            return None
        repo = repo or payload.get("cwd") or hv.DEFAULT_REPO
        stamp = hv.verify(hv.extract_claims(report), hv.Ctx(repo))
        failed = sorted({r["claim"].get("type", "?") for r in stamp["results"] if not r["ok"]})
        try:
            os.makedirs(os.path.dirname(ledger), exist_ok=True)
            with open(ledger, "a") as f:
                f.write(json.dumps({"at": stamp["at"], "session": payload.get("session_id"),
                                    "stamp": stamp["stamp"], "reason": stamp["reason"],
                                    "results": stamp["results"]}) + "\n")
        except OSError:
            pass
        extra = f" failed claim types: {', '.join(failed)}." if failed else ""
        return (f"HAND-BACK STAMP: {stamp['stamp']} ({stamp['reason']}).{extra} Only VERIFIED is believed; "
                f"UNVERIFIED = treat as not done (handback_verify, AKPL-P5).")
    except Exception:   # noqa: BLE001 - a hook must never break the hand-back
        return None

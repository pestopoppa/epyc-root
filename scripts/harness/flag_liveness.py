#!/usr/bin/env python3
"""HIL-RE-3: telemetry read/write-asymmetry invariant for harness flags.

A flag that FIRES on the write side while its consumer counter is identically
zero is wired to nothing: any sweep that varies it measures noise. Such a flag is
marked SILENT, excluded from sweeps, and reported as ONE typed event.

Verdict rules (zero inference; pure function of two counters per flag):
  writes > 0 and consumer_reads == 0   -> silent (the invariant trips)
  writes > 0 and consumer_reads > 0    -> live
  writes == 0                          -> idle (never fired; no asymmetry to claim)
  consumer_reads is None / absent      -> unmeasured (an absent counter is not a
                                          zero counter; no verdict, kept in sweeps)

Input JSON: {"flags": {"<name>": {"writes": int, "consumer_reads": int|null}}}
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

EVENT_SCHEMA = "harness.flag_silent.v1"


def classify(rec: dict) -> str:
    writes, reads = rec.get("writes"), rec.get("consumer_reads")
    if not isinstance(writes, int) or writes < 0:
        return "unmeasured"
    if writes == 0:
        return "idle"
    if not isinstance(reads, int) or isinstance(reads, bool) or reads < 0:
        return "unmeasured"
    return "silent" if reads == 0 else "live"


def evaluate(flags: dict[str, dict]) -> dict:
    """Return {verdicts, silent_events, sweep_eligible}; one event per silent flag."""
    verdicts = {name: classify(rec) for name, rec in flags.items()}
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    events = [{"schema_version": EVENT_SCHEMA, "ts": ts, "kind": "flag-silent", "flag": n,
               "writes": flags[n]["writes"], "consumer_reads": 0,
               "action": "excluded from sweeps until its consumer counter is non-zero"}
              for n, v in sorted(verdicts.items()) if v == "silent"]
    return {"verdicts": verdicts, "silent_events": events,
            "sweep_eligible": sorted(n for n, v in verdicts.items() if v != "silent")}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: flag_liveness.py <counters.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        result = evaluate(json.load(fh)["flags"])
    for ev in result["silent_events"]:
        print(json.dumps(ev, sort_keys=True))
    return 1 if result["silent_events"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

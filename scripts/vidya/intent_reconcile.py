"""PR3: reconcile every intent frame against a real ratification artifact.

Spec §15: "every intent frame in the ledger is reconciled against an actual ratification artifact
before any promotion proposal is written. A frame with no matching artifact is a defect."

Intent-frame forgery is the pilot's one accepted security hole — any local process can emit one,
and that is tolerable only because shadow state gates nothing. The spec makes reconciliation a
pilot-EXIT check, which is the shape that rots: a one-time gate nobody runs until the day it
matters, by which point there is a backlog to adjudicate under pressure.

So this is a standing check instead. It passes today because the ledger holds ZERO intent frames
and the frame type is not yet emitted by anything (measured 2026-08-10) — and a check that passes
vacuously is worth exactly nothing, which is why it fails loudly the moment one appears without a
matching artifact rather than waiting to be remembered.

    intent_reconcile.py            # exit 0 if every intent frame resolves
    intent_reconcile.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ledger import Ledger  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / ".vidya" / "ledger.jsonl"
FT_INTENT = "epyc.vidya/frame/human_intent_recorded/v1"

# Where a genuine operator ratification leaves a durable trace.
ARTIFACT_DIRS = ("artifacts/operator", "docs/design", "handoffs/active", "handoffs/completed")


def _artifact_exists(ref: str) -> bool:
    """A reference resolves if it names a file that is actually on disk."""
    if not ref:
        return False
    p = (REPO_ROOT / ref).resolve()
    try:
        p.relative_to(REPO_ROOT)
    except ValueError:
        return False          # escapes the repo — not a ratification artifact
    return p.is_file()


def reconcile(ledger_path: Path = LEDGER) -> dict:
    if not ledger_path.exists():
        return {"intent_frames": 0, "unreconciled": [], "ok": True,
                "note": "no ledger at this path"}

    frames = [r.frame for r in Ledger(ledger_path).read_all()]
    intents = [f for f in frames if f.get("frame_type") == FT_INTENT]

    unreconciled = []
    for f in intents:
        assertion = f.get("assertion") or {}
        provenance = f.get("provenance") or {}
        ref = (assertion.get("ratification_artifact")
               or provenance.get("ratification_artifact")
               or assertion.get("artifact"))
        if not _artifact_exists(str(ref or "")):
            unreconciled.append({
                "frame_id": f.get("frame_id"),
                "actor": (f.get("pubinfo") or {}).get("actor"),
                "claimed_artifact": ref,
                "reason": "no such file in the repo" if ref else "no artifact reference at all",
            })

    return {
        "intent_frames": len(intents),
        "unreconciled": unreconciled,
        "ok": not unreconciled,
        "note": (
            "PASSES VACUOUSLY: the ledger holds no intent frames and nothing emits them yet. "
            "That is the current state, not a clean bill of health — the value of this check is "
            "that it starts failing the moment an unbacked intent frame appears."
            if not intents else
            f"{len(intents)} intent frame(s) present; "
            f"{len(unreconciled)} cannot be resolved to an artifact."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", help=f"ledger path (default {LEDGER})")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    result = reconcile(Path(args.ledger) if args.ledger else LEDGER)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"intent frames: {result['intent_frames']}  "
              f"unreconciled: {len(result['unreconciled'])}")
        print(f"  {result['note']}")
        for u in result["unreconciled"]:
            print(f"  DEFECT {u['frame_id']}: {u['reason']} (claimed {u['claimed_artifact']!r}, "
                  f"actor {u['actor']!r})")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Private writer -> ledger -> actual loop-belief planning-context check; never runs inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "scripts" / "vidya"
sys.path.insert(0, str(HERE))
import loop_beliefs  # noqa: E402


class PrivateLedgerSync:
    """The canary uses an isolated ledger and an explicit local freshness receipt."""
    def status(self, *args, **kwargs):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1,
                "synced_max_id": 1, "last_sync": datetime.now(timezone.utc).isoformat()}

    def sync(self, *args, **kwargs):
        raise AssertionError("private canary ledger unexpectedly requested sync")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--native-run", required=True)
    ap.add_argument("--ledger", required=True, help="private scratch ledger; never canonical")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    native = Path(a.native_run).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    ledger = Path(a.ledger).resolve()
    rec = json.loads((native / "RUN_RECORD.json").read_text())
    argv = rec["recipe"]["argv"]
    model = Path(argv[argv.index("-m") + 1]).name
    target = {"model_file": model, "quant": "Q8_0", "backend": "gpu", "device": "mi210_0",
              "model_sha256": rec["model_sha256"], "recipe": rec["recipe"]["name"]}
    as_of = datetime.now(timezone.utc).isoformat()
    answer = loop_beliefs.prepare(
        "cme7t-native-diagnostic", target, ledger=ledger, index_path=out / "private-index.json",
        as_of=as_of, sync_module=PrivateLedgerSync(), known_good=out / "known-good.json",
        alarm_state=out / "alarm-state.json", alarm_config=out / "private-alarm.yaml",
        read_log=out / "read-log.jsonl", max_claims=64, max_bytes=500000)
    context = out / "planner-context.json"
    context.write_text(json.dumps(answer, indent=2, sort_keys=True, default=str) + "\n")
    claims = answer.get("evidence", {}).get("claims", [])
    visible = [c for c in claims if c.get("source_kind") == "cme7t-response"]
    if answer.get("status") != "ready" or not visible:
        raise RuntimeError("actual loop_beliefs planning context did not expose CME-7T evidence")
    receipt = {
        "status": "partial", "inference_run": False,
        "planning_reader": "scripts/vidya/loop_beliefs.py:prepare",
        "planning_context": "CME-7T native diagnostic tuples visible",
        "visible_claim_count": len(visible), "visible_claim_ids": [c["claim_id"] for c in visible],
        "do_not_repeat_history_loaded": False,
        "blocker": "No CME-7T planning consumer/no-repeat history loader was found in this root view; do not mark wired.",
        "target": target, "ledger_path": str(ledger),
        "native_run_record_sha256": sha(native / "RUN_RECORD.json"),
        "planner_context_sha256": sha(context), "status_reason": answer.get("reason"),
    }
    (out / "canary-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out / "canary-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

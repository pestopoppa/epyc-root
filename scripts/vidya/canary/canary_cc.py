#!/usr/bin/env python3
"""Canary CC (VB-CC-PILOT): the committed-conclusion register reaches the AutoKernel planner.

NO model call, NO inference. On a scratch COPY of the canonical ledger (plus its intake sync
marker, but NOT the register marker) this runs the real consumer read,
`loop_beliefs.py prepare --consumer autokernel.planner`, for two GPU targets (Qwen3.8-27B Q8_0
and Q38FN UD-IQ4_XS). `ensure_current` must see origin/main's register as stale and fold it into
the copy (VB-CC-3), then the rendered context must carry the 2026-11-06 AK-ASM verdicts:

  27B   tried-mechanisms: gfx90a-asm:h10-* improved, h4-* and h9-* regressed, h14-* null;
        host tier: the int8-MFMA-rate device fact; harness tier: the three harness lessons.
  Q38FN tried-mechanisms: gfx90a-asm:h12-* and h13-* improved.

Dev mode: CC_REGISTER=<file> pre-ingests that register into the copy instead of relying on
origin/main (before the register is merged). The canonical ledger is hashed before and after
and must be unchanged. Prints one `CANARY_RESULT: {...}` line; exit 0 PASS / 1 FAIL / 2 UNKNOWN.
Usage: CANARY_SCRATCH=/mnt/raid0/llm/tmp/<new dir> python3 canary_cc.py <root checkout>
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CANONICAL = Path("/mnt/raid0/llm/state/vidya")
CONSUMER = "autokernel.planner"
T27B = {"label": "27B", "model_file": "Qwen3.8-27B-Q8_0.gguf", "quant": "Q8_0",
        "backend": "gpu"}
TQ38 = {"label": "Q38FN", "model_file": "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
        "backend": "gpu"}
EXPECT_TRIED = {
    "27B": {"gfx90a-asm:h10-gqa-packed-verify-attn": "improved",
            "gfx90a-asm:h4-int8-mmq-prefill": "regressed",
            "gfx90a-asm:h9-int8-gemm-per32-scale": "regressed",
            "gfx90a-asm:h14-fused-qknorm-rope-kvwrite": "null"},
    "Q38FN": {"gfx90a-asm:h12-fused-qsa-attention": "improved",
              "gfx90a-asm:h13-fused-hc-seam": "improved"},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result(status: str, **kw) -> int:
    print("CANARY_RESULT: " + json.dumps({"loop": "CC", "status": status, **kw}, sort_keys=True))
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[status]


def main() -> int:
    if len(sys.argv) != 2:
        return result("UNKNOWN", reason="usage: canary_cc.py <root checkout>")
    root = Path(sys.argv[1]).resolve()
    base = Path(os.environ.get("CANARY_SCRATCH", "")).resolve()
    tmp = Path("/mnt/raid0/llm/tmp")
    if not base.is_relative_to(tmp) or base == tmp or base.exists():
        return result("UNKNOWN", reason="CANARY_SCRATCH must be a NEW dir under /mnt/raid0/llm/tmp")
    state = base / "state"
    state.mkdir(parents=True)
    canonical_before = sha(CANONICAL / "ledger.jsonl")
    for name in ("ledger.jsonl", "ledger.jsonl.sync.json"):
        shutil.copy2(CANONICAL / name, state / name)
    if sha(state / "ledger.jsonl") != canonical_before:
        return result("UNKNOWN", reason="canonical ledger changed during copy")
    (base / "alarm").mkdir()
    (base / "alarm" / "alarm_config.yaml").write_text(
        "schema_version: alarm_channel.config.v1\nenabled: false\nbackend: ntfy\n"
        "advisory_mirror: false\nntfy:\n  url: https://ntfy.sh/REPLACE-ME-canary-disabled\n"
        "  timeout_s: 1\nemail:\n  to: REPLACE-ME@example.invalid\nfile:\n"
        f"  path: {base / 'alarm/alarms.jsonl'}\n")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    vidya = root / "scripts" / "vidya"
    dev = os.environ.get("CC_REGISTER")
    if dev:
        r = subprocess.run([sys.executable, str(vidya / "cli.py"), "--ledger",
                            str(state / "ledger.jsonl"), "ingest", "committed-conclusion",
                            "--path", dev, "--as-of", as_of, "--only-new"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return result("UNKNOWN", reason="dev pre-ingest failed", stderr=r.stderr[-400:])
    failures, summary = [], {}

    def prepare(target, stamp):
        return subprocess.run(
            [sys.executable, str(vidya / "loop_beliefs.py"), "prepare", "--consumer", CONSUMER,
             "--target-json", json.dumps(target), "--ledger", str(state / "ledger.jsonl"),
             "--read-log", str(state / "reads.jsonl"), "--as-of", stamp,
             "--alarm-state", str(base / "alarm" / "alarm_state.json"),
             "--alarm-config", str(base / "alarm" / "alarm_config.yaml"),
             "--known-good", str(state / "known-good.json"), "--max-claims", "64"],
            capture_output=True, text=True, cwd=str(root))

    # Warm-up read: ensure_current folds the stale register (VB-CC-3) with frames stamped at
    # fold time, i.e. after this read's as_of; they are visible to every later read.
    prepare(T27B, as_of)
    import time
    time.sleep(2)
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for target in (T27B, TQ38):
        r = prepare(target, as_of)
        try:
            answer = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return result("UNKNOWN", reason="prepare produced no JSON", stderr=r.stderr[-400:])
        (base / f"answer-{target['label']}.json").write_text(json.dumps(answer, indent=1,
                                                                        default=str))
        text = json.dumps(answer, default=str)
        ev = answer.get("evidence") or {}
        section = str(ev.get("section") or "")
        (base / f"section-{target['label']}.md").write_text(section)
        cc_hits = section.count("clm_cc:v1:")
        got = {e.get("mechanism_id"): e.get("outcome") for e in ev.get("tried_index") or []
               if e.get("model_file") == target["model_file"]}
        got = {k: v for k, v in got.items() if k in EXPECT_TRIED[target["label"]]}
        for mech, want in EXPECT_TRIED[target["label"]].items():
            if got.get(mech) != want:
                failures.append(f"{target['label']}: {mech} expected {want}, got {got.get(mech)}")
        claims = ev.get("claims") or []
        host = [c for c in claims if c.get("tier") == "host"
                and str(c.get("claim_id", "")).startswith("clm_cc:")]
        harness = [c for c in claims if c.get("tier") == "harness"
                   and str(c.get("claim_id", "")).startswith("clm_cc:")]
        if target["label"] == "27B":
            if "gfx90a-asm:int8-mfma-rate" not in section or not host:
                failures.append("27B: int8-MFMA device fact missing from host tier")
            if len(harness) < 3:
                failures.append(f"27B: expected 3 harness lessons, got {len(harness)}")
        summary[target["label"]] = {"status": answer.get("status"), "tried": got, "host_cc": len(host), "harness_cc": len(harness),
                                    "committed_conclusion_mentions": cc_hits,
                                    "fresh": (answer.get("ledger_state") or {}).get("freshness")}
    if sha(CANONICAL / "ledger.jsonl") != canonical_before:
        return result("UNKNOWN", reason="canonical ledger changed during the canary", **summary)
    cc_marker = state / "ledger.jsonl.cc-sync.json"
    summary["register_folded_by_sync"] = cc_marker.exists()
    if not dev and not cc_marker.exists():
        failures.append("ensure_current did not fold the register (no cc-sync marker)")
    summary["scratch"] = str(base)
    return result("FAIL" if failures else "PASS", failures=failures, **summary)


if __name__ == "__main__":
    sys.exit(main())

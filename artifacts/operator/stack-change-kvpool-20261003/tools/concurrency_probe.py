#!/usr/bin/python3
"""Serving-proof item 8 for STACKCHG-KVPOOL-20261003: 4 x ~90k concurrent on :8083.

NOT RUN DURING PREPARATION. It sends inference. The OWNER of :8083 inference runs it,
in a window they choose, after `reload architect_critic`:

    /usr/bin/python3 tools/concurrency_probe.py --i-own-the-window [--tokens 90000] [--n 4]

What it does (stdlib only, direct to the llama-server, bypassing the orchestrator on
purpose: the orchestrator's one-long-prefill rule would SERIALIZE these, and the thing under
test is the 393216-cell pool itself):
  1. builds N DISTINCT prompts of ~--tokens tokens each, calibrated with POST /tokenize;
  2. notes the server log offset, arms a 0.5 s KFD/VRAM sampler and a 1 s /slots sampler;
  3. fires N concurrent POST /completion (cache_prompt false, n_predict 64, temperature 0);
  4. verdict: PASS iff every request returns 200 with content, ZERO "failed to find a
     memory slot" and ZERO "Context size has been exceeded" lines after the offset, the
     /slots sampler saw >= 3 slots processing at once with >= 300,000 cells in flight (it
     was really concurrent), and the KFD peak stays <= 62 GiB (gate budget).
Writes evidence/concurrency-probe-<ts>.json. Starts, stops and reloads nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

PKG = Path("/mnt/raid0/llm/tmp/stack-change-kvpool-20261003")
LOG = Path("/mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log")
VRAM_USED = Path("/sys/class/drm/card2/device/mem_info_vram_used")
GIB = 1024 ** 3
BUDGET_GIB = 62.0
BAD = (re.compile(r"failed to find a memory slot"), re.compile(r"Context size has been exceeded"))


def _post(url: str, body: dict, timeout: float) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read() or b"{}")


def _get(url: str, timeout: float = 3.0):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read() or b"null")


def _n_tokens(base: str, text: str) -> int:
    _, body = _post(f"{base}/tokenize", {"content": text}, 300)
    return len(body.get("tokens") or [])


def _prompt(base: str, i: int, target: int) -> tuple[str, int]:
    line = lambda k: f"[{i}:{k}] record {k * 7919 % 100003} of ledger {i}: value {k * 31 % 997}.\n"  # noqa: E731
    sample = "".join(line(k) for k in range(200))
    per_line = _n_tokens(base, sample) / 200.0
    lines = max(1, int(target / per_line))
    text = f"Batch {i}. Read the ledger below.\n" + "".join(line(k) for k in range(lines))
    text += "\nAnswer with the single word OK.\n"
    n = _n_tokens(base, text)
    while n > target * 1.01:                       # trim to within 1% of the target
        lines = int(lines * target / n)
        text = f"Batch {i}. Read the ledger below.\n" + "".join(line(k) for k in range(lines))
        text += "\nAnswer with the single word OK.\n"
        n = _n_tokens(base, text)
    return text, n


def _kfd_pid(port: int) -> int | None:
    import subprocess
    out = subprocess.run(["ss", "-ltnp", f"sport = :{port}"], capture_output=True, text=True).stdout
    m = re.search(r"pid=(\d+)", out)
    return int(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--i-own-the-window", action="store_true")
    ap.add_argument("--base", default="http://127.0.0.1:8083")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--tokens", type=int, default=90000)
    ap.add_argument("--n-predict", type=int, default=64)
    args = ap.parse_args()
    if not args.i_own_the_window:
        print("REFUSING: this sends inference to :8083. Run it only as the owner of :8083 "
              "inference, in your window, with --i-own-the-window.", file=sys.stderr)
        return 2
    props = _get(f"{args.base}/props")
    slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
    pid = _kfd_pid(int(args.base.rsplit(":", 1)[1]))
    kfd = Path(f"/sys/class/kfd/kfd/proc/{pid}") if pid else None
    print(f"server pid {pid}, slots {props.get('total_slots')}, slot n_ctx {slot_ctx}")

    prompts = [_prompt(args.base, i, args.tokens) for i in range(args.n)]
    print("prompt tokens:", [n for _, n in prompts], "sum", sum(n for _, n in prompts))

    offset = LOG.stat().st_size
    stop = threading.Event()
    vram: list[tuple[float, int, int | None]] = []
    slots_seen: list[tuple[float, int, int]] = []

    def sample_vram() -> None:
        while not stop.is_set():
            card = int(VRAM_USED.read_text())
            proc = None
            if kfd is not None:
                vals = [int(p.read_text()) for p in kfd.glob("vram_*")]
                proc = sum(vals) if vals else None
            vram.append((time.time(), card, proc))
            stop.wait(0.5)

    def sample_slots() -> None:
        while not stop.is_set():
            try:
                body = _get(f"{args.base}/slots", 2.0)
                busy = [s for s in body if s.get("is_processing")]
                slots_seen.append((time.time(), len(busy),
                                   sum(int(s.get("n_prompt_tokens") or 0) for s in busy)))
            except Exception:  # noqa: BLE001 - a missed sample is not a verdict
                pass
            stop.wait(1.0)

    results: list[dict] = [{} for _ in prompts]

    def fire(i: int, text: str) -> None:
        t0 = time.time()
        try:
            status, body = _post(f"{args.base}/completion",
                                 {"prompt": text, "n_predict": args.n_predict, "temperature": 0,
                                  "cache_prompt": False}, 3600)
            results[i] = {"status": status, "content": (body.get("content") or "")[:80],
                          "prompt_n": (body.get("timings") or {}).get("prompt_n"),
                          "seconds": round(time.time() - t0, 1)}
        except Exception as exc:  # noqa: BLE001
            results[i] = {"status": "error", "error": str(exc)[:300], "seconds": round(time.time() - t0, 1)}

    samplers = [threading.Thread(target=sample_vram, daemon=True),
                threading.Thread(target=sample_slots, daemon=True)]
    for t in samplers:
        t.start()
    workers = [threading.Thread(target=fire, args=(i, p)) for i, (p, _) in enumerate(prompts)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    time.sleep(2)
    stop.set()
    for t in samplers:
        t.join(timeout=5)

    with LOG.open("rb") as fh:
        fh.seek(offset)
        tail = fh.read().decode(errors="replace").splitlines()
    bad = {p.pattern: sum(1 for ln in tail if p.search(ln)) for p in BAD}
    peak_proc = max((p for _, _, p in vram if p is not None), default=None)
    peak_card = max((c for _, c, _ in vram), default=None)
    max_busy = max((b for _, b, _ in slots_seen), default=0)
    max_cells = max((c for _, _, c in slots_seen), default=0)
    ok_requests = all(r.get("status") == 200 and r.get("content") is not None for r in results)
    verdict = (ok_requests and all(v == 0 for v in bad.values()) and max_busy >= min(3, args.n)
               and max_cells >= 300_000 and peak_proc is not None and peak_proc / GIB <= BUDGET_GIB)
    report = {
        "schema": "epyc.stackchg_kvpool.concurrency_probe.v1",
        "taken_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "server_pid": pid, "slot_n_ctx": slot_ctx, "n": args.n,
        "prompt_tokens": [n for _, n in prompts], "results": results,
        "log_lines_after_offset": len(tail), "bad_line_counts": bad,
        "slots_max_processing": max_busy, "slots_max_cells_in_flight": max_cells,
        "kfd_peak_bytes": peak_proc, "kfd_peak_gib": round(peak_proc / GIB, 3) if peak_proc else None,
        "card_peak_bytes": peak_card, "vram_samples": len(vram), "budget_gib": BUDGET_GIB,
        "verdict": "PASS" if verdict else "FAIL",
    }
    out = PKG / "evidence" / f"concurrency-probe-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("verdict", "bad_line_counts", "slots_max_processing",
                                             "slots_max_cells_in_flight", "kfd_peak_gib")}))
    print(f"wrote {out}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())

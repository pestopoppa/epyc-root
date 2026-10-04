#!/usr/bin/python3
"""UFH14-B4g — the 27B DFlash2 prompt-cache entry cost on the CURRENT :8083 shape
(np 4, -c 393216 unified, q8_0 KV, DFlash2 n-max 7), for PFX-SEL-1's entry cost
(agentic-serving-harness-fixes.md UFH14-B4g; design ufh14-b4-prefix-cache-policy §4.4).

Source lines (default verbosity, logs/llama-server-8083.log):
  prompt_save: - saving prompt with length N, total state size = X MiB (draft: Y MiB)
  update:      - prompt 0x..: N tokens, checkpoints: C, X MiB     (entry incl. checkpoints)
  create_check: created context checkpoint i of 32 (... n_tokens = N, size = X MiB)
  alloc:       - making room for prompt cache entry, removing oldest entry (size = X MiB)

Mode:
  1. PARSE the log from --since-offset (default: the start of the CURRENT launch, i.e. the last
     `load_model: initializing ... n_ctx_slot = 262144` line), so the T7 / KVU-16b long calls
     already in this window count. Pass --since-report <q38_t7 report.json> to start at T7.
  2. TRIGGER (only if --trigger always, or auto and < --min-points distinct save lengths >= 4k):
     for each size in --sizes: one /completion of that many tokens (n_predict 8), --idle-s of
     idle, then one 1-token new task — the new task's launch saves the idle long slot
     (cache_idle_slots ON) or, if it lands on that slot, the f_keep < 0.5 update path does.
  3. FIT least squares MiB = a + b*N for total, target-only (total - draft) and draft, and for
     the entry-with-checkpoints lines; report b*1000 = MiB per 1k tokens, a = fixed (recurrent)
     part, R^2, and the prior (np4/196608, n_max 4: 1631.2 MiB @ 39,875; 3306.0 MiB @ 84,951).

Usage:
  b4g_entry_cost.py --dry-run
  b4g_entry_cost.py --i-own-the-window [--trigger auto|always|never] [--since-report PATH]
  b4g_entry_cost.py --parse-only            (no requests at all; just the fit over the log)
Starts, stops and reloads nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_gpublock as L  # noqa: E402

PRIOR = [(39875, 1631.188, 156.674), (84951, 3306.0, 333.8)]


def launch_offset(path: Path, n_ctx_slot: int = 262144) -> tuple[int | None, str | None]:
    """Byte offset of the LAST launch line with this slot size (scans the whole log once)."""
    off, last, last_line = 0, None, None
    with path.open("rb") as fh:
        for raw in fh:
            if b"load_model: initializing" in raw:
                m = L.RE_LAUNCH.search(raw.decode(errors="replace"))
                if m and int(m.group(2)) == n_ctx_slot:
                    last, last_line = off, raw.decode(errors="replace").strip()
            off += len(raw)
    return last, last_line


def fit(points: list[tuple[float, float]]) -> dict | None:
    pts = sorted(set(points))
    if len({x for x, _ in pts}) < 2:
        return {"n": len(pts), "points": pts, "fit": None}
    n = len(pts)
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    b = sum((x - mx) * (y - my) for x, y in pts) / sxx
    a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in pts)
    ss_tot = sum((y - my) ** 2 for _, y in pts)
    return {"n": n, "mib_per_1k_tokens": round(b * 1000, 3), "kib_per_token": round(b * 1024, 2),
            "fixed_mib": round(a, 1), "r2": round(1 - ss_res / ss_tot, 5) if ss_tot else None,
            "points": [(int(x), round(y, 1)) for x, y in pts]}


def parse(lines: list[str]) -> dict:
    saves, entries, ckpts = [], {}, []
    for ln in lines:
        m = L.RE_SAVE.search(ln)
        if m:
            saves.append((int(m.group(1)), float(m.group(2)), float(m.group(3))))
        m = L.RE_ENTRY.search(ln)
        if m:
            entries[(m.group(1), int(m.group(2)))] = (int(m.group(2)), int(m.group(3)), float(m.group(4)))
        m = L.RE_CKPT.search(ln)
        if m:
            ckpts.append((int(m.group(5)), float(m.group(6))))
    return {"saves": saves, "entries": list(entries.values()), "checkpoints": ckpts,
            "events": L.prompt_cache_events(lines)}


def summarize(p: dict) -> dict:
    s = p["saves"]
    return {
        "save_total": fit([(n, t) for n, t, _ in s]),
        "save_target_only": fit([(n, t - d) for n, t, d in s]),
        "save_draft": fit([(n, d) for n, _, d in s]),
        "entry_with_checkpoints": fit([(n, mib) for n, _, mib in p["entries"]]),
        "checkpoint_size": fit([(n, mib) for n, mib in p["checkpoints"]]),
        "checkpoints_per_entry": sorted({c for _, c, _ in p["entries"]}),
        "events": p["events"],
        "prior_total": fit([(n, t) for n, t, _ in PRIOR]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--parse-only", action="store_true")
    ap.add_argument("--i-own-the-window", action="store_true")
    ap.add_argument("--base", default="http://127.0.0.1:8083")
    ap.add_argument("--log", default=str(L.LOG_8083))
    ap.add_argument("--since-offset", type=int)
    ap.add_argument("--since-report", help="a q38_t7 report.json: start at its log_offset_start")
    ap.add_argument("--trigger", choices=("auto", "always", "never"), default="auto")
    ap.add_argument("--sizes", default="8000,24000,48000,72000")
    ap.add_argument("--min-points", type=int, default=3)
    ap.add_argument("--idle-s", type=float, default=5.0)
    args = ap.parse_args()
    log_path = Path(args.log)
    sizes = [int(s) for s in args.sizes.split(",")]

    def start_offset() -> tuple[int, str]:
        if args.since_offset is not None:
            return args.since_offset, "--since-offset"
        if args.since_report:
            return int(json.loads(Path(args.since_report).read_text())["log_offset_start"]), args.since_report
        off, line = launch_offset(log_path)
        if off is None:
            raise SystemExit("no n_ctx_slot = 262144 launch line in the log; pass --since-offset")
        return off, f"current launch: {line[:120]}"

    if args.dry_run or args.parse_only:
        problems: list[str] = []
        files = [L.check_file(log_path, "server log", problems)]
        off, why = start_offset()
        p = parse(L.LogWindow(log_path, off).lines())
        sm = summarize(p)
        lens = sorted({n for n, _, _ in p["saves"] if n >= 4000})
        need = args.trigger == "always" or (args.trigger == "auto" and len(lens) < args.min_points)
        rows = [f"window from byte {off} ({why}) to {log_path.stat().st_size}",
                f"prompt_save lines {len(p['saves'])} (lengths >= 4k: {lens}); entry lines {len(p['entries'])}; "
                f"checkpoint lines {len(p['checkpoints'])}; events {p['events']}",
                f"fit now: total {sm['save_total']}", f"prior (np4/196608, n_max 4): {sm['prior_total']}"]
        if args.parse_only:
            print(json.dumps(sm, indent=1, default=str))
            return 0
        trig = [f"trigger mode {args.trigger}: {'WOULD TRIGGER' if need else 'no trigger needed'} (today's window; "
                "re-evaluated after T7/KVU-16b have run)",
                f"sizes {sizes}: per size 1 x /completion (n_predict 8, distinct nonce) + {args.idle_s:.0f} s idle + 1 x 1-token task",
                f"prefill ~{round(sum(sizes) / 450 / 60, 1)} min at ~450 tok/s"]
        return L.print_plan("b4g_entry_cost.py (UFH14-B4g)", [
            ("inputs", files), ("current log window (read-only parse, done now)", rows), ("trigger", trig),
            ("estimate", [f"parse < 1 min; trigger (if needed) ~{round(sum(sizes) / 450 / 60 + len(sizes) * 0.3, 1)} min"]),
            ("outputs", [f"{L.RESULTS}/b4g/<ts>/report.json, report.md (MiB per 1k tokens, fixed MiB, R^2)"]),
        ], problems)

    L.require_owner(args, "trigger mode sends inference to :8083")
    od = L.out_dir("b4g")
    off, why = start_offset()
    p = parse(L.LogWindow(log_path, off).lines())
    lens = sorted({n for n, _, _ in p["saves"] if n >= 4000})
    triggered = []
    if args.trigger == "always" or (args.trigger == "auto" and len(lens) < args.min_points):
        for k, size in enumerate(sizes):
            txt, n, _ = L.fit_prompt(args.base, size, L.nonce(f"b4g {size}"), start=k)
            st, resp = L.http_json(f"{args.base}/completion", {"prompt": txt, "n_predict": 8}, timeout=1800)
            time.sleep(args.idle_s)
            st2, _ = L.http_json(f"{args.base}/completion", {"prompt": L.nonce("b4g new-task") + "Say OK.",
                                                              "n_predict": 1}, timeout=120)
            triggered.append({"size": size, "tokens": n, "http": st, "http_newtask": st2,
                              **L.timing_summary((resp or {}).get("timings"))})
            print(json.dumps(triggered[-1]), flush=True)
        time.sleep(2)
        p = parse(L.LogWindow(log_path, off).lines())
    sm = summarize(p)
    rep = {"schema": "epyc.gpublock.b4g.v1", "at": L.now_iso(), "log": str(log_path), "offset": off, "why": why,
           "log_offset_end": log_path.stat().st_size, "triggered": triggered, **sm}
    L.write_json(od / "report.json", rep)
    f = sm["save_total"] or {}
    md = [f"# UFH14-B4g — 27B DFlash2 prompt-cache entry cost, current shape ({rep['at']})", "",
          f"- window: {L.LOG_8083.name} bytes {off}-{rep['log_offset_end']} ({why})",
          f"- prompt_save fit (target+draft): **{f.get('mib_per_1k_tokens')} MiB per 1k tokens**, fixed {f.get('fixed_mib')} MiB, "
          f"R^2 {f.get('r2')}, n={f.get('n')}",
          f"- target-only {sm['save_target_only'].get('mib_per_1k_tokens') if sm['save_target_only'] else None} MiB/1k; "
          f"draft {sm['save_draft'].get('mib_per_1k_tokens') if sm['save_draft'] else None} MiB/1k",
          f"- entry incl. checkpoints: {sm['entry_with_checkpoints']}",
          f"- checkpoint size vs n_tokens: {sm['checkpoint_size']}",
          f"- prior (np4/196608, n_max 4): {sm['prior_total'].get('mib_per_1k_tokens')} MiB/1k, fixed {sm['prior_total'].get('fixed_mib')} MiB",
          f"- events: {sm['events']}", f"- points: {f.get('points')}"]
    (od / "report.md").write_text("\n".join(md) + "\n")
    print("\n".join(md), flush=True)
    return 0 if f.get("mib_per_1k_tokens") is not None else 1


if __name__ == "__main__":
    sys.exit(main())

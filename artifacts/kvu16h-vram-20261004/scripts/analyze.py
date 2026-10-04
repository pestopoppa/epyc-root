#!/usr/bin/env python3
"""KVU-16h analysis: per-phase VRAM table + attribution of the growth to a NAMED allocator -> summary.md/.json.

Inputs per arm dir (written by kvu16h_run.py): vram.jsonl (1 Hz KFD per pid + card), smi.jsonl (rocm-smi),
marks.jsonl (phase boundaries), server.log (epoch-prefixed -lv 4 lines), shim.log (hipMalloc/hipFree with caller
frames; optional), residency.json (/proc/<pid>/maps libs), requests.jsonl, server.pid.

Evidence and what each one can decide:
  * KFD per-process VRAM (1 Hz): the growth itself, per phase (delta at the end of each phase's 60 s idle).
  * shim (LD_PRELOAD hipMalloc interposer): every PUBLIC device allocation with its call chain -> class:
      pool_leg/<route>   ggml_cuda_pool_leg::alloc (never frees); route from the frames: cublas_f16 (Q8_0 ne11>128
                         -> hipBLAS with F16 dequant of the weight + F16 src1/dst), fattn, mmq, mmvq, other
      compute            ggml backend buffer from sched_reserve / graph_reserve / gallocr (compute-buffer realloc)
      kv / model / state backend buffers for the KV/RS cache, weights, state save/restore
      rocblas / hipblaslt / hipblas   allocations made inside those libraries (handle device memory, workspaces)
      other              anything else (top call chains listed)
    ctx = draft if any frame mentions speculative/dflash/draft, else target (heuristic; chains are listed)
  * residual = KFD delta - shim net delta: memory the HIP runtime allocates internally (hipGraph exec /
    instantiation, code objects incl. lazily loaded Tensile kernels, kernarg pools). Not a public hipMalloc.
  * -lv 4 log: sched_reserve "compute buffer size" lines (re-reserves), the exit memory breakdown (target ctx only;
    unaccounted = pool + drafter + rocBLAS + graphs + runtime), the ~llama_context WARN "compute buffer size of X
    does not match expectation of Y" (silent gallocr growth; survives Release), idle-slot save / restore lines.
    Pool growth itself is NOT logged by this build (DEBUG_CUDA_MALLOC off; gallocr realloc logs are #ifndef NDEBUG).

Usage: analyze.py <run_dir> [--arm armA]        writes <run_dir>/summary.md + summary.json
       analyze.py --fixture                     CPU-only dry run on old logs (see build_fixture)
"""
from __future__ import annotations

import argparse
import bisect
import collections
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GIB = 1024 ** 3
MIB = 1024 ** 2
LIB_DIRS = [Path("/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin"), Path("/opt/rocm/lib")]

LOG_PATS = {
    "reserve": re.compile(r"sched_reserve: reserving|graph_reserve|reserve took"),
    "compute_buffer": re.compile(r"compute buffer size"),
    "pool": re.compile(r"\bpool\b|pool\[", re.I),
    "realloc": re.compile(r"realloc", re.I),
    "alloc_fail": re.compile(r"failed to allocate|out of memory|alloc of .* failed|hipErrorOutOfMemory", re.I),
    "expect_mismatch": re.compile(r"does not match expectation"),
    "breakdown": re.compile(r"memory breakdown|common_memory_breakdown_print"),
    "idle_save": re.compile(r"saving idle slot"),
    "clear_prompt": re.compile(r"clearing prompt with [1-9]"),
    "cache_restore": re.compile(r"found better prompt|restored context|loading prompt from cache|failed to restore"),
    "checkpoint": re.compile(r"context checkpoint"),
    "graphs": re.compile(r"cuda graph|hip graph|graph capture", re.I),
}
RE_COMPUTE = re.compile(r"sched_reserve:\s+(\S+) compute buffer size =\s+([\d.]+) MiB")
RE_BD = re.compile(r"\|\s+- (.+?)\s+\|\s*(-?\d+)\s*=\s*(-?\d+)\s*\+\s*\(\s*(-?\d+)\s*=\s*(-?\d+)\s*\+\s*(-?\d+)"
                   r"\s*\+\s*(-?\d+)\s*\)\s*\+\s*(-?\d+)\s*\|")
RE_MISMATCH = re.compile(r"(\S+) compute buffer size of\s+([\d.]+) MiB, does not match expectation of\s+([\d.]+) MiB")
DRAFT_RE = re.compile(r"specul|dflash|draft", re.I)


def jl(p: Path) -> list[dict]:
    out = []
    try:
        for ln in p.open():
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def gib(b) -> str:
    return "-" if b is None else f"{b / GIB:.3f}"


def dgib(b) -> str:
    return "-" if b is None else f"{b / GIB:+.3f}"


# ---------------------------------------------------------------- vram
class Vram:
    def __init__(self, arm: Path, pid: int | None) -> None:
        self.rows = []
        self.aborts: list[dict] = []
        inline_marks = []
        for r in jl(arm / "vram.jsonl"):
            if "mark" in r:
                inline_marks.append(r)
                continue
            if "abort" in r:
                self.aborts.append(r)
                continue
            if "t" not in r:
                continue
            pids = r.get("pids") or {}
            own = r.get("own_vram_b")
            if own is None and pid is not None:
                own = (pids.get(str(pid)) or {}).get("vram_b")
            card = r.get("card_used_b", r.get("used_b"))
            self.rows.append((r["t"], own, card))
        self.rows.sort(key=lambda r: r[0])
        self.ts = [r[0] for r in self.rows]
        self.inline_marks = inline_marks

    def at(self, t: float, col: int = 1):
        i = bisect.bisect_right(self.ts, t) - 1
        while i >= 0 and self.rows[i][col] is None:
            i -= 1
        return self.rows[i][col] if i >= 0 else None

    def peak(self, t0: float, t1: float, col: int = 1):
        v = [r[col] for r in self.rows if t0 <= r[0] <= t1 and r[col] is not None]
        return max(v) if v else None


def smi_at(arm: Path, t: float):
    best = None
    for r in jl(arm / "smi.jsonl"):
        if r.get("t1", 0) <= t and r.get("cards"):
            best = r
    if not best:
        return None
    return sum(c["used_b"] for c in best["cards"].values())


# ---------------------------------------------------------------- phases
def phases(arm: Path, vr: Vram) -> list[dict]:
    marks = jl(arm / "marks.jsonl")
    out: dict[str, dict] = {}
    order = []
    for m in marks:
        ph, ev = m.get("phase"), m.get("event")
        if ph not in out:
            out[ph] = {"phase": ph}
            order.append(ph)
        out[ph][ev] = m["t"]
        out[ph].setdefault("marks", []).append(m)
    res = []
    for ph in order:
        d = out[ph]
        if ph == "load":
            d["t0"] = d.get("launched", d.get("pre_launch"))
            d["t1"] = d.get("healthy", d["t0"])
            d["t2"] = d.get("idle_end", d["t1"])
        elif ph == "teardown":
            d["t0"] = d.get("begin")
            d["t1"] = d["t2"] = d.get("end", d["t0"])
        elif "begin" in d:
            d["t0"], d["t1"] = d["begin"], d.get("traffic_end", d["begin"])
            d["t2"] = d.get("idle_end", d["t1"])
        else:
            d["skipped"] = True
        res.append(d)
    return res


# ---------------------------------------------------------------- server log
def server_log(arm: Path) -> list[tuple[float, str]]:
    out, last_t = [], 0.0
    try:
        for raw in (arm / "server.log").open("rb"):
            ln = raw.decode(errors="replace").rstrip("\n")
            m = re.match(r"^(\d{9,}\.\d+) (.*)$", ln)
            if m:
                last_t = float(m.group(1))
                out.append((last_t, m.group(2)))
            else:
                out.append((last_t, ln))
    except OSError:
        pass
    return out


def log_window(lines, t0, t1) -> dict:
    sel = [(t, l) for t, l in lines if t0 <= t <= t1]
    counts = {k: sum(1 for _, l in sel if p.search(l)) for k, p in LOG_PATS.items()}
    samples = {k: [l[:220] for _, l in sel if p.search(l)][:4] for k, p in LOG_PATS.items() if counts[k]}
    computes = [(round(t, 1), m.group(1), float(m.group(2))) for t, l in sel for m in [RE_COMPUTE.search(l)] if m]
    return {"counts": {k: v for k, v in counts.items() if v}, "samples": samples, "compute_buffers": computes}


def breakdowns(lines) -> list[dict]:
    out = []
    for t, l in lines:
        m = RE_BD.search(l)
        if m:
            k = ["total", "free", "self", "model", "context", "compute", "unaccounted"]
            out.append({"t": t, "device": m.group(1).strip(), **{a: int(m.group(i + 2)) for i, a in enumerate(k)}})
    return out


# ---------------------------------------------------------------- shim
def lib_paths(arm: Path) -> dict[str, Path]:
    res: dict[str, Path] = {}
    try:
        for p in json.loads((arm / "residency.json").read_text())["maps"]["all_libs"]:
            res[Path(p).name] = Path(p)
    except Exception:  # noqa: BLE001
        pass
    for d in LIB_DIRS:
        if d.exists():
            for p in d.iterdir():
                res.setdefault(p.name, p)
    return res


def resolve_frames(events: list[dict], libs: dict[str, Path]) -> dict[tuple[str, int], str]:
    """addr2line -f -C on (lib, return_address - 1) for every frame, batched per library (.symtab has the
    static/hidden functions that dladdr cannot name)."""
    want: dict[str, set[int]] = collections.defaultdict(set)
    for e in events:
        for lib, off, _ in e["frames"]:
            want[lib].add(off)
    out: dict[tuple[str, int], str] = {}
    if not shutil.which("addr2line"):
        return out
    for lib, offs in want.items():
        path = libs.get(lib)
        if not path or not path.exists():
            continue
        offs_l = sorted(offs)
        for i in range(0, len(offs_l), 2000):
            chunk = offs_l[i:i + 2000]
            try:
                r = subprocess.run(["addr2line", "-f", "-C", "-e", str(path)] + [hex(max(0, o - 1)) for o in chunk],
                                   capture_output=True, text=True, timeout=300)
            except Exception:  # noqa: BLE001
                continue
            ls = r.stdout.splitlines()
            for j, o in enumerate(chunk):
                if 2 * j < len(ls) and ls[2 * j] != "??":
                    out[(lib, o)] = ls[2 * j]
    return out


def parse_shim(arm: Path) -> list[dict]:
    ev = []
    try:
        fh = (arm / "shim.log").open()
    except OSError:
        return ev
    for ln in fh:
        if not ln or ln[0] not in "AF":
            continue
        head, _, tail = ln.rstrip("\n").partition(" |")
        p = head.split()
        if len(p) < 7:
            continue
        frames = []
        for tok in tail.split():
            m = re.match(r"^([^+]+)\+0x([0-9a-f]+)(?::(.*))?$", tok)
            if m:
                frames.append((m.group(1), int(m.group(2), 16), m.group(3) or ""))
        ev.append({"k": p[0], "t": float(p[1]), "tid": p[2], "fn": p[3], "size": int(p[4]), "ptr": p[5],
                   "rc": int(p[6]), "frames": frames[1:]})  # frames[0] is the shim's own entry point
    return ev


def classify(frames: list[tuple[str, int, str]], names: dict) -> tuple[str, str, str]:
    syms = [names.get((lib, off)) or sym for lib, off, sym in frames]
    libs = [lib for lib, _, _ in frames]
    s = " ".join(syms)
    ctx = "draft" if DRAFT_RE.search(s) else "target"
    if any(l.startswith("librocblas") for l in libs[:12]):
        cls = "rocblas"
    elif any(l.startswith("libhipblaslt") for l in libs[:12]):
        cls = "hipblaslt"
    elif any(l.startswith("libhipblas") for l in libs[:6]):
        cls = "hipblas"
    elif "ggml_cuda_pool_leg" in s:
        route = ("cublas_f16" if "mul_mat_cublas" in s else "fattn" if re.search(r"flash_attn|fattn", s) else
                 "mmq" if "mmq" in s else "mmvq" if "mmvq" in s else "mmv" if "mul_mat_vec" in s else "other")
        cls = f"pool_leg/{route}"
    elif "ggml_cuda_pool_vmm" in s:
        cls = "pool_vmm"
    elif "alloc_buffer" in s or "ggml_backend_alloc" in s:
        cls = ("compute" if re.search(r"sched_reserve|graph_reserve|gallocr|sched_alloc", s) else
               "kv" if re.search(r"kv_cache|memory_recurrent|memory_hybrid", s) else
               "model" if re.search(r"load_tensors|model_loader|llama_model", s) else
               "state" if re.search(r"state_seq|state_set|state_get", s) else "buffer_other")
    else:
        cls = "other"
    chain = " < ".join((x.split("(")[0][:70] if x else f"{lib}+{off:#x}") for x, (lib, off, _) in zip(syms[:8], frames[:8]))
    return cls, ctx, chain


class ShimLedger:
    def __init__(self, arm: Path) -> None:
        self.events = parse_shim(arm)
        self.present = (arm / "shim.log").exists()
        names = resolve_frames([e for e in self.events if e["k"] == "A"], lib_paths(arm)) if self.events else {}
        self.live: dict[str, tuple[int, str]] = {}
        self.timeline: list[tuple[float, str, int]] = []   # (t, class|ctx, signed bytes)
        self.chains: collections.Counter = collections.Counter()
        self.chain_cls: dict[str, str] = {}
        for e in self.events:
            if e["rc"] != 0:
                continue
            if e["k"] == "A":
                cls, ctx, chain = classify(e["frames"], names)
                key = f"{cls}|{ctx}"
                self.live[e["ptr"]] = (e["size"], key)
                self.timeline.append((e["t"], key, e["size"]))
                self.chains[chain] += e["size"]
                self.chain_cls[chain] = key
            elif e["ptr"] in self.live:
                size, key = self.live.pop(e["ptr"])
                self.timeline.append((e["t"], key, -size))

    def net(self, t0: float, t1: float) -> dict[str, int]:
        c: collections.Counter = collections.Counter()
        for t, k, b in self.timeline:
            if t0 < t <= t1:
                c[k] += b
        return {k: v for k, v in c.items() if v}

    def counts(self, t0: float, t1: float) -> int:
        return sum(1 for t, _, b in self.timeline if t0 < t <= t1 and b > 0)


# ---------------------------------------------------------------- analysis
def analyze_arm(arm: Path) -> dict:
    pid = None
    try:
        pid = int((arm / "server.pid").read_text().strip())
    except (OSError, ValueError):
        pass
    vr = Vram(arm, pid)
    lines = server_log(arm)
    shim = ShimLedger(arm)
    phs = phases(arm, vr)
    run = [p for p in phs if not p.get("skipped") and p.get("t0") is not None]
    rows = []
    prev_end = prev_t2 = None
    base_t = next((p["t2"] for p in run if p["phase"] == "load"), None)
    for p in run:
        own_end = vr.at(p["t2"])
        own_start = vr.at(p["t0"]) if p["phase"] != "load" else 0
        ref = prev_end if prev_end is not None else own_start
        d = (own_end - ref) if (own_end is not None and ref is not None) else None
        lo = p["t0"] if prev_end is None else prev_t2
        net = shim.net(lo, p["t2"]) if shim.events else {}
        shim_tot = sum(net.values()) if net else None
        rows.append({
            "phase": p["phase"], "t0": p["t0"], "t2": p["t2"], "dur_s": round(p["t2"] - p["t0"], 1),
            "own_end_b": own_end, "delta_b": d, "peak_b": vr.peak(p["t0"], p["t2"]),
            "card_end_b": vr.at(p["t2"], 2), "smi_end_b": smi_at(arm, p["t2"]),
            "shim_net": net, "shim_net_b": shim_tot, "shim_allocs": shim.counts(lo, p["t2"]) if shim.events else None,
            "residual_b": (d - shim_tot) if (d is not None and shim_tot is not None and p["phase"] != "load") else None,
            "log": log_window(lines, lo, p["t2"]),
            "marks": {m["event"]: {k: v for k, v in m.items() if k not in ("t", "at", "phase", "event")}
                      for m in p.get("marks", [])},
        })
        prev_end, prev_t2 = own_end, p["t2"]
    skipped = [p["phase"] for p in phs if p.get("skipped")]
    serving = [r for r in rows if r["phase"] not in ("load", "teardown")]
    growth = None
    t_last = serving[-1]["t2"] if serving else None
    if base_t is not None and t_last is not None and vr.at(base_t) is not None and vr.at(t_last) is not None:
        growth = vr.at(t_last) - vr.at(base_t)
    peak_serving = vr.peak(base_t, t_last) if (base_t and t_last) else None
    by_class = shim.net(base_t, t_last) if (shim.events and base_t and t_last) else {}
    shim_growth = sum(by_class.values()) if by_class else (0 if shim.events else None)
    residual = (growth - shim_growth) if (growth is not None and shim_growth is not None) else None
    bds = breakdowns(lines)
    td = next((p for p in phs if p["phase"] == "teardown"), {})
    exit_bd = [b for b in bds if td.get("t0") and b["t"] >= td["t0"]]
    load_bd = [b for b in bds if not exit_bd or b["t"] < exit_bd[0]["t"]]
    mism = [{"t": t, "buf": m.group(1), "actual_mib": float(m.group(2)), "expected_mib": float(m.group(3))}
            for t, l in lines for m in [RE_MISMATCH.search(l)] if m]
    loadc = [(round(t, 1), b, mib) for t, l in lines for m in [RE_COMPUTE.search(l)] if m
             for b, mib in [(m.group(1), float(m.group(2)))] if base_t is None or t <= base_t]
    return {"arm": arm.name, "pid": pid, "vram_aborts": vr.aborts, "rows": rows, "skipped": skipped, "growth_b": growth,
            "peak_serving_b": peak_serving, "own_after_load_b": vr.at(base_t) if base_t else None,
            "shim_present": shim.present, "shim_events": len(shim.events), "by_class_b": by_class,
            "shim_growth_b": shim_growth, "residual_b": residual,
            "top_chains": [{"chain": c, "class": shim.chain_cls[c], "alloc_b": b} for c, b in shim.chains.most_common(14)],
            "breakdown_load": load_bd[-2:], "breakdown_exit": exit_bd, "compute_mismatch": mism,
            "compute_reserves_at_load": loadc,
            "requests": jl(arm / "requests.jsonl"), "arm_result": (json.loads((arm / "arm_result.json").read_text())
                                                                 if (arm / "arm_result.json").exists() else {})}


def share_groups(r: dict) -> dict[str, int]:
    """Collapse classes into the brief's candidates (+ HIP runtime residual)."""
    g: collections.Counter = collections.Counter()
    for key, b in (r.get("by_class_b") or {}).items():
        cls, ctx = key.split("|")
        if cls.startswith("pool_leg"):
            g[f"legacy pool ({ctx})"] += b
        elif cls == "compute":
            g[f"compute-buffer realloc ({ctx})"] += b
        elif cls in ("rocblas", "hipblaslt", "hipblas"):
            g[f"rocBLAS/hipBLAS(Lt) ({ctx})"] += b
        elif cls == "state":
            g["slot save/restore (state buffers)"] += b
        else:
            g[f"{cls} ({ctx})"] += b
    if r.get("residual_b") is not None:
        g["HIP runtime internal (residual: graphs, code objects, kernarg)"] += r["residual_b"]
    return dict(g)


def verdict(r: dict) -> dict:
    G = r.get("growth_b")
    out: dict = {"growth_gib": None if G is None else round(G / GIB, 3)}
    if G is None:
        out["text"] = "no VRAM series: nothing to attribute"
        return out
    if G < 0.5 * GIB:
        out["text"] = f"growth {G / GIB:.2f} GiB < 0.5 GiB: did NOT reproduce in this run (shapes insufficient or fixed)"
        out["named"] = None
        return out
    groups = share_groups(r)
    if groups:
        top = max(groups.items(), key=lambda kv: kv[1])
        out["groups_gib"] = {k: round(v / GIB, 3) for k, v in sorted(groups.items(), key=lambda kv: -kv[1])}
        share = top[1] / G
        out["named"] = top[0]
        out["share"] = round(share, 3)
        out["text"] = (f"{'ATTRIBUTED' if share >= 0.6 else 'MIXED (largest share)'}: {top[0]} = "
                       f"{top[1] / GIB:.2f} of {G / GIB:.2f} GiB ({share:.0%})")
    else:
        bd = r.get("breakdown_exit") or []
        comp0 = max((mib for _, b, mib in r.get("compute_reserves_at_load", []) if b.startswith("ROCm")), default=None)
        txt = "NO SHIM: only the exit breakdown splits the growth"
        if bd and comp0 is not None:
            dev = next((b for b in bd if "ROCm" in b["device"]), bd[0])
            txt += (f": target compute at exit {dev['compute']} MiB vs largest load reserve {comp0:.0f} MiB; "
                    f"unaccounted {dev['unaccounted']} MiB = pool + drafter + rocBLAS + graphs (not separable)")
        out["text"] = txt
        out["named"] = None
    mix = {x["phase"]: x["delta_b"] for x in r["rows"]}
    if mix.get("mix1") is not None and mix.get("mix2") is not None:
        out["plateau"] = ("PLATEAU" if mix["mix2"] < 0.25 * GIB or mix["mix2"] < 0.2 * max(mix["mix1"], 1)
                          else "STILL GROWING") + f" (mix1 {mix['mix1'] / GIB:+.2f}, mix2 {mix['mix2'] / GIB:+.2f} GiB)"
    if mix.get("longidle") is not None:
        out["idle_release"] = f"long idle delta {mix['longidle'] / GIB:+.3f} GiB"
    return out


def decide_arm_b(r: dict) -> tuple[str, str]:
    v = verdict(r)
    G = r.get("growth_b") or 0
    if G < 0.5 * GIB:
        return "off", v.get("text", "no growth")
    named = v.get("named") or ""
    if named.startswith("HIP runtime internal"):
        return "nographs", f"{v['text']} -> test GGML_CUDA_DISABLE_GRAPHS=1"
    return "ub512", f"{v.get('text')} -> test -b 512 -ub 512 (bounds per-ubatch pool temps + compute; KVU-16f)"


# ---------------------------------------------------------------- report
def fmt_classes(net: dict) -> str:
    if not net:
        return "-"
    items = sorted(net.items(), key=lambda kv: -abs(kv[1]))[:3]
    return "; ".join(f"{k} {v / GIB:+.2f}" for k, v in items)


def candidates_md(r: dict) -> list[str]:
    G = r.get("growth_b") or 0
    groups = share_groups(r)
    rows = {x["phase"]: x for x in r["rows"]}

    def g(prefix):
        return sum(v for k, v in groups.items() if k.startswith(prefix))

    def st(b):
        if G < 0.5 * GIB:
            return "n/a (growth < 0.5 GiB: not reproduced)"
        if not r.get("shim_events"):
            return "undetermined (no shim)"
        s = b / G
        return "PRIMARY" if s >= 0.6 else "contributes" if s >= 0.1 else "ruled out (<10%)"
    ic = rows.get("idlecache", {})
    out = ["| candidate | evidence | GiB | verdict |", "|---|---|---|---|",
           f"| ggml-cuda legacy pool (NO_VMM: GGML_HIP_NO_VMM=ON, no pool_vmm symbols) | shim ggml_cuda_pool_leg::alloc net | "
           f"{g('legacy pool') / GIB:.2f} | {st(g('legacy pool'))} |",
           f"| compute-buffer realloc beyond the reserve | shim sched/gallocr buffers + mismatch WARN x{len(r.get('compute_mismatch') or [])} | "
           f"{g('compute-buffer') / GIB:.2f} | {st(g('compute-buffer'))} |",
           f"| rocBLAS / hipBLASLt workspaces | shim allocs inside librocblas/libhipblas* | {g('rocBLAS') / GIB:.2f} | {st(g('rocBLAS'))} |",
           f"| DFlash2 drafter buffers | shim classes with ctx=draft | "
           f"{sum(v for k, v in groups.items() if '(draft)' in k) / GIB:.2f} | {st(sum(v for k, v in groups.items() if '(draft)' in k))} |",
           f"| slot save/restore (--cache-ram, idle-slot caching) | idlecache phase KFD delta {dgib(ic.get('delta_b'))}; "
           f"idle saves {ic.get('log', {}).get('counts', {}).get('idle_save', 0)}, restores "
           f"{ic.get('log', {}).get('counts', {}).get('cache_restore', 0)} | {(ic.get('delta_b') or 0) / GIB:.2f} | "
           f"{'ruled out' if ic and abs(ic.get('delta_b') or 0) < 0.1 * GIB else 'CHECK' if ic else 'not run'} |",
           f"| HIP runtime internal (HIP graphs: GGML_HIP_GRAPHS=ON; code objects) | residual = KFD - shim | "
           f"{(r.get('residual_b') or 0) / GIB:.2f} | {st(r.get('residual_b') or 0)} |"]
    return out


def arm_md(r: dict) -> list[str]:
    v = verdict(r)
    md = [f"## {r['arm']}", "",
          f"- server pid {r['pid']}; own KFD after load {gib(r['own_after_load_b'])} GiB; serving peak "
          f"{gib(r['peak_serving_b'])} GiB; **growth {gib(r['growth_b'])} GiB**; shim {'ON' if r['shim_present'] else 'OFF'} "
          f"({r['shim_events']} events)",
          f"- **verdict: {v.get('text')}**"]
    for k in ("plateau", "idle_release"):
        if v.get(k):
            md.append(f"- {k}: {v[k]}")
    ar = r.get("arm_result") or {}
    if ar.get("aborted") or r.get("vram_aborts"):
        md.append(f"- **ABORTED (VRAM ceiling): {ar.get('aborted') or r['vram_aborts'][0].get('abort')}**")
    if ar.get("error"):
        md.append(f"- error: {ar['error']}")
    if r.get("skipped"):
        md.append(f"- skipped (budget): {', '.join(r['skipped'])}")
    md += ["", "| phase | dur s | KFD end GiB | delta GiB | peak GiB | card end | rocm-smi end | shim net GiB (top classes) | residual GiB | log: reserve / compute-buf / pool / mismatch / idle-save / restore |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for x in r["rows"]:
        c = x["log"]["counts"]
        md.append(f"| {x['phase']} | {x['dur_s']} | {gib(x['own_end_b'])} | {dgib(x['delta_b'])} | {gib(x['peak_b'])} | "
                  f"{gib(x['card_end_b'])} | {gib(x['smi_end_b'])} | {fmt_classes(x['shim_net'])} | {dgib(x['residual_b'])} | "
                  f"{c.get('reserve', 0)} / {c.get('compute_buffer', 0)} / {c.get('pool', 0)} / {c.get('expect_mismatch', 0)} / "
                  f"{c.get('idle_save', 0)} / {c.get('cache_restore', 0)} |")
    md += ["", "### Candidates", ""] + candidates_md(r)
    if v.get("groups_gib"):
        md += ["", "### Growth by allocator (load idle end -> last serving phase)", "", "| allocator | GiB |", "|---|---|"]
        md += [f"| {k} | {val:+.3f} |" for k, val in v["groups_gib"].items()]
    if r.get("top_chains"):
        md += ["", "### Top allocation call chains (shim, bytes allocated over the whole arm)", "",
               "| class | GiB | chain (innermost first) |", "|---|---|---|"]
        md += [f"| {c['class']} | {c['alloc_b'] / GIB:.2f} | `{c['chain'][:300]}` |" for c in r["top_chains"]]
    md += ["", "### Compute buffers / breakdown", ""]
    md += [f"- load reserve: {b} {mib:.2f} MiB (t {t})" for t, b, mib in r.get("compute_reserves_at_load", [])][:12]
    for b in r.get("breakdown_exit") or []:
        md.append(f"- EXIT breakdown {b['device']}: total {b['total']} = free {b['free']} + (self {b['self']} = model "
                  f"{b['model']} + context {b['context']} + compute {b['compute']}) + unaccounted {b['unaccounted']} MiB")
    if not r.get("breakdown_exit"):
        md.append("- no exit breakdown (needs graceful SIGTERM and -lv >= 4)")
    for m in r.get("compute_mismatch") or []:
        md.append(f"- WARN compute mismatch {m['buf']}: actual {m['actual_mib']} MiB vs expected {m['expected_mib']} MiB")
    md += ["", "### Log lines per phase (first matches)", ""]
    for x in r["rows"]:
        if x["log"]["samples"] or x["log"]["compute_buffers"]:
            md.append(f"- **{x['phase']}**: " + "; ".join(f"{k}: `{s[0][-160:]}`" for k, s in x["log"]["samples"].items()))
    return md


def compare_md(a: dict, b: dict) -> list[str]:
    ra = {x["phase"]: x for x in a["rows"]}
    rb = {x["phase"]: x for x in b["rows"]}

    def thru(r, rows):
        s = [x["delta_b"] for x in r["rows"] if x["phase"] not in ("load", "teardown") and x["delta_b"] is not None]
        return sum(s) if s else None
    ga, gb = thru(a, ra), thru(b, rb)
    bounded = gb is not None and ga is not None and gb <= 0.5 * max(ga, 1) and (rb.get("mix2", {}).get("delta_b") or 0) < 0.25 * GIB
    return [f"## Arm comparison: {a['arm']} vs {b['arm']}", "",
            f"- growth after load: {a['arm']} {dgib(ga)} GiB (all phases) vs {b['arm']} {dgib(gb)} GiB (mix1+mix2 only)",
            f"- mix1/mix2 deltas: A {dgib(ra.get('mix1', {}).get('delta_b'))}/{dgib(ra.get('mix2', {}).get('delta_b'))} vs "
            f"B {dgib(rb.get('mix1', {}).get('delta_b'))}/{dgib(rb.get('mix2', {}).get('delta_b'))} GiB",
            f"- **{'BOUNDED by this flag' if bounded else 'NOT shown bounded by this flag'}** (rule: B growth <= 50% of A's and "
            f"B's mix2 delta < 0.25 GiB). Caveat: A's mix phases ran after other shapes had already grown the pool."]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?", type=Path)
    ap.add_argument("--fixture", action="store_true", help="CPU-only dry run on old logs")
    a = ap.parse_args(argv)
    if a.fixture:
        a.run_dir = build_fixture()
    if not a.run_dir:
        ap.error("run_dir required")
    arms = sorted(p for p in a.run_dir.iterdir() if p.is_dir() and p.name.startswith("arm"))
    run = json.loads((a.run_dir / "run.json").read_text()) if (a.run_dir / "run.json").exists() else {}
    res = [analyze_arm(p) for p in arms]
    md = ["# KVU-16h — :8083 VRAM growth attribution", "",
          f"- run `{a.run_dir}`; argv source: {run.get('argv_source', '?')}",
          f"- argv: `{' '.join(run.get('argv', []))}`",
          f"- shim: {run.get('shim')}; -lv {run.get('lv')}; ceiling {run.get('ceiling_gib')} GiB; budget "
          f"{run.get('budget_min')} min; elapsed {run.get('elapsed_min')} min; arm B {run.get('arm_b_decision')}",
          "- question: production :8083 went 51.69 -> 58.88 -> 59.77 GiB while serving (KVU-16b at 310k cells added 0); "
          "the gate is 62 GiB.", ""]
    for r in res:
        md += arm_md(r) + [""]
    a_res = next((r for r in res if r["arm"].startswith("armA")), None)
    for r in res:
        if r["arm"].startswith("armB") and a_res:
            md += compare_md(a_res, r) + [""]
    if a_res:
        v = verdict(a_res)
        md += ["## KVU-16i runtime term (proposal)", "",
               f"- `vram_runtime_growth_gib` for :8083 = serving peak - after-load = "
               f"{gib((a_res['peak_serving_b'] or 0) - (a_res['own_after_load_b'] or 0))} GiB in this run "
               f"(production observed +8.08 from 51.69 to 59.77 and still rising); evidence `{a_res['arm']}/vram.jsonl`",
               f"- attribution: {v.get('text')}", ""]
    md += ["## How the candidates are decided", "",
           "1. Growth G = own-pid KFD at the end of the last serving phase - at the end of the post-load idle.",
           "2. The shim ledger splits G by the call chain of every public hipMalloc/hipFree (net live bytes per class "
           "in the window); residual = G - shim = HIP-runtime-internal memory.",
           "3. The largest group is the named allocator (ATTRIBUTED if >= 60% of G, else MIXED). Pool route "
           "cublas_f16 = the Q8_0 ne11>128 hipBLAS path (MMQ is used only for ne11 <= 128 on CDNA2).",
           "4. Cross-checks: exit breakdown compute column vs the load reserve (gallocr growth); the "
           "~llama_context mismatch WARN; per-phase steps (first occurrence of a larger shape) and the mix2 plateau; "
           "the idlecache phase delta (slot save/restore lives in host RAM by source).",
           "5. Arm B: BOUNDED if its growth <= 50% of arm A's and mix2 adds < 0.25 GiB."]
    (a.run_dir / "summary.md").write_text("\n".join(md) + "\n")
    (a.run_dir / "summary.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if k not in ("requests",)} | {"verdict": verdict(r)} for r in res],
        indent=1, default=str) + "\n")
    print(f"wrote {a.run_dir / 'summary.md'}")
    return 0


# ---------------------------------------------------------------- CPU-only fixture (dry run on old logs)
def build_fixture() -> Path:
    """Fixture from REAL old logs: the gpu-slot-ak -lv 4 server.log (epoch-prefixed, same argv shape, build
    c7f5ac9ad) and its 1 Hz vram.jsonl, with phase marks laid over its time range, plus a SYNTHETIC shim log whose
    frames are real v10 libggml-hip/libllama offsets (so the addr2line resolution runs against the real .symtab).
    It checks parsing and the pipeline end to end; its verdict is about synthetic bytes, not production."""
    src = Path("/mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/20261004T050808Z/kvu_off_b2048")
    run = HERE / "dryrun" / "fixture_run"
    if run.exists():
        shutil.rmtree(run)
    arm = run / "armA"
    arm.mkdir(parents=True)
    shutil.copy(src / "server.log", arm / "server.log")
    shutil.copy(src / "vram.jsonl", arm / "vram.jsonl")
    shutil.copy(src / "server.pid", arm / "server.pid")
    vr = [r for r in jl(arm / "vram.jsonl") if "t" in r and "mark" not in r]
    t0, t_end = vr[0]["t"], vr[-1]["t"]
    span = t_end - t0
    names = ["short", "sweep", "prefill80k", "dec4", "mix1", "mix2", "idlecache", "longidle"]
    marks = [{"t": t0, "phase": "load", "event": "launched"}, {"t": t0 + 4, "phase": "load", "event": "healthy"},
             {"t": t0 + 6, "phase": "load", "event": "idle_end"}]
    step = (span - 10) / (len(names) + 1)
    for i, n in enumerate(names):
        b = t0 + 6 + i * step
        marks += [{"t": b, "phase": n, "event": "begin"}, {"t": b + 0.7 * step, "phase": n, "event": "traffic_end"},
                  {"t": b + step, "phase": n, "event": "idle_end"}]
    td = t0 + 6 + len(names) * step
    marks += [{"t": td, "phase": "teardown", "event": "begin"}, {"t": t_end, "phase": "teardown", "event": "end"}]
    with open(arm / "marks.jsonl", "w") as fh:
        for m in marks:
            fh.write(json.dumps(m) + "\n")
    # synthetic shim log: real v10 offsets (readelf .symtab): ggml_cuda_pool_leg::alloc 0x35774e0 (exported),
    # ggml_cuda_mul_mat_cublas 0x3572b50 (LOCAL), ggml_backend_cuda_buffer_type_alloc_buffer 0x3565b40 (LOCAL),
    # llama_context::graph_reserve 0xfd930 (libllama). +0x40 = a return address inside each function.
    hip, lla = "libggml-hip.so.0", "libllama.so.0"
    pool = f"libhipmalloc_trace.so+0x1844:hipMalloc {hip}+0x3577520:_ZN18ggml_cuda_pool_leg5allocEmPm {hip}+0x3572b90"
    comp = f"libhipmalloc_trace.so+0x1844:hipMalloc {hip}+0x3565b80 {lla}+0xfd970:_ZN13llama_context13graph_reserveEjjjPK22llama_memory_context_ibPm"
    roc = "libhipmalloc_trace.so+0x1844:hipMalloc librocblas.so.4+0x123456"
    lines = ["# kvu16h hipmalloc_trace v1 pid 0 frames 28 (fixture)"]
    ptr = 0x7f0000000000
    for i, n in enumerate(names):
        b = t0 + 6 + i * step + 1
        for j in range(3 if n in ("mix1", "prefill80k") else 1):
            ptr += 0x10000000
            lines.append(f"A {b + j:.6f} 1 hipMalloc {int(0.4 * GIB)} {hex(ptr)} 0 | {pool}")
        if n == "mix1":
            ptr += 0x10000000
            lines.append(f"A {b + 5:.6f} 1 hipMalloc {200 * MIB} {hex(ptr)} 0 | {comp}")
            lines.append(f"F {b + 6:.6f} 1 hipFree 0 {hex(ptr)} 0")
            ptr += 0x10000000
            lines.append(f"A {b + 7:.6f} 1 hipMalloc {64 * MIB} {hex(ptr)} 0 | {roc}")
    (arm / "shim.log").write_text("\n".join(lines) + "\n")
    (arm / "residency.json").write_text(json.dumps({"maps": {"all_libs": [
        "/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/libggml-hip.so.0",
        "/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/libllama.so.0"]}}))
    (run / "run.json").write_text(json.dumps({"argv_source": f"FIXTURE from {src}", "argv": [], "shim": "synthetic",
                                              "lv": 4, "ceiling_gib": 62.5, "budget_min": 60}))
    print(f"fixture: {run} (log + vram from {src}; {len(lines) - 1} synthetic shim events)")
    return run


if __name__ == "__main__":
    raise SystemExit(main())

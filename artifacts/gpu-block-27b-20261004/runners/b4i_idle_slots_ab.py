#!/usr/bin/python3
"""UFH14-B4i — `--cache-idle-slots` (v10 default ON) vs `--no-cache-idle-slots` A/B on a
SCRATCH port with the exact production :8083 argv (agentic-serving-harness-fixes.md UFH14-B4i).

This script NEVER starts or kills a server. It:
  --print-launch   writes and prints the exact launch + kill scripts for each arm
                   (results/b4i/launch_<ARM>.sh, kill_<ARM>.sh). The MAIN SESSION runs them:
                   production argv from logs/server_launches/8083.json with --port 18083 and a
                   scratch --slot-save-path, arm OFF adds --no-cache-idle-slots, the kernel-store
                   binary, LD_LIBRARY_PATH and env as in the live :8083 process environ
                   (LLAMA_SERVER_SLOTS_DEBUG dropped), same numactl/taskset; PID captured to a file.
  (run mode)       drives agent-like traffic to the given port and measures it:
                   3 concurrent multi-turn conversations, each with a distinct ~20k-token context,
                   6 turns, ~1.5k new tokens per turn ("tool output"), 200 generated tokens,
                   pauses between turns staggered so other conversations launch tasks while a
                   conversation is idle (the moment cache_idle_slots saves-and-clears its slot).
  --compare A B..  prints the A/B table from report.json files.

Per turn: TTFT, timings prompt_n / cache_n / prompt_ms, decode tok/s, draft acceptance, and the
tokens the turn SHOULD have found cached (the previous turn's prompt + generation). Per arm:
hit_tok = sum(cache_n)/sum(cache_n+prompt_n) (HIGHER better), missed_prefill_share (LOWER better;
same definitions as orchestrator scripts/analysis/prefix_cache_report.py, but with the exact
known shared prefix instead of fingerprints, because scratch traffic writes no serving records),
turn>=2 TTFT, prompt-cache restores / restore failures / evictions from the scratch server log,
and KFD VRAM of the scratch PID.

Arm ON must first SHOW the purge (handoff correction 2026-10-03): `saving idle slot` lines
followed by `clearing prompt with N tokens` (N > 0) and/or a /slots sample where an idle
conversation's slot drops to 0 tokens while another slot is busy. If arm ON shows no purge,
the report says so and the A/B has nothing to compare.

Usage:
  b4i_idle_slots_ab.py --dry-run
  b4i_idle_slots_ab.py --print-launch
  b4i_idle_slots_ab.py --i-own-the-window --arm ON  --rep r1     (after `bash launch_ON.sh`)
  b4i_idle_slots_ab.py --compare results/b4i/ON-r1-*/report.json results/b4i/OFF-r1-*/report.json
"""
from __future__ import annotations

import argparse
import json
import shlex
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_gpublock as L  # noqa: E402

B4I = L.RESULTS / "b4i"
STORE_BIN = Path("/mnt/raid0/llm/kernels/production/gpu/llama-server")
LINKAGE = Path("/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
ENV_KEYS = ("LD_LIBRARY_PATH", "HIP_PATH", "ROCM_PATH", "OMP_PROC_BIND", "OMP_PLACES", "OMP_WAIT_POLICY",
            "OMP_DYNAMIC", "GGML_IQK")
# Read from the live :8083 (PID 1083497) environ at 2026-10-03 ~16:26Z; used only if :8083 is down
# when --print-launch runs. LLAMA_SERVER_SLOTS_DEBUG (the UFH14-A7 diag override) is excluded.
ENV_FALLBACK = {
    "LD_LIBRARY_PATH": "/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:"
                       "/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib",
    "HIP_PATH": "/opt/rocm", "ROCM_PATH": "/opt/rocm", "OMP_PROC_BIND": "spread", "OMP_PLACES": "cores",
    "OMP_WAIT_POLICY": "active", "OMP_DYNAMIC": "false", "GGML_IQK": "1",
}
SYSTEM = ("You are an autonomous coding agent working in a repository. You read tool outputs and keep a short, "
          "current list of the constraints that matter. Be brief.")


# --------------------------------------------------------------------------- launch scripts
def launch_spec(port: int) -> dict:
    rec = json.loads(L.LAUNCH_RECORD_8083.read_text())
    argv = list(rec["argv"])
    live = L.port_pid(8083)
    env_src, env = "fallback (live :8083 not listening)", dict(ENV_FALLBACK)
    if live:
        pe = L.proc_environ(live)
        if pe:
            env = {k: pe[k] for k in ENV_KEYS if k in pe}
            env_src = f"live :8083 PID {live} environ"
    return {"argv": argv, "env": env, "env_src": env_src, "record": str(L.LAUNCH_RECORD_8083),
            "record_launched_at": rec.get("launched_at"), "binary": rec.get("binary"),
            "binary_realpath": rec.get("binary_realpath"), "port": port}


def arm_argv(spec: dict, arm: str, port: int) -> list[str]:
    argv = list(spec["argv"])
    argv[argv.index("--port") + 1] = str(port)
    if "--slot-save-path" in argv:
        argv[argv.index("--slot-save-path") + 1] = str(B4I / "kv_slots_scratch")
    if arm == "OFF":
        argv.append("--no-cache-idle-slots")
    return argv


def write_launch(spec: dict, arm: str, port: int) -> tuple[Path, Path, str]:
    B4I.mkdir(parents=True, exist_ok=True)
    (B4I / "kv_slots_scratch").mkdir(exist_ok=True)
    argv = arm_argv(spec, arm, port)
    log = B4I / f"scratch-{arm}.log"
    pidf = B4I / f"scratch-{arm}.pid"
    envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in spec["env"].items())
    cmd = f"env -u LLAMA_SERVER_SLOTS_DEBUG {envs} {shlex.join(argv)}"
    bin_ = spec["binary"]
    launch = f"""#!/bin/bash
# UFH14-B4i scratch arm {arm} on :{port}. Generated by b4i_idle_slots_ab.py --print-launch at {L.now_iso()}.
# Argv source: {spec['record']} (launched_at {spec['record_launched_at']}); env source: {spec['env_src']}.
# PRECONDITION: production :8083 is STOPPED (two 27B processes do not fit in 64 GiB).
set -euo pipefail
if ss -ltn 'sport = :8083' | grep -q LISTEN; then echo "REFUSING: :8083 still listening (stop architect_critic first)"; exit 2; fi
if ss -ltn 'sport = :{port}' | grep -q LISTEN; then echo "REFUSING: :{port} already in use"; exit 2; fi
echo "=== launch $(date -u +%FT%TZ) arm {arm}" >> {shlex.quote(str(log))}
nohup {cmd} >> {shlex.quote(str(log))} 2>&1 &
PID=$!
echo "$PID" > {shlex.quote(str(pidf))}
echo "scratch {arm} PID $PID (log {log})"
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:{port}/health >/dev/null 2>&1; then break; fi
  if ! ps -p "$PID" >/dev/null; then echo "server PID $PID died during load; tail of log:"; tail -20 {shlex.quote(str(log))}; exit 1; fi
  sleep 2
done
curl -sf http://127.0.0.1:{port}/health && echo
echo "--- residency/linkage proof (read-only)"
tr '\\0' ' ' < /proc/$PID/cmdline; echo
grep -o '/[^ ]*libggml[^ ]*\\.so[^ ]*' /proc/$PID/maps | sort -u || echo 'no libggml in maps yet'
KFD=/sys/class/kfd/kfd/proc/$PID; if [ -d "$KFD" ]; then echo "KFD vram GiB: $(( $(cat $KFD/vram_* | paste -sd+ | bc) / 1073741824 ))"; else echo "NOT a KFD process (no GPU residency!)"; exit 1; fi
LD_LIBRARY_PATH={shlex.quote(spec['env'].get('LD_LIBRARY_PATH', ''))} {LINKAGE} {shlex.quote(bin_)} {shlex.quote(str(Path(bin_).parent.parent))} || echo "linkage check reported a problem"
"""
    kill = f"""#!/bin/bash
# Kill ONLY the captured scratch PID for arm {arm}; verify it is dead (SIGTERM -> SIGKILL).
set -euo pipefail
PID=$(cat {shlex.quote(str(pidf))})
ps -o pid,lstart,args -p "$PID" | cut -c1-200 || {{ echo "PID $PID not running"; exit 0; }}
tr '\\0' ' ' < /proc/$PID/cmdline | grep -q -- '--port {port}' || {{ echo "REFUSING: PID $PID is not the :{port} scratch server"; exit 2; }}
kill -TERM "$PID"
for i in $(seq 1 30); do ps -p "$PID" >/dev/null || break; sleep 1; done
if ps -p "$PID" >/dev/null; then echo "SIGTERM ignored after 30 s, sending SIGKILL"; kill -KILL "$PID"; sleep 2; fi
if ps -p "$PID" >/dev/null; then echo "PID $PID STILL ALIVE"; exit 1; fi
echo "PID $PID dead"; ls /sys/class/kfd/kfd/proc/; cat /sys/class/drm/card2/device/mem_info_vram_used
"""
    lp, kp = B4I / f"launch_{arm}.sh", B4I / f"kill_{arm}.sh"
    lp.write_text(launch)
    kp.write_text(kill)
    lp.chmod(0o755)
    kp.chmod(0o755)
    return lp, kp, cmd


# --------------------------------------------------------------------------- traffic
class Conv(threading.Thread):
    def __init__(self, c: int, a: argparse.Namespace, base: str, sink: L.JsonlSink, corpus) -> None:
        super().__init__(daemon=True)
        self.c, self.a, self.base, self.sink, self.corpus = c, a, base, sink, corpus
        self.rows: list[dict] = []

    def run(self) -> None:
        a = self.a
        time.sleep(self.c * a.stagger_s)
        ctx, n_ctx, _ = L.fit_prompt(self.base, a.base_tokens, L.nonce(f"b4i conv{self.c}"), start=2 * self.c)
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": ctx + "\n\nTask: list the three most important constraints in this material."}]
        stream_text = L.rotated_text(2 * self.c + 1, int(a.turns * a.turn_add_tokens * L.EST_CHARS_PER_TOKEN) + 10, self.corpus)
        step = int(a.turn_add_tokens * L.EST_CHARS_PER_TOKEN)
        prev_total = 0
        for turn in range(1, a.turns + 1):
            if turn > 1:
                chunk = stream_text[(turn - 2) * step:(turn - 1) * step]
                msgs.append({"role": "user", "content": f"Tool output (step {turn - 1}):\n{chunk}\n\nUpdate your list given this output."})
            body = {"messages": msgs, "max_tokens": a.gen, "temperature": 0.0,
                    "chat_template_kwargs": {"enable_thinking": False}}
            t_send = time.time()
            r = L.stream_request(f"{self.base}/v1/chat/completions", body, timeout=1800)
            ts = L.timing_summary(r.get("timings"))
            pn, cn = ts.get("prompt_n") or 0, ts.get("cache_n") or 0
            expected = max(0, prev_total - 64) if turn > 1 else 0  # template slack around the re-rendered reply
            missed = max(0, expected - cn)
            row = {"conv": self.c, "turn": turn, "t_send": round(t_send, 3), "http": r.get("http_status"),
                   "error": r.get("error"), "ttft_s": r.get("ttft_s"), "wall_s": r.get("wall_s"), **ts,
                   "expected_cached": expected, "missed_tokens": missed,
                   "missed_prefill_ms": round((ts.get("prompt_ms") or 0) * min(1.0, missed / pn), 1) if pn else 0.0}
            self.rows.append(row)
            self.sink.add(row)
            print(json.dumps({k: row[k] for k in ("conv", "turn", "ttft_s", "prompt_n", "cache_n", "expected_cached")}), flush=True)
            msgs.append({"role": "assistant", "content": r.get("content") or ""})
            prev_total = pn + cn + (ts.get("predicted_n") or 0)
            if turn < a.turns:
                time.sleep(a.pause_s + 3 * self.c)


def idle_drops(samples: list[tuple[float, list[dict]]]) -> list[dict]:
    """An idle slot holding tokens that holds 0 in the next sample while another slot is busy."""
    out = []
    for (t0, a), (t1, b) in zip(samples, samples[1:]):
        bb = {r["id"]: r for r in b}
        for r in a:
            nxt = bb.get(r["id"])
            if nxt and not r["proc"] and r["n_tok"] > 0 and nxt["n_tok"] == 0 and any(x["proc"] for x in b):
                out.append({"t": round(t1, 1), "slot": r["id"], "tokens_dropped": r["n_tok"]})
    return out


def arm_metrics(rows: list[dict]) -> dict:
    later = [r for r in rows if r["turn"] > 1 and r.get("ttft_s") is not None]
    tt = sorted(r["ttft_s"] for r in later)
    cn = sum(r.get("cache_n") or 0 for r in rows)
    pn = sum(r.get("prompt_n") or 0 for r in rows)
    pms = sum(r.get("prompt_ms") or 0 for r in rows)
    mms = sum(r.get("missed_prefill_ms") or 0 for r in rows)
    pms_later = sum(r.get("prompt_ms") or 0 for r in later)
    mms_later = sum(r.get("missed_prefill_ms") or 0 for r in later)
    return {"turns": len(rows), "errors": sum(1 for r in rows if r.get("http") != 200 or r.get("error")),
            "ttft_turn2plus_median_s": round(statistics.median(tt), 3) if tt else None,
            "ttft_turn2plus_p90_s": round(tt[int(0.9 * (len(tt) - 1))], 3) if tt else None,
            "ttft_turn2plus_mean_s": round(statistics.mean(tt), 3) if tt else None,
            "hit_tok": round(cn / (cn + pn), 4) if cn + pn else None,
            "prefill_s": round(pms / 1000, 2), "missed_prefill_share": round(mms / pms, 4) if pms else None,
            "missed_prefill_share_turn2plus": round(mms_later / pms_later, 4) if pms_later else None,
            "decode_tps_mean": round(statistics.mean([r["decode_tps"] for r in rows if r.get("decode_tps")]), 2)
            if any(r.get("decode_tps") for r in rows) else None}


def compare(paths: list[str]) -> int:
    reps = [json.loads(Path(p).read_text()) for p in paths]
    keys = ["ttft_turn2plus_median_s", "ttft_turn2plus_p90_s", "hit_tok", "missed_prefill_share_turn2plus",
            "prefill_s", "decode_tps_mean", "errors"]
    print("| arm/rep | purge shown | " + " | ".join(keys) + " | restores | restore fails | evictions | KFD peak GiB |")
    print("|---" * (len(keys) + 6) + "|")
    for r in reps:
        m, e = r["metrics"], r["log_events"]
        print(f"| {r['arm']}/{r['rep']} | {r['purge']['shown']} | " + " | ".join(str(m.get(k)) for k in keys) +
              f" | {e['restores_better']} | {e['restore_failures']} | {e['evictions']} | {r['vram']['kfd_peak_gib']} |")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-launch", action="store_true")
    ap.add_argument("--compare", nargs="+")
    ap.add_argument("--i-own-the-window", action="store_true")
    ap.add_argument("--port", type=int, default=18083)
    ap.add_argument("--arm", choices=("ON", "OFF"))
    ap.add_argument("--rep", default="r1")
    ap.add_argument("--server-log")
    ap.add_argument("--convs", type=int, default=3)
    ap.add_argument("--turns", type=int, default=6)
    ap.add_argument("--base-tokens", type=int, default=20000)
    ap.add_argument("--turn-add-tokens", type=int, default=1500)
    ap.add_argument("--gen", type=int, default=200)
    ap.add_argument("--pause-s", type=float, default=30)
    ap.add_argument("--stagger-s", type=float, default=12)
    args = ap.parse_args()
    if args.port == 8083:
        raise SystemExit("REFUSING: B4i runs on a scratch port, never :8083")
    if args.compare:
        return compare(args.compare)

    if args.dry_run or args.print_launch:
        problems: list[str] = []
        files = [L.check_file(L.LAUNCH_RECORD_8083, "production launch record", problems),
                 L.check_file(STORE_BIN, "kernel-store llama-server", problems),
                 L.check_file(LINKAGE, "verify_ggml_linkage.sh", problems)]
        spec = launch_spec(args.port)
        if Path(spec["binary"]).resolve() != STORE_BIN.resolve():
            problems.append(f"launch-record binary {spec['binary']} is not the kernel-store binary {STORE_BIN.resolve()}")
        if "--kv-unified" not in spec["argv"] or "--cache-ram" not in spec["argv"]:
            problems.append("launch-record argv lacks --kv-unified/--cache-ram (the purge path needs both)")
        if "--no-cache-idle-slots" in spec["argv"]:
            problems.append("production argv already carries --no-cache-idle-slots")
        sections = [("inputs", files + [f"argv from {spec['record']} (launched_at {spec['record_launched_at']}); env from {spec['env_src']}"])]
        for arm in ("ON", "OFF"):
            lp, kp, cmd = write_launch(spec, arm, args.port)
            sections.append((f"arm {arm} (main session runs these)", [f"bash {lp}", f"bash {kp}", f"command: {cmd}"]))
        per_arm = (args.convs * args.base_tokens / 600 + (args.turns - 1) * (args.pause_s + 3 * (args.convs - 1) + 12)) / 60
        sections += [
            ("traffic per arm", [f"{args.convs} conversations x {args.turns} turns; base ~{args.base_tokens} tok distinct; "
                                 f"+~{args.turn_add_tokens} tok per turn; gen {args.gen}; pauses {args.pause_s:.0f}+3c s; "
                                 f"conv starts staggered {args.stagger_s:.0f} s; greedy, thinking off",
                                 "samples /slots 2 s, KFD VRAM 1 s; scratch log scanned for idle saves / clears / restores / evictions"]),
            ("run", [f"b4i_idle_slots_ab.py --i-own-the-window --arm ON --rep r1   (after launch_ON.sh is healthy)",
                     "b4i_idle_slots_ab.py --compare results/b4i/ON-r1-*/report.json results/b4i/OFF-r1-*/report.json"]),
            ("estimate", [f"traffic ~{round(per_arm, 1)} min per arm + load ~2 min + kill ~0.5 min; "
                          f"ON/OFF ~{round(2 * (per_arm + 2.5))} min; ABA (ON/OFF/ON) ~{round(3 * (per_arm + 2.5))} min"]),
            ("outputs", [f"{B4I}/<ARM>-<rep>-<ts>/turns.jsonl, slots.jsonl, report.json; scratch logs {B4I}/scratch-<ARM>.log"]),
        ]
        if args.print_launch and not args.dry_run:
            for head, rows in sections:
                print(f"[{head}]")
                for r in rows:
                    print(f"  {r}")
            return 0 if not problems else 3
        return L.print_plan("b4i_idle_slots_ab.py (UFH14-B4i)", sections, problems)

    L.require_owner(args, f"this sends inference to the scratch server on :{args.port}")
    if not args.arm:
        raise SystemExit("--arm ON|OFF is required in run mode")
    base = f"http://127.0.0.1:{args.port}"
    pid = L.port_pid(args.port)
    argv = L.proc_cmdline(pid) if pid else []
    if not pid:
        raise SystemExit(f"nothing listening on :{args.port}; run launch_{args.arm}.sh first")
    has_off = "--no-cache-idle-slots" in argv
    if has_off != (args.arm == "OFF"):
        raise SystemExit(f"REFUSING: arm {args.arm} but the server argv has --no-cache-idle-slots={has_off}")
    log_path = Path(args.server_log) if args.server_log else B4I / f"scratch-{args.arm}.log"
    od = L.out_dir("b4i", f"{args.arm}-{args.rep}")
    log = L.LogWindow(log_path)
    turns = L.JsonlSink(od / "turns.jsonl")
    vs = L.VramSampler(pid, 1.0)
    ss = L.SlotsSampler(base, 2.0, sink=L.JsonlSink(od / "slots.jsonl"))
    pre = {"pid": pid, "pid_started": L.proc_lstart(pid), "argv": argv, "kfd": L.kfd_procs(),
           "prod_8083_listening": bool(L.port_pid(8083)), "props_build": (L.get_json(f"{base}/props", 10) or {}).get("build_info")}
    vs.start()
    ss.start()
    corpus = L.context_corpus()
    convs = [Conv(c, args, base, turns, corpus) for c in range(args.convs)]
    t0 = time.time()
    for c in convs:
        c.start()
    for c in convs:
        c.join()
    time.sleep(3)
    vs.stop_ev.set()
    ss.stop_ev.set()
    vs.join(timeout=3)
    ss.join(timeout=5)
    rows = [r for c in convs for r in c.rows]
    ev = L.prompt_cache_events(log.lines())
    drops = idle_drops(ss.samples)
    purge = {"idle_save_lines": ev["idle_saves"], "clear_nonzero_lines": ev["clear_nonzero"],
             "clear_nonzero_tokens": ev["clear_nonzero_tokens"], "slots_idle_drops": len(drops),
             "drops": drops[:20], "shown": ev["clear_nonzero"] > 0 or len(drops) > 0}
    rep = {"schema": "epyc.gpublock.b4i.v1", "arm": args.arm, "rep": args.rep, "at": L.now_iso(),
           "wall_s": round(time.time() - t0, 1), "preflight": pre, "args": vars(args), "metrics": arm_metrics(rows),
           "log_events": ev, "purge": purge, "vram": vs.summary(), "server_log": str(log_path),
           "log_offset_start": log.start, "rows": rows}
    if args.arm == "ON" and not purge["shown"]:
        rep["warning"] = ("arm ON did NOT show the idle-slot purge (no non-zero clear lines, no /slots drops): "
                          "the A/B has nothing to compare (handoff correction 2026-10-03)")
    L.write_json(od / "report.json", rep)
    print(json.dumps({"arm": args.arm, "metrics": rep["metrics"], "purge": {k: purge[k] for k in purge if k != "drops"},
                      "vram": rep["vram"], "warning": rep.get("warning")}, indent=1), flush=True)
    print(f"wrote {od}/report.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

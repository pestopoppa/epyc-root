#!/usr/bin/env python3
"""scenarios.py - hand-built replay fixtures, one per 2026-11-05 incident class. Each scenario is a short trace plus a
check(decisions) -> [violations]. The global INVARIANTS (replay_lib) are also checked on every scenario."""
from __future__ import annotations

import os

from replay_lib import GPU, QUARTERS, TraceWriter, _iso, contract_lite, cpu_set, qcores, tokens_to_cores  # noqa: F401

T0 = 1793836800.0   # 2026-11-05T00:00:00Z
TICK = 120
JOB = "/mnt/raid0/llm/tmp/replay-fixture"
POCKETS = set(range(116, 120)) | set(range(140, 144)) | set(range(164, 168))   # rowflow SMOKE_POCKETS (audit 2026-11-10 #5)


def launcher(rid, cls="cpu", claim="", gpu_quiet="", role="", extra="", job_text=None, nofold=False):
    d = f"{JOB}/{rid}"
    a = [f"--id {rid}", f"--class {cls}", "--min-window 600", "--complete-cmd 'true'", f"--stop {d}/STOP",
         f"--cmd '{d}/job.sh'"]
    if claim:
        a.append(f"--claim-cpus {claim}")
    if gpu_quiet:
        a.append(f"--gpu-quiet {gpu_quiet}")
    if role:
        a.append(f"--role {role}")
    if nofold:
        a.append("--no-fold-siblings")
    text = "#!/bin/bash\nset -euo pipefail\n" + f"exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh {' '.join(a)}\n"
    files = {f"{d}/job.sh": job_text if job_text is not None else f"#!/bin/bash\n{extra}\n"}
    return f"{d}/launch.sh", text, files


def row(rid, lane="cpu", regions="any-cpu-quarter", est=3600, stopped=False, passed=True, rank=100, man=None, **lk):
    lp, text, files = launcher(rid, **lk)
    m = {"schema": "epyc.row.v3", "id": rid, "owner": "replay", "lane": lane, "regions": regions,
         "launcher": {"path": lp}, "engine": {"path": "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh"},
         "window_s": est + 900, "min_window_s": 600, "estimate_s": est, "gib": 8, "priority_rank": rank, "ports": [],
         "result_path": f"{JOB}/{rid}/out/results.jsonl", "result_format": "jsonl", "decision_rule": "replay fixture",
         "handoff_task": "handoffs/active/replay.md:FIX", "published_at": _iso(T0 - 3600), "stop_file": f"{JOB}/{rid}/STOP",
         "first_progress_s": 300}
    m.update(man or {})
    blob = {"manifest": m, "launcher_text": text, "files": files, "stopped": stopped, "fails": [],
            "pass": {"id": rid, "passed_at": _iso(T0 - 1800), "units": 1, "result_path": m["result_path"]} if passed else None,
            "pass_matches": True}
    return blob


def write(path, ticks, notes=""):
    w = TraceWriter(path, "scenario", notes)
    for i, (rows, world) in enumerate(ticks):
        w.tick(T0 + i * TICK, rows, **world)
    w.close()
    return path


def _granted(decisions, rid):
    return [(d["i"], g) for d in decisions for g in d["grants"] if g["id"] == rid]


# ---------------------------------------------------------------------------------------------- scenarios
def sc_stopped(path):
    """F4: lsa-oracle-reference-build-f6dddb7's manifest carried an UNEXPANDED `$D/STOP` (launcher D=<its own dir>);
    it was granted 1,344 times while stopped. Plus a plain literal-path stopped row."""
    lsa = row("lsa-oracle-reference-build-f6dddb7", stopped=True, extra="make -j 16", man={"stop_file": "$D/STOP"})
    d = f"{JOB}/lsa-oracle-reference-build-f6dddb7"
    lsa["launcher_text"] = lsa["launcher_text"].replace("set -euo pipefail\n", 'set -euo pipefail\nD="$(cd "$(dirname "$0")" && pwd)"\n') \
        .replace(f"--stop {d}/STOP", '--stop "$D/STOP"')
    rows = {"stopped-row": row("stopped-row", stopped=True, extra="python3 x.py --workers 8"),
            "lsa-oracle-reference-build-f6dddb7": lsa}
    return write(path, [(rows, {})] * 4), lambda d: [f"granted stopped row {g['id']} at tick {i}"
                                                       for i, g in _granted(d, "stopped-row") + _granted(d, "lsa-oracle-reference-build-f6dddb7")]


def sc_one_thread(path):
    # gitnexus impact: --workers 1, declared shape host on 0-95 (22 such grants on 11-05)
    r = row("kpf41-impact-w1", regions="0-95", claim="0-95", extra="gitnexus analyze --workers 1",
            man={"shape": "host", "busy_fraction": 0.05})
    def check(d):
        out = []
        for i, g in _granted(d, "kpf41-impact-w1"):
            if set(QUARTERS) <= ({h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])):
                out.append(f"1-thread row got the whole host at tick {i}: {g['holds']}")
        if not _granted(d, "kpf41-impact-w1"):
            out.append("1-thread row never granted at all (must be right-sized, not starved)")
        return out
    return write(path, [({"kpf41-impact-w1": r}, {})] * 4), check


def _fullq(holds):
    from replay_lib import full_quarters
    return full_quarters(tokens_to_cores(set(holds)))


def sc_gpu_work_q3(path):
    """GPU non-timing row (kvu16g2-decstep form) running; a CPU correctness row that can only use q3 must be granted."""
    g = row("kvu16g2-decstep", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200,
            extra="llama-server -t 8", man={"admission_class": "correctness"})
    c = row("q3-build", regions="any-of q3", extra="make -j 24", est=1800)
    # q0-q2 held by foreign jobs so q3 is the only CPU room
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    ticks = [({"kvu16g2-decstep": g}, world)] + [({"kvu16g2-decstep": g, "q3-build": c}, world)] * 3
    def check(d):
        if not _granted(d, "kvu16g2-decstep"):
            return ["GPU work row never granted"]
        return [] if _granted(d, "q3-build") else ["q3 left idle beside a GPU NON-timing grant (q3 must stay grantable)"]
    return write(path, ticks), check


def sc_gpu_timing_q3(path):
    """GPU timing row (hsf5p-profile form) running; a CPU timing row wanting q3 must NOT be placed there."""
    g = row("hsf5p-profile6-q3", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", claim="72-95",
            role="bench", est=7200, extra="rocprof -t 8")
    c = row("cpu-bench-q3", regions="any-of q3", role="bench", gpu_quiet="", extra="llama-bench -t 24", est=1800)
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    # two lone ticks: an EXCLUSIVE grant needs GPU_QUIET_SAMPLES consecutive quiet host-view samples
    ticks = [({"hsf5p-profile6-q3": g}, world)] * 2 + [({"hsf5p-profile6-q3": g, "cpu-bench-q3": c}, world)] * 3
    def check(d):
        out = []
        tg = _granted(d, "hsf5p-profile6-q3")
        if not tg:
            return ["GPU timing row never granted"]
        for i, g2 in _granted(d, "cpu-bench-q3"):
            if i < tg[0][0] + 60 and tokens_to_cores(set(g2["holds"])) & set(range(72, 96)):
                out.append(f"CPU timing row placed on q3 at tick {i} beside a GPU timing grant")
        return out
    return write(path, ticks), check


NPD1_JOB = '''import subprocess
THREADS = "48"
CPUS = "0-95"
def launch(port):
    return subprocess.Popen(["taskset", "-c", CPUS, "numactl", "--interleave=all", "llama-server", "-t", THREADS, "--port", str(port)])
'''


def sc_npd1_step5(path):
    """Whole-host CPU serving: cpu+gpu, gpu-quiet exclusive, claim 0-95, -t THREADS (a Python variable = 48)."""
    lp, text, files = launcher("npd1-step5-20261105", cls="cpu+gpu", claim="0-95", gpu_quiet="exclusive", role="bench")
    files[f"{JOB}/npd1-step5-20261105/job.py"] = NPD1_JOB
    text = text.replace("job.sh'", "job.py'")
    r = row("npd1-step5-20261105", lane="gpu", regions="mi210_0,0-95", est=3000, rank=40,
            man={"shape": "quiet-host", "gib": 130, "declared_threads": None, "baseline_ref": None})
    r["launcher_text"], r["files"] = text, files
    r["pass"]["vram_used_max_bytes"] = 6693199872
    def check(d):
        gs = _granted(d, "npd1-step5-20261105")
        if not gs:
            return ["npd1-step5 (48-thread whole-host CPU serving) never granted: refused/starved"]
        i, g = gs[0]
        hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
        out = []
        if not set(QUARTERS) <= hq:
            out.append(f"npd1-step5 not admitted whole-host: holds {g['holds']}")
        if i > LIV:
            out.append(f"npd1-step5 granted only at tick {i}")
        return out
    return write(path, [({"npd1-step5-20261105": r}, {})] * 4), check


LIV = 3


def sc_coexist_lockset(path):
    """gpu-q3 GPU timing row whose engine locks ONLY its gpu threads (--no-fold-siblings) + an UNMARKED single-worker
    gitnexus row pinned to 72-79: lock sets are disjoint -> must co-run. A second gpu-q3 row whose claim locks GLOBAL.q3
    EX must NOT get a coexist row beside it (that co-run is fake: the coexist engine would block in region-lock)."""
    g = row("inf34-gpu-timing", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="bench -t 8")
    x = row("kpf17-impact-sq3", regions="72-79", claim="72-79", extra="taskset -c 72-79 gitnexus analyze --workers 1",
            est=1200)
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    ticks = [({"inf34-gpu-timing": g}, world)] + [({"inf34-gpu-timing": g, "kpf17-impact-sq3": x}, world)] * 3
    def check(d):
        if not _granted(d, "inf34-gpu-timing"):
            return ["gpu-q3 timing row never granted"]
        return [] if _granted(d, "kpf17-impact-sq3") else \
            ["lock-disjoint coexist row (72-79, --workers 1) never co-ran beside the gpu-q3 grant (declaration-gated?)"]
    return write(path, ticks), check


def sc_gpu_timing_narrow_q3(path):
    """gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"): q38p4b-int8-20261105 (GPU timing, regions
    mi210_0,184-191, --role bench) was refused "needs gpu-quiet,q3,t184..t191: q3 busy" while an 8-core AITER build sat on
    80-87/176-183. An 8-core q3 CPU row and a GPU timing row must be granted CONCURRENTLY: the GPU timing grant holds
    gpu-quiet + 88-95 + 184-191 and never q3 cores 72-87. q0-q2 are foreign so q3 is the only CPU room."""
    b = row("rock-aiter-prebuild-r4", regions="80-87", claim="80-87", extra="taskset -c 80-87,176-183 make -j 8", est=7200)
    g = row("q38p4b-int8", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="llama-bench -t 8", man={"shape": "gpu-q3"})
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    # the build first (two lone ticks: an EXCLUSIVE grant needs GPU_QUIET_SAMPLES quiet samples anyway), then the timing row
    ticks = [({"rock-aiter-prebuild-r4": b}, world)] * 2 + [({"rock-aiter-prebuild-r4": b, "q38p4b-int8": g}, world)] * 4

    def check(d):
        out = []
        bg, tg = _granted(d, "rock-aiter-prebuild-r4"), _granted(d, "q38p4b-int8")
        if not bg:
            return ["8-core q3 CPU row never granted (scenario precondition)"]
        if not tg:
            return ["GPU timing row never granted beside an 8-core q3 CPU grant (the q38p4b-int8 refusal)"]
        i, g2 = tg[0]
        if "rock-aiter-prebuild-r4" not in d[i]["open_before"] and bg[0][0] != i:
            out.append(f"GPU timing row granted at tick {i} only after the q3 CPU grant closed (not concurrent)")
        held = tokens_to_cores(set(g2["holds"]))
        if held & set(range(72, 88)) or "q3" in g2["holds"]:
            out.append(f"GPU timing grant holds q3 cores 72-87: {sorted(g2['holds'])}")
        if not set(range(88, 96)) <= held or GPU not in g2["holds"]:
            out.append(f"GPU timing grant does not hold gpu-quiet + 88-95: {sorted(g2['holds'])}")
        bh = tokens_to_cores(set(bg[0][1]["holds"]))
        if not bh <= set(range(80, 88)):
            out.append(f"8-core CPU grant holds more than 80-87: {sorted(bg[0][1]['holds'])}")
        return out
    return write(path, ticks), check


def sc_gpu_timing_narrow_q3_reverse(path):
    """Same pair, GPU timing grant first: the 8-core q3 CPU row is granted beside it (72-87 stay grantable)."""
    g = row("q38p4b-int8", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="llama-bench -t 8", man={"shape": "gpu-q3"})
    b = row("rock-aiter-prebuild-r4", regions="80-87", claim="80-87", extra="taskset -c 80-87,176-183 make -j 8", est=3600)
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    ticks = [({"q38p4b-int8": g}, world)] * 3 + [({"q38p4b-int8": g, "rock-aiter-prebuild-r4": b}, world)] * 3

    def check(d):
        tg, bg = _granted(d, "q38p4b-int8"), _granted(d, "rock-aiter-prebuild-r4")
        if not tg:
            return ["GPU timing row never granted (scenario precondition)"]
        if not bg:
            return ["8-core q3 CPU row never granted beside an open GPU timing grant (72-87 must stay grantable)"]
        i = bg[0][0]
        if "q38p4b-int8" not in d[i]["open_before"]:
            return [f"CPU row granted at tick {i} only after the GPU timing grant closed (not concurrent)"]
        return []
    return write(path, ticks), check


def sc_smoke_whole_host(path):
    """A queued smoke while a whole-host grant runs: SMOKE-WAIT each tick (never FAIL, never an exception), and placed
    within two ticks of the host freeing."""
    h = row("akx-host-48", regions="0-95", claim="0-95", extra="bench -t 96", est=TICK * 3,
            man={"shape": "host", "shape_override": "operator: replay 2026-11-05: fixture"})
    s = row("smoke-me", passed=False, extra="python3 x.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-me", "queued_at": _iso(T0), "cpus": 4}
    ticks = [({"akx-host-48": h, "smoke-me": s}, {})] * 7
    def check(d):
        out, hg = [], _granted(d, "akx-host-48")
        if not hg:
            return ["whole-host row never granted (scenario precondition)"]
        if any("smoke-me" in f for x in d for f in x["fails_new"]):
            out.append("smoke FAILed under a whole-host grant")
        free_at = next((x["i"] for x in d if x["i"] > hg[0][0] and "akx-host-48" not in x["open_after"]), None)
        placed = next((x["i"] for x in d for l in x["lines"] if l.startswith("SMOKE-PLACE smoke-me") or l.startswith("PLAN smoke smoke-me")), None)
        waited = any(l.startswith("SMOKE-WAIT smoke-me") for x in d for l in x["lines"])
        if not waited and (placed is None or placed > hg[0][0]):
            out.append("smoke neither WAITed nor ran beside the whole-host grant (silent hang)")
        if free_at is not None and (placed is None or placed > free_at + 2):
            out.append(f"smoke not placed within 2 ticks of the host freeing at tick {free_at} (hang)")
        return out
    return write(path, ticks), check


def sc_dryrun_deadline(path):
    """codex-ifbench-cj6a-27b-v4-20261104: dry run started 11-04 15:30Z, engine never reached START, pid alive -> must
    be reaped (killed / WAIT / FAIL, RUNNING.json gone, cpus freed) once past its deadline."""
    rid = "codex-ifbench-cj6a-27b-v4-20261104"
    r = row(rid, passed=False, regions="0-3", claim="0-3", extra="python3 ifbench.py --workers 4", man={"first_progress_s": 900})
    r["running"] = {"id": rid, "started": "2026-11-04T15:30:02Z", "regions": "0-3", "at": "2026-11-04T15:30:02Z"}
    r["running_alive"] = True
    r["dry_grant"] = f"regions=0-3 start=2026-11-04T15:29Z end=2026-11-04T16:04Z holds=c0,c1,c2,c3\n"
    def check(d):
        last = d[-1]["running_json"].get(rid)
        if last and last["pid_alive"]:
            return [f"wedged dry run (alive since 11-04 15:30Z) not reaped after {len(d)} ticks"]
        return []
    return write(path, [({rid: r}, {})] * 4), check


def sc_deadpid_release(path):
    """Same row, pid DEAD (stale dryrun grant + RUNNING.json): its cpus c0-c3 must be free again within one tick, so a
    row that needs exactly 0-3 is granted."""
    rid = "codex-ifbench-cj6a-27b-v4-20261104"
    r = row(rid, passed=False, regions="0-3", claim="0-3", extra="python3 ifbench.py --workers 4", man={"first_progress_s": 900})
    r["running"] = {"id": rid, "started": "2026-11-04T15:30:02Z", "regions": "0-3", "at": "2026-11-04T15:30:02Z"}
    r["running_alive"] = False
    r["dry_grant"] = "regions=0-3 start=2026-11-04T15:29Z end=2026-11-04T16:04Z holds=c0,c1,c2,c3\n"
    w = row("needs-c0-3", regions="0-3", claim="0-3", extra="python3 y.py --workers 4", est=1200)
    world = {"foreign": {"q1": "f1", "q2": "f2", "q3": "f3"}}
    def check(d):
        gs = _granted(d, "needs-c0-3")
        return [] if gs and gs[0][0] <= 1 else ["c0-c3 held by a dead dry run past one tick (needs-c0-3 not granted by tick 1)"]
    return write(path, [({rid: r, "needs-c0-3": w}, world)] * 4), check


def sc_idle_named(path):
    """Every quarter free, one grantable row that fits nowhere for a reason (RAM): every free region must carry an
    IDLE-WHY naming the rule, every tick."""
    r = row("big-ram", extra="python3 z.py --workers 8", man={"gib": 2000})
    return write(path, [({"big-ram": r}, {"mem_gib": 500.0})] * 5), lambda d: []


def sc_declared_shape(path):
    """inf34 v15: shape 'gpu' declared over mi210_0,0-95, launcher class gpu, claim 0-95, no evidence -> never books
    q0-q2 (the declared shape must not bypass the evidence check)."""
    r = row("refactor-inf34-a2-gpu-qual-v15", lane="gpu", regions="mi210_0,0-95", cls="gpu", gpu_quiet="exclusive",
            claim="0-95", extra="python3 qual.py", man={"shape": "gpu"})
    def check(d):
        out = []
        for i, g in _granted(d, "refactor-inf34-a2-gpu-qual-v15"):
            hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
            if hq & {"q0", "q1", "q2"}:
                out.append(f"declared shape=gpu booked {sorted(hq)} without evidence at tick {i}")
        return out
    return write(path, [({"refactor-inf34-a2-gpu-qual-v15": r}, {})] * 3), check


def sc_smoke_packing(path):
    """(2026-11-10: a smoke pocket now also satisfies this.) PACKING (operator "fix it" 2026-11-05): a 4-core smoke and two whole-quarter rows queued; q2 foreign, q3 partly used
    by a GPU row's host threads. The smoke must land on q3's non-GPU cores and both whole-quarter rows get q0 + q1 the
    same tick; with no partly used quarter (variant: q2 + q3 foreign) the smoke waits rather than break a quarter."""
    gpu = row("kvu-gpu-work", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200, extra="llama-server -t 8")
    r1 = row("whole-q-a", extra="make -j 16", est=3600)
    r2 = row("whole-q-b", extra="make -j 16", est=3600)
    s = row("smoke-4c", passed=False, extra="python3 x.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-4c", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q2": "foreign-c"}}
    rows = {"kvu-gpu-work": gpu, "whole-q-a": r1, "whole-q-b": r2, "smoke-4c": s}
    ticks = [({"kvu-gpu-work": gpu}, world)] + [(rows, world)] * 3

    def check(d):
        out = []
        for rid in ("whole-q-a", "whole-q-b"):
            gs = _granted(d, rid)
            if not gs or gs[0][0] > 1:
                out.append(f"whole-quarter row {rid} not granted on tick 1 (starved by the smoke?)")
        pl = [l for x in d for l in x["lines"] if l.startswith("SMOKE-PLACE smoke-4c")]
        if not pl:
            out.append("smoke never placed although q3 had 16 free non-GPU cores")
        else:
            import re as _re
            cs = cpu_set(_re.search(r"cpus=(\S+)", pl[0]).group(1))
            if not (cs <= POCKETS or not {c % 96 for c in cs} - set(range(72, 88))):
                out.append(f"smoke placed on {sorted(cs)[:8]}... outside the smoke pockets and q3's non-GPU cores")
        return out
    return write(path, ticks), check


def sc_smoke_waits_for_whole(path):
    """Variant: q2 + q3 foreign, two whole-quarter rows + a smoke: the smoke never breaks q0/q1 (it waits)."""
    r1 = row("whole-q-a", extra="make -j 16", est=3600)
    r2 = row("whole-q-b", extra="make -j 16", est=3600)
    s = row("smoke-4c", passed=False, extra="python3 x.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-4c", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q2": "foreign-c", "q3": "foreign-d"}}

    def check(d):
        return [f"whole-quarter row {rid} not granted on tick 0" for rid in ("whole-q-a", "whole-q-b")
                if not _granted(d, rid) or _granted(d, rid)[0][0] > 0]
    return write(path, [({"whole-q-a": r1, "whole-q-b": r2, "smoke-4c": s}, world)] * 3), check


def sc_subquarter_free_cores(path):
    """20 free cores (q0-q2 foreign, a 2-thread row on 4 of q3's cores) + a 4-thread any-cpu-quarter row: the contract
    says 4 cores, so it is placed on the free q3 cores the same tick - not starved waiting for a whole quarter."""
    a = row("small-a", extra="python3 a.py --workers 2", est=7200)
    b = row("small-b", extra="python3 b.py --workers 4", est=3600)
    world = {"foreign": {"q0": "f0", "q1": "f1", "q2": "f2"}}

    def check(d):
        out = []
        ga, gb = _granted(d, "small-a"), _granted(d, "small-b")
        if not ga:
            out.append("2-thread row never placed on q3's free cores")
        if not gb or gb[0][0] > 1:
            out.append("4-thread row not placed on the 20 free q3 cores on tick 1")
        for i, g in ga + gb:
            if _fullq(g["holds"]) or set(g["holds"]) & set(QUARTERS):
                out.append(f"sub-quarter row {g['id']} held a whole quarter: {g['holds'][:6]}")
        return out
    return write(path, [({"small-a": a}, world)] + [({"small-a": a, "small-b": b}, world)] * 3), check


def sc_gpu_exclusive_no_kfd(path):
    """GPU EXCLUSIVITY (kvu16g2-ab-20261105, 12:52Z: 41.17e9 B foreign VRAM + 83 foreign KFD pids under a gpu-quiet
    EXCLUSIVE grant). While the exclusive grant is open, nothing else that can open /dev/kfd may start: not a cpu-lane HIP
    build row, not an -ngl > 0 row, not the smoke of either. After the grant ends they run."""
    ab = row("kvu16g2-ab", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", nofold=True,
             est=TICK * 3, extra="llama-server -ngl 99 -t 8", man={"admission_class": "correctness"})
    hip = row("llg-build-gpu", extra="cmake -B build-hip -DGGML_HIP=ON && cmake --build build-hip -j 16", est=1200)
    ngl = row("cpu-lane-ngl", extra="llama-server -ngl 40 -t 8", est=1200)
    sm = row("hip-smoke", passed=False, extra="hipcc -o t t.cpp && ./t --workers 2")
    sm["smoke_queued"] = {"id": "hip-smoke", "queued_at": _iso(T0), "cpus": 4}
    rows = {"kvu16g2-ab": ab, "llg-build-gpu": hip, "cpu-lane-ngl": ngl, "hip-smoke": sm}
    ticks = [({"kvu16g2-ab": ab}, {})] + [(rows, {})] * 30   # GPU holders serialize: smoke, then each row

    def check(d):
        gs = _granted(d, "kvu16g2-ab")
        if not gs:
            return ["exclusive GPU row never granted (precondition)"]
        out = []
        for x in d:
            if "kvu16g2-ab" not in x["open_before"]:
                continue
            for g in x["grants"]:
                if g["id"] != "kvu16g2-ab":
                    out.append(f"{g['id']} granted at tick {x['i']} beside the gpu-quiet EXCLUSIVE grant (holds {g['holds'][:4]})")
            for l in x["lines"]:
                if l.startswith("SMOKE-PLACE hip-smoke"):
                    out.append(f"HIP smoke placed at tick {x['i']} beside the gpu-quiet EXCLUSIVE grant")
        for rid in ("llg-build-gpu", "cpu-lane-ngl"):
            if not _granted(d, rid):
                out.append(f"{rid} never granted after the exclusive grant ended (starved)")
        return out
    return write(path, ticks), check


def sc_gpu_foreign_vram(path):
    """kvu16g2-ab-20261105: foreign VRAM from ANOTHER container (twyne-root / sangha-root map the MI210; no keeper lock or
    grant names them). An EXCLUSIVE row is not granted while a foreign KFD client holds >= 1 GiB (IDLE-WHY names it), is
    granted after two quiet samples, and a foreign client appearing mid-grant raises GPU-CONTAMINATED."""
    ex = row("kvu16g2-ab", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", nofold=True,
             role="bench", est=TICK * 20, extra="llama-server -ngl 99 -t 8")
    foreign = {"kfd": {"3449271": 41170000000}, "vram_bytes": 41170000000}
    ticks = [({"kvu16g2-ab": ex}, foreign)] * 3 + [({"kvu16g2-ab": ex}, {})] * 4 + [({"kvu16g2-ab": ex}, foreign)] * 3

    def check(d):
        out = []
        gs = _granted(d, "kvu16g2-ab")
        if any(i < 3 for i, _ in gs):
            out.append(f"EXCLUSIVE grant at tick {gs[0][0]} while 41 GB foreign VRAM was resident")
        if not gs or gs[0][0] > 5:
            out.append("EXCLUSIVE row not granted within two quiet samples after the foreign VRAM left")
        if not any(l.startswith("IDLE-WHY gpu-quiet") and "3449271" in l for x in d[:3] for l in x["lines"]):
            out.append("no IDLE-WHY gpu-quiet naming the foreign KFD pid while it held the device")
        if not any(l.startswith("GPU-CONTAMINATED kvu16g2-ab") for x in d[7:] for l in x["lines"]):
            out.append("foreign VRAM under an open EXCLUSIVE grant raised no GPU-CONTAMINATED")
        return out
    return write(path, ticks), check


def sc_pass_is_terminal(path):
    """q38p4c-cpu-int8-20261105: the smoke PASSed (12:52:12Z) but its queue record and a dead RUNNING.json remained; the
    keeper reaped + requeued it and 'state grantable; nothing to do' counted as never-started -> FAIL-1 overrode the PASS.
    A PASS for the current launcher is terminal: never re-smoked, never FAILed, the row is granted."""
    rid = "q38p4c-cpu-int8-20261105"
    r = row(rid, extra="python3 bench.py --workers 4", est=1800)
    r["smoke_queued"] = {"id": rid, "queued_at": _iso(T0 - 300), "cpus": 4, "waits": 2}
    r["running"] = {"id": rid, "started": _iso(T0 - 200), "regions": "72-75", "at": _iso(T0 - 200)}
    r["running_alive"] = False
    r["dry_grant"] = f"regions=72-75 start={_iso(T0 - 240)[:16]}Z end={_iso(T0 + 1800)[:16]}Z holds=c72,c73,c74,c75\n"

    def check(d):
        out = []
        if any(rid in f for x in d for f in x["fails_new"]):
            out.append("a FAIL was recorded after the row's PASS")
        if any(l.startswith(f"SMOKE-PLACE {rid}") for x in d for l in x["lines"]):
            out.append("a grantable (PASSed) row was re-smoked")
        if not _granted(d, rid):
            out.append("PASSed row never granted")
        return out
    return write(path, [({rid: r}, {})] * 4), check


def sc_gpu_blocked_whole_rows_free_smokes(path):
    """CLASSFIX (2026-11-05 14:55Z keeper log): rock-aiter-build holds q3 + the MI210 host threads; three queued GPU rows that also need a
    whole CPU quarter cannot run, so they reserve nothing - the queued smokes are placed on the free quarters."""
    g1 = row("gpu-whole-a", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3600,
                             role="bench", extra="llama-server -t 8")
    g2 = row("gpu-whole-b", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3600,
                             role="bench", extra="llama-server -t 8")
    g3 = row("gpu-whole-c", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3600,
                             role="bench", extra="llama-server -t 8")
    s1 = row("smoke-x", passed=False, extra="python3 x.py --workers 2")
    s1["smoke_queued"] = {"id": "smoke-x", "queued_at": _iso(T0), "cpus": 4}
    s2 = row("smoke-y", passed=False, extra="python3 y.py --workers 2")
    s2["smoke_queued"] = {"id": "smoke-y", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q3": "rock-aiter-build", "q1": "hil15b-heavy"}}
    rows = {"gpu-whole-a": g1, "gpu-whole-b": g2, "gpu-whole-c": g3, "smoke-x": s1, "smoke-y": s2}
    ticks = [(rows, world)] * 3

    def check(d):
        out = []
        if any(_granted(d, r) for r in ("gpu-whole-a", "gpu-whole-b", "gpu-whole-c")):
            out.append("fixture: a GPU row was granted (GPU not held)")
        for sid in ("smoke-x", "smoke-y"):
            if not any(l.startswith(f"SMOKE-PLACE {sid}") or l.startswith(f"PLAN smoke {sid}") for x in d for l in x["lines"]):
                out.append(f"{sid} starved by whole-quarter rows blocked on the held GPU")
        return out
    return write(path, ticks), check


def sc_cpu_whole_row_reservation_holds(path):
    """CLASSFIX counter-case: a CPU whole-quarter row runnable NOW keeps its reservation; with q2 + q3 foreign and two
    such rows, the smoke must not break q0/q1."""
    r1 = row("cpu-whole-a", extra="make -j 16", est=3600)
    r2 = row("cpu-whole-b", extra="make -j 16", est=3600)
    s = row("smoke-z", passed=False, extra="python3 z.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-z", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q2": "foreign-c", "q3": "foreign-d"}}

    def check(d):
        out = [f"whole-quarter row {rid} not granted on tick 0" for rid in ("cpu-whole-a", "cpu-whole-b")
               if not _granted(d, rid) or _granted(d, rid)[0][0] > 0]
        import re as _re
        for l in (l for x in d[:1] for l in x["lines"] if l.startswith("SMOKE-PLACE smoke-z")):
            if not cpu_set(_re.search(r"cpus=(\S+)", l).group(1)) <= POCKETS:
                out.append("smoke broke a whole quarter a runnable CPU row needed")
        return out
    return write(path, [({"cpu-whole-a": r1, "cpu-whole-b": r2, "smoke-z": s}, world)] * 3), check


def _idle_held_rows(util_busy):
    """One GPU row (rock-aiter-tests-r3 form: gpu lane, mi210_0,184-191, class gpu, 2 h estimate) granted at tick 0 and
    then measured at util_busy % on the device every tick; q0-q2 foreign so nothing else moves."""
    g = row("rock-aiter-tests-r3", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200,
            extra="ctest --test-dir build-hip", man={"admission_class": "correctness"})
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"},
             "util": {"q0": 90.0, "q1": 90.0, "q2": 90.0, "q3": 0.0,
                      "gpu": {"busy": util_busy, "vram_pct": 0.0 if not util_busy else 40.0, "vram_gib": 0.0, "card": "card2"}}}
    return {"rock-aiter-tests-r3": g}, world


def _warn_lines(d, rid):
    return [(x["i"], l) for x in d for l in x["lines"] if l.startswith(f"IDLE-HELD-WARN gpu-quiet {rid}:")]


def sc_idle_held_warns_once(path):
    """operator 2026-11-05 (notify-only): rock-aiter-tests-r3-20261105 held gpu-quiet at 0% for ~20 min (21:20-21:41Z,
    stale lock) and nobody was told. 8 ticks x 120 s: the grant is IDLE-HELD from tick 1 (age > 60 s) and gets EXACTLY
    ONE IDLE-HELD-WARN (owner notified) once it has been idle >= 300 s - never before, never twice within 15 min - and
    the grant is never ended."""
    rows, world = _idle_held_rows(0)
    ticks = [(rows, world)] * 8

    def check(d):
        out = []
        if not _granted(d, "rock-aiter-tests-r3"):
            return ["fixture: GPU row never granted"]
        w = _warn_lines(d, "rock-aiter-tests-r3")
        if len(w) != 1:
            out.append(f"expected exactly one IDLE-HELD-WARN over 8 ticks (16 min), got {len(w)}: {w}")
        if w and w[0][0] < 3:
            out.append(f"warned at tick {w[0][0]} (< 300 s idle)")
        if not any(l.startswith("IDLE-HELD gpu-quiet rock-aiter-tests-r3") for x in d for l in x["lines"]):
            out.append("fixture: the grant never read IDLE-HELD")
        if any(x["open_after"].get("rock-aiter-tests-r3") is None for x in d[1:]):
            out.append("the grant was ended by the keeper (notify-only: it must never be)")
        return out
    return write(path, ticks), check


def sc_idle_held_repeats_each_15min(path):
    """Same grant over 14 ticks (28 min): the second warning comes >= 900 s after the first, and no third."""
    rows, world = _idle_held_rows(0)
    ticks = [(rows, world)] * 14

    def check(d):
        w = _warn_lines(d, "rock-aiter-tests-r3")
        if len(w) != 2:
            return [f"expected exactly two IDLE-HELD-WARN over 14 ticks, got {len(w)}: {w}"]
        if (w[1][0] - w[0][0]) * TICK < 900:
            return [f"repeat warning after {(w[1][0] - w[0][0]) * TICK}s (< 900 s)"]
        return []
    return write(path, ticks), check


def sc_idle_held_busy_grant_silent(path):
    """Control: the same grant measured 95% busy on the device never warns (and never reads IDLE-HELD)."""
    rows, world = _idle_held_rows(95)
    ticks = [(rows, world)] * 8

    def check(d):
        if not _granted(d, "rock-aiter-tests-r3"):
            return ["fixture: GPU row never granted"]
        w = _warn_lines(d, "rock-aiter-tests-r3")
        return [f"a busy grant was warned: {w}"] if w else []
    return write(path, ticks), check



# ---------------------------------------------------------------------------------------------- friction pass 4 (2026-11-06)
PRECOND_LINE = ("refuse rc=12: not ready: precond-cmd failed: printf '%s %s\n' c66f05148e35355bd04292958d9a123b0a80f1db "
                "'/mnt/raid0/llm/tmp/heterogeneous-slot-fabric/kpf50/input.json' | sha256sum -c --status")
DEAD_LINE = "refuse rc=14: launcher pid {pid} of {rid} is dead (no /proc/{pid} or zombie)"


def _fails_per_tick(d):
    return [len(x["fails_new"]) for x in d]


def _lines(d, prefix):
    return [(x["i"], l) for x in d for l in x["lines"] if l.startswith(prefix)]


def sc_precond_parks_once(path):
    """P4.4 row 1: kpf50-child-evidence-main-impact-r2 was refused by its own --precond-cmd 171 times (06:34Z-09:26Z, one
    per tick) and alerted 171 times, because its live poller kept it `armed`. Rule: the FIRST refusal parks the row (one
    FAIL, one PARK line); it is never re-admitted until its manifest changes (tick 5: a republish with new notes), which
    buys exactly one more refusal episode."""
    rid = "kpf50-child-evidence-main-impact-20261104-r2"
    r = row(rid, regions="any-cpu-quarter", est=3600)
    r["admit"] = {"refuse": PRECOND_LINE}
    r2 = dict(r, manifest=dict(r["manifest"], notes="precondition input regenerated"))
    world = {"foreign": {}}
    ticks = [({rid: r}, world)] * 5 + [({rid: r2}, world)] * 3

    def check(d):
        out = []
        f = _fails_per_tick(d)
        if f != [1, 0, 0, 0, 0, 1, 0, 0]:
            out.append(f"FAIL records per tick {f}; expected one at tick 0 and one at tick 5 (the spec change), never per tick")
        park = _lines(d, f"PARK {rid}:")
        if [i for i, _ in park] != [0, 5]:
            out.append(f"PARK lines at ticks {[i for i, _ in park]}; expected [0, 5]")
        skip = _lines(d, f"SKIP {rid}:")
        if skip:
            out.append(f"the parked row was re-admitted (SKIP lines at ticks {[i for i, _ in skip]})")
        if _granted(d, rid):
            out.append("a refused row was granted")
        return out
    return write(path, ticks), check


def sc_completed_not_rc14(path):
    """P4.4 row 2: v11-122-llg-build-cpu / c6q4isum-llg-build-gpu & co: `refuse rc=14: launcher pid N is dead` was written
    as a launch FAIL (+ owner alert, + fix_task) 1 s after the poller had finished the WHOLE job (grants/<id>.complete,
    .ended rc=0 reason=complete). Rule: a receipt present at admission time makes a dead pid a COMPLETION: no FAIL, no
    alert, a COMPLETE line, and the row is `done` from the next tick (never a candidate again)."""
    rid = "v11-122-llg-build-cpu-20261105"
    r = row(rid, regions="any-cpu-quarter", est=3600)
    r["admit"] = {"refuse": DEAD_LINE, "complete_marker": True, "pid_dies": True}
    ticks = [({rid: r}, {"foreign": {}})] * 3

    def check(d):
        out = []
        if sum(_fails_per_tick(d)):
            out.append(f"a completed row got a FAIL record (per tick {_fails_per_tick(d)})")
        c = _lines(d, f"COMPLETE {rid}:")
        if [i for i, _ in c] != [0]:
            out.append(f"COMPLETE lines at ticks {[i for i, _ in c]}; expected exactly one, at tick 0")
        if any((x["cands"] or 0) > 0 for x in d[1:]):
            out.append("the completed row stayed a candidate after its receipt")
        if _granted(d, rid):
            out.append("a completed row was granted")
        return out
    return write(path, ticks), check


def sc_dead_poller_without_receipt_still_fails(path):
    """Control for the rule above: the same dead pid with NO receipt is still a launch FAIL (a real dead poller)."""
    rid = "akx-c6-n4-generic-vs-candidate-20261104"
    r = row(rid, regions="any-cpu-quarter", est=3600)
    r["admit"] = {"refuse": DEAD_LINE, "pid_dies": True}
    ticks = [({rid: r}, {"foreign": {}})] * 2

    def check(d):
        out = []
        if _fails_per_tick(d)[0] != 1:
            out.append(f"a genuinely dead poller must still FAIL at tick 0 (got {_fails_per_tick(d)})")
        if _lines(d, f"COMPLETE {rid}:"):
            out.append("COMPLETE logged without any receipt")
        return out
    return write(path, ticks), check


def _gpu_harness_rows(util_busy, regions="mi210_0,184-191", q3=0.0):
    g = row("ak-asm-t1-harness", lane="gpu", regions=regions, cls="gpu", nofold=True, est=7200,
            extra="python3 harness.py --device rocm", man={"admission_class": "correctness"})
    g["kfd_own"] = True
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"},
             "util": {"q0": 90.0, "q1": 90.0, "q2": 90.0, "q3": q3,
                      "gpu": {"busy": util_busy, "vram_pct": 3.0, "vram_gib": 2.0, "card": "card2"}}}
    return {"ak-asm-t1-harness": g}, world


def sc_gpu_harness_with_kfd_never_idle(path):
    """P4.4 rows 3-4: ak-asm-t1-harness (a RUNNING GPU harness: own KFD client, 2 GiB VRAM) read IDLE-HELD gpu-quiet and
    warned its owner 30+ times because the device busy % sampled 0 between kernels and its host threads sat idle. Rule:
    a grant whose own process tree holds a KFD client is busy; it never reads IDLE-HELD and never warns - 8 ticks."""
    rows, world = _gpu_harness_rows(0)
    ticks = [(rows, world)] * 8

    def check(d):
        out = []
        if not _granted(d, "ak-asm-t1-harness"):
            return ["fixture: GPU row never granted"]
        held = _lines(d, "IDLE-HELD")
        if held:
            out.append(f"a GPU grant with its own KFD client read IDLE-HELD: {held[:3]}")
        return out
    return write(path, ticks), check


def sc_gpu_grant_cpu_regions_not_judged(path):
    """A GPU grant over mi210_0 + all of q3 (kvu16g3 form): q3 reads 0 % CPU while the device is 80 % busy and no KFD
    client is attributable (a fenced child container). CPU % never judges a GPU-token grant: no IDLE-HELD q3."""
    rows, world = _gpu_harness_rows(80, regions="mi210_0,72-95", q3=0.0)
    rows["ak-asm-t1-harness"]["kfd_own"] = False
    ticks = [(rows, world)] * 6

    def check(d):
        out = []
        if not _granted(d, "ak-asm-t1-harness"):
            return ["fixture: GPU row never granted"]
        held = _lines(d, "IDLE-HELD")
        if held:
            out.append(f"IDLE-HELD read on a GPU grant by CPU %: {held[:3]}")
        return out
    return write(path, ticks), check


def sc_gpu_grant_quiet_device_idle_after_two_samples(path):
    """Counter-case: no own KFD client AND the device at 0 % - IDLE-HELD gpu-quiet only from the 2nd quiet sample (tick 2:
    tick 0 grants, tick 1 is sample 1), then warns the owner once >= 300 s later (the pass-3 notify-only contract)."""
    rows, world = _gpu_harness_rows(0)
    rows["ak-asm-t1-harness"]["kfd_own"] = False
    ticks = [(rows, world)] * 8

    def check(d):
        out = []
        held = [i for i, _ in _lines(d, "IDLE-HELD gpu-quiet ak-asm-t1-harness")]
        if not held or held[0] != 2:
            out.append(f"IDLE-HELD gpu-quiet should start at tick 2 (2nd quiet sample), got ticks {held[:4]}")
        if any(l for _, l in _lines(d, "IDLE-HELD q3")):
            out.append("q3 judged by CPU % under a GPU grant")
        w = [i for i, _ in _lines(d, "IDLE-HELD-WARN gpu-quiet ak-asm-t1-harness:")]
        if len(w) != 1:
            out.append(f"expected exactly one owner warning over 8 ticks, got {w}")
        return out
    return write(path, ticks), check


def sc_p5_idle_held_logs_once(path):
    """Pass 5 item 3 (2026-11-07): a GPU grant that stays quiet reads IDLE-HELD from tick 2 and the keeper must say so ONCE
    (a state transition), not on every one of the following ticks. The grant itself is still judged idle every tick."""
    rows, world = _gpu_harness_rows(0)
    rows["ak-asm-t1-harness"]["kfd_own"] = False
    ticks = [(rows, world)] * 8

    def check(d):
        held = [i for i, _ in _lines(d, "IDLE-HELD gpu-quiet ak-asm-t1-harness")]
        if len(held) != 1 or held[0] != 2:
            return [f"IDLE-HELD logged on ticks {held} over 8 quiet ticks; expected exactly one line, at tick 2 (transition only)"]
        return []
    return write(path, ticks), check


def sc_override_multiquarter_books_two(path):
    """lsa-quality-32k-20261106-r4-pca: regions any-cpu-quarter, declared multi-quarter(2) accepted via shape_override, threads
    unknown. It was granted ONE quarter (q1) while q3 sat idle. A 2-quarter row is granted two whole quarters or waits."""
    rid = "lsa-r4-pca-override"
    r = row(rid, regions="any-cpu-quarter", extra="python3 job.py", man={
        "declared_shape": "multi-quarter(2)", "shape": "quarter",
        "shape_override": "operator: pestopoppa 2026-11-06: widen LSA pca arm to 2 quarters (longest arm)"})
    free_q1_only = {"q1": {"busy": False}}

    def check(d):
        out = []
        for i, g in _granted(d, rid):
            hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
            if len(hq) != 2:
                out.append(f"2-quarter row granted {sorted(hq)} at tick {i}")
        if not _granted(d, rid):
            out.append("2-quarter row never granted on an idle host")
        return out
    return write(path, [({rid: r}, {})] * 3), check


def sc_multiquarter_never_q3(path):
    """operator 2026-11-06 "Yes, both": lsa-quality-32k-20261106-r5-pca (multi-quarter(2) via shape_override) was granted q1+q3;
    its q3 lock covered 88-95 (the cores behind MI210 host threads 184-191) and a GPU row waited 600 s on it (rc75). With q0
    and q2 busy and only q1 + q3 free the row WAITS: a CPU multi-quarter booking is q0-q2 only."""
    rid = "lsa-r5-pca-override"
    r = row(rid, regions="any-cpu-quarter", extra="python3 job.py", man={
        "declared_shape": "multi-quarter(2)", "shape": "quarter",
        "shape_override": "operator: pestopoppa 2026-11-06: widen LSA pca arm to 2 quarters (longest arm)"})
    world = {"foreign": {"q0": "foreign-a", "q2": "foreign-b"}}

    def check(d):
        out = []
        for i, g in _granted(d, rid):
            hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
            out.append(f"multi-quarter CPU row granted {sorted(hq)} at tick {i} (q3 must never be booked)")
        return out
    return write(path, [({rid: r}, world)] * 3), check


def _backfill_rows(gpu=True):
    """2026-11-07 incident: lsa-quality-32k-20261106-r8-{dense,pca} hold q0+q1 for 10 h; the whole-host row
    c7-local-code28k-20261106-r3 (q0-q3) waits; rows that need only q2 / q3 / the GPU are ready."""
    lsa_d = row("lsa-r8-dense", regions="any-of q0", extra="python3 job.py --workers 24", est=36000, rank=20)
    lsa_p = row("lsa-r8-pca", regions="any-of q1", extra="python3 job.py --workers 24", est=36000, rank=20)
    wide = row("c7-code28k-r3", regions="q0,q1,q2,q3", claim="0-95", extra="make -j 96", est=5400, rank=40,
               man={"shape": "host", "declared_shape": "host", "baseline_ref": "replay fixture: whole-host serving"})
    wide["pass"]["passed_at"] = _iso(T0 - 4 * 3600)   # waited > DRAIN_AFTER_S: the wide row drains
    q2 = row("bf-q2-build", regions="any-of q2", extra="make -j 24", est=3 * 3600, rank=60)
    q3 = row("bf-q3-build", regions="any-of q3", extra="make -j 24", est=3 * 3600, rank=60)
    rows = {"lsa-r8-dense": lsa_d, "lsa-r8-pca": lsa_p, "c7-code28k-r3": wide, "bf-q2-build": q2, "bf-q3-build": q3}
    if gpu:
        rows["bf-gpu-tests"] = row("bf-gpu-tests", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=2 * 3600,
                                   rank=60, extra="ctest --test-dir build-hip", man={"admission_class": "correctness"})
    return rows


def sc_backfill_if_fits(path):
    """Backfill-if-fits (operator 2026-11-07 "Approve + deploy"): LSA holds q0+q1 (10 h left), a whole-host row waits;
    the q2 / q3 / GPU rows end long before the whole-host row's earliest feasible start (the LSA grants' end), so they
    are granted. A foreign hold with no known end on q1 (tick 1) makes the start UNKNOWN: no reservation at all."""
    rows = _backfill_rows()
    lsa = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca")}
    ticks = [(lsa, {})] + [(rows, {})] * 4

    def check(d):
        out = []
        if not _granted(d, "lsa-r8-dense") or not _granted(d, "lsa-r8-pca"):
            return ["fixture: the LSA rows were not granted on tick 0"]
        for rid in ("bf-q2-build", "bf-q3-build", "bf-gpu-tests"):
            if not _granted(d, rid):
                out.append(f"{rid} never granted: q2/q3/gpu idled behind the whole-host row's drain")
        if _granted(d, "c7-code28k-r3"):
            out.append("fixture: the whole-host row was granted while q0+q1 are busy")
        return out
    return write(path, ticks), check


def sc_backfill_reserve_binds(path):
    """Counter-case: a row that would END AFTER the whole-host row's earliest feasible start may not take its regions."""
    rows = _backfill_rows(gpu=False)
    long_q2 = row("bf-q2-long", regions="any-of q2", extra="make -j 24", est=20 * 3600, rank=60)
    rows = {k: v for k, v in rows.items() if k not in ("bf-q2-build", "bf-q3-build")}
    rows["bf-q2-long"] = long_q2
    lsa = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca")}
    ticks = [(lsa, {})] + [(rows, {})] * 3

    def check(d):
        return [f"bf-q2-long (ends after the whole-host start) granted at tick {i}" for i, _ in _granted(d, "bf-q2-long")]
    return write(path, ticks), check


def sc_backfill_expired_drain(path):
    """Expired drains never block: a persisted drain T in the past (the wide row's T may only move earlier) must not
    keep q2/q3 idle. Ticks 0-16: q0+q1 foreign (no end known); from tick 16 the drain's persisted T has expired."""
    rows = _backfill_rows(gpu=False)
    wide = {"c7-code28k-r3": rows["c7-code28k-r3"]}
    world = {"foreign": {"q0": "foreign-lsa-dense", "q1": "foreign-lsa-pca"}}
    tw = TraceWriter(path, "scenario", "")
    for i in range(16):
        tw.tick(T0 + i * TICK, wide, **world)
    rest = {k: rows[k] for k in ("c7-code28k-r3", "bf-q2-build", "bf-q3-build")}
    for i in range(16, 20):
        tw.tick(T0 + i * TICK, rest, **world)
    tw.close()

    def check(d):
        return [f"{rid} never granted after the drain expired" for rid in ("bf-q2-build", "bf-q3-build") if not _granted(d, rid)]
    return path, check



# ---------------------------------------------------------------------------------------------- scheduling model (audit 2026-11-10 C)
def _held_ticks(d, rid):
    """Ticks rid's simulated job was open (grant tick to the tick its engine ended it)."""
    return sum(1 for x in d if rid in x["open_after"])


def _drain_world(extra):
    """LSA rows hold q0+q1 (est 2 h -> grant end ~2 h 15 m); the whole-host row c7 drains for them; `extra` backfills."""
    rows = _backfill_rows(gpu=False)
    rows = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca", "c7-code28k-r3")}
    for k in ("lsa-r8-dense", "lsa-r8-pca"):
        rows[k]["manifest"].update(estimate_s=7200, window_s=8100)
    lsa = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca")}
    return lsa, dict(rows, **extra)


def sc_race_eqv_books_by_estimate(path):
    """race-eqv-gpu-r3-20261109 (11-10 04:33-06:38): a row whose estimate overstates its run could not pass a drain and ran
    7 minutes once admitted. Shape-equivalent on q2: estimate 9000 s, drain start ~2 h 15 m away; the old rule admitted by
    estimate + 25 % (11250 s, window 9900 s) and held q2 idle; book_s = 0.75 * 9000 = 6750 s fits, so it is admitted with
    its grant end capped at the drain start and runs its real 7 minutes."""
    r = row("race-eqv-r3-shape", regions="any-of q2", extra="make -j 24", est=9000, rank=60,
            man={"window_s": 9900, "min_window_s": 600})
    r["actual_s"] = 420
    lsa, rows = _drain_world({"race-eqv-r3-shape": r})
    ticks = [(lsa, {})] + [(rows, {})] * 6

    def check(d):
        g = _granted(d, "race-eqv-r3-shape")
        if not g or g[0][0] > 1:
            return ["race-eqv-r3-shape not admitted ahead of the drain by its book_s (q2 idled behind the drain)"]
        gl = [l for l in d[g[0][0]]["lines"] if l.startswith("GRANT race-eqv-r3-shape ")]
        lsa = [l for l in d[0]["lines"] if l.startswith("GRANT lsa-r8-dense ")]
        end = lambda l: l.split(" end=")[1].split()[0]   # noqa: E731
        if not gl or not lsa or end(gl[0]) != end(lsa[0]):
            return ["admitted ahead of the drain without its grant end capped at the drain start"]
        if _held_ticks(d, "race-eqv-r3-shape") * TICK > 420 + 2 * TICK:
            return ["did not end at its real 7-minute run"]
        return []
    return write(path, ticks), check


def sc_resumable_window_end(path):
    """ak-c10-q38fn-floor-r2-20261110 ran out of window at pairs-5 of 24: a resumable row whose job outlasts its window
    ends at the grant end (hard-end rc=75, a normal end for it), never a FAIL, and is not re-granted by the keeper."""
    r = row("ak-floor-resumable", regions="any-of q0", extra="make -j 24", est=4900, rank=50,
            man={"resumable": True, "window_s": 6180, "min_window_s": 600})
    r["actual_s"] = 4 * 4900
    ticks = [({"ak-floor-resumable": r}, {})] * 60

    def check(d):
        out = []
        g = _granted(d, "ak-floor-resumable")
        if len(g) != 1:
            out.append(f"granted {len(g)} times (want exactly 1)")
        if not 0 < _held_ticks(d, "ak-floor-resumable") * TICK <= 6180 + 2 * TICK:
            out.append("the job was not ended at its window")
        if any("ak-floor-resumable" in f for x in d for f in x["fails_new"]):
            out.append("a resumable window end was recorded as a FAIL")
        return out
    return write(path, ticks), check


def sc_overrun_capped_at_drain(path):
    """c10-fold-cpu-q38pp-r2-20261109 ran out of window after 4 of 6 rounds. A non-resumable row admitted ahead of a drain
    that overruns its estimate is still ended at the drain start (the kept hard-end safety): the drain row starts on time."""
    r = row("c10-fold-overrun", regions="any-of q2", extra="make -j 24", est=1800, rank=60,
            man={"window_s": 2460, "min_window_s": 600})
    r["actual_s"] = 3 * 3600
    lsa, rows = _drain_world({"c10-fold-overrun": r})
    rows["c7-code28k-r3"]["manifest"]["estimate_s"] = 600
    ticks = [(lsa, {})] + [(rows, {})] * 90

    def check(d):
        g = _granted(d, "c10-fold-overrun")
        if not g:
            return ["fixture: the overrun row was never admitted"]
        if not 0 < _held_ticks(d, "c10-fold-overrun") * TICK <= 2460 + 2 * TICK:
            return ["overrun row held q2 past its window"]
        return []
    return write(path, ticks), check


def sc_smoke_pockets_no_starvation(path):
    """142 SMOKE-WAIT in two days ("no 4 free cores outside the whole quarters N queued rows need") while regions idled:
    with q2 + q3 foreign and two whole-quarter rows queued, the rows take q0 + q1 AND both smokes run on tick 0 in the
    q0 / q1 pockets."""
    r1 = row("pk-whole-a", extra="make -j 16", est=3600)
    r2 = row("pk-whole-b", extra="make -j 16", est=3600)
    sm = {}
    for i, sid in enumerate(("pk-smoke-1", "pk-smoke-2")):
        b = row(sid, passed=False, extra="python3 x.py --workers 2")
        b["smoke_queued"] = {"id": sid, "queued_at": _iso(T0 + i), "cpus": 4}
        sm[sid] = b
    world = {"foreign": {"q2": "foreign-c", "q3": "foreign-d"}}

    def check(d):
        out = [f"{rid} not granted on tick 0" for rid in ("pk-whole-a", "pk-whole-b")
               if not _granted(d, rid) or _granted(d, rid)[0][0] > 0]
        for sid in sm:
            if not any(l.startswith(f"SMOKE-PLACE {sid}") for l in d[0]["lines"]):
                out.append(f"{sid} not placed on tick 0 (starved)")
        return out
    return write(path, [(dict({"pk-whole-a": r1, "pk-whole-b": r2}, **sm), world)] * 3), check

SCENARIOS = {
    "sched-race-eqv-books-by-estimate": sc_race_eqv_books_by_estimate,
    "sched-resumable-window-end": sc_resumable_window_end,
    "sched-overrun-capped-at-drain": sc_overrun_capped_at_drain,
    "sched-smoke-pockets-no-starvation": sc_smoke_pockets_no_starvation,
    "backfill-if-fits-lsa-whole-host": sc_backfill_if_fits,
    "backfill-reserve-binds-long-row": sc_backfill_reserve_binds,
    "backfill-expired-drain-never-blocks": sc_backfill_expired_drain,
    "multiquarter-never-q3": sc_multiquarter_never_q3,
    "override-multiquarter-books-two": sc_override_multiquarter_books_two,
    "stopped-never-granted": sc_stopped,
    "one-thread-not-whole-host": sc_one_thread,
    "gpu-work-leaves-q3-grantable": sc_gpu_work_q3,
    "gpu-timing-keeps-q3-quiet": sc_gpu_timing_q3,
    "npd1-step5-whole-host-admitted": sc_npd1_step5,
    "coexist-by-lockset": sc_coexist_lockset,
    "smoke-under-whole-host-waits": sc_smoke_whole_host,
    "dryrun-deadline-reaped": sc_dryrun_deadline,
    "dead-dryrun-releases-in-one-tick": sc_deadpid_release,
    "idle-regions-named": sc_idle_named,
    "declared-shape-no-bypass": sc_declared_shape,
    "smoke-packs-onto-partly-used-q3": sc_smoke_packing,
    "smoke-never-breaks-needed-whole-quarter": sc_smoke_waits_for_whole,
    "subquarter-row-on-20-free-cores": sc_subquarter_free_cores,
    "gpu-exclusive-admits-no-kfd-holder": sc_gpu_exclusive_no_kfd,
    "gpu-foreign-vram-blocks-exclusive": sc_gpu_foreign_vram,
    "smoke-pass-is-terminal": sc_pass_is_terminal,
    "gpu-blocked-whole-rows-free-smokes": sc_gpu_blocked_whole_rows_free_smokes,
    "cpu-whole-row-reservation-holds": sc_cpu_whole_row_reservation_holds,
    "gpu-timing-narrow-q3-concurrent-with-8core-build": sc_gpu_timing_narrow_q3,
    "gpu-timing-narrow-q3-build-beside-open-timing": sc_gpu_timing_narrow_q3_reverse,
    "idle-held-warns-owner-once": sc_idle_held_warns_once,
    "idle-held-repeat-warning-15min": sc_idle_held_repeats_each_15min,
    "idle-held-busy-grant-silent": sc_idle_held_busy_grant_silent,
    "p4-precond-refusal-parks-once": sc_precond_parks_once,
    "p4-completed-row-not-rc14": sc_completed_not_rc14,
    "p4-dead-poller-without-receipt-still-fails": sc_dead_poller_without_receipt_still_fails,
    "p4-gpu-harness-with-kfd-never-idle-held": sc_gpu_harness_with_kfd_never_idle,
    "p4-gpu-grant-cpu-regions-not-judged": sc_gpu_grant_cpu_regions_not_judged,
    "p4-gpu-grant-quiet-device-idle-after-two-samples": sc_gpu_grant_quiet_device_idle_after_two_samples,
    "p5-idle-held-logs-once": sc_p5_idle_held_logs_once,
}

# which global invariants each scenario is ABOUT (the others are still checked; these are its subject)
SUBJECT = {
    "stopped-never-granted": ["INV-STOP", "INV-REGRANT"],
    "one-thread-not-whole-host": ["INV-1THREAD", "INV-EVIDENCE"],
    "gpu-timing-keeps-q3-quiet": ["INV-GPU-TIMING-Q3"],
    "coexist-by-lockset": ["INV-LOCKSET"],
    "dryrun-deadline-reaped": ["INV-DRYRUN-DEADLINE"],
    "dead-dryrun-releases-in-one-tick": ["INV-DEADPID-RELEASE"],
    "idle-regions-named": ["INV-IDLE-WHY-ALL", "INV-IDLE-NAMED"],
    "declared-shape-no-bypass": ["INV-EVIDENCE"],
    "gpu-timing-narrow-q3-concurrent-with-8core-build": ["INV-GPU-TIMING-Q3", "INV-LOCKSET"],
    "gpu-timing-narrow-q3-build-beside-open-timing": ["INV-GPU-TIMING-Q3", "INV-LOCKSET"],
}


# ---------------------------------------------------------------------------------------------- PUBLISH-path scenarios
# The allocation replay never runs rowflow.publish; these run the candidate's publish() on a temp tree.
NPD1_STEP5_JOB = '''import subprocess
SMOKE = False
THREADS = "48" if not SMOKE else "4"
CPUS = "0-95"
def launch(port):
    return subprocess.Popen(["taskset", "-c", CPUS, "numactl", "--interleave=all", "llama-server", "-t", THREADS, "--port", str(port)])
'''


def pub_npd1_step5(root):
    """keeper-hotfix D14: npd1-step5's spec (cpu+gpu, gpu-quiet exclusive, claim 0-95, role bench, -t THREADS = 48,
    numactl --interleave=all) is whole-host CPU serving and MUST be accepted at publish (8fbe18182 refused it)."""
    d = os.path.join(root, "npd1-step5-20261105")
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write(NPD1_STEP5_JOB)
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\ncd \"$D\"\nexec /bin/bash {eng} --id npd1-step5-20261105 "
                        "--class cpu+gpu --gpu-quiet exclusive --claim-cpus 0-95 --role bench --min-window 3600 "
                        "--cmd \"/usr/bin/python3 -I $D/job.py\" --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": "npd1-step5-20261105", "owner": "ws58", "launcher": lp, "lane": "gpu", "regions": "mi210_0,0-95",
            "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/mi210-serving-program.md:NPD1-STEP5", "ram_gib": 130,
            "first_progress_s": 900, "priority_rank": 40}

    def check(row, err):
        if err is not None:
            return [f"npd1-step5 refused at publish: {err}"]
        out = []
        if row.get("shape") not in ("quiet-host", "host"):
            out.append(f"npd1-step5 published as {row.get('shape')}, not whole-host")
        if row.get("declared_threads") != 48:
            out.append(f"npd1-step5 threads {row.get('declared_threads')} != 48 (-t THREADS not resolved)")
        return out
    return spec, check


INF75_JOB = """import os, subprocess
def helper():
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    return subprocess.run(["python3", "census.py"], env=env)
def serve(port):
    return subprocess.Popen(["llama-server", "-t", "48", "--port", str(port)])
"""


def pub_inf75_helper_omp(root):
    """inf75-c5-w3-halfb-census-c6-r2 (2026-11-05): llama-server -t 48 on 48-95,144-191 (cpu+gpu, gpu-quiet exclusive)
    was refused as 'threads 1: OMP_NUM_THREADS 1' - the OMP knob belonged to a Python helper's env. Thread evidence is
    the compute binary's own argv; a helper's OMP_NUM_THREADS is never evidence."""
    rid = "inf75-c5-w3-halfb-census-c6-r2-20261105"
    d = os.path.join(root, rid)
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write(INF75_JOB)
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexec /bin/bash {eng} --id {rid} --class cpu+gpu "
                        "--gpu-quiet exclusive --claim-cpus 48-95,144-191 --min-window 3600 --cmd \"/usr/bin/python3 -B $D/job.py\" "
                        "--complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": rid, "owner": "inf22", "launcher": lp, "lane": "gpu", "regions": "mi210_0,48-95,144-191",
            "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:INF75", "ram_gib": 64, "first_progress_s": 900}

    def check(row, err):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        return [] if row.get("declared_threads") == 48 else [f"threads {row.get('declared_threads')} != 48 (helper OMP taken as evidence)"]
    return spec, check


YARN_JOB_SIDE = """import os, subprocess
def job(port):
    env = os.environ
    if env.get('FILLER_THREADS') != '24' or len(os.sched_getaffinity(0)) != 48:
        raise ValueError("affinity")
    procenv = {'PATH': '/usr/bin:/bin', 'OMP_NUM_THREADS': '24', 'OMP_PROC_BIND': 'spread'}
    return subprocess.run(['llama-server', '--port', str(port)], env=procenv).returncode
def smoke():
    procenv = {'PATH': '/usr/bin:/bin', 'OMP_NUM_THREADS': '1'}
    return subprocess.run(['python3', '-c', 'pass'], env=procenv).returncode
"""


def pub_yarn_job_side_threads(root):
    """yarn-oolong-s1/s2-import-eligible29-v38 (2026-11-05): launch.sh's blanket `export OMP_NUM_THREADS=1` was the
    only evidence read; the compute process (job_side.py, imported by boot.py) runs llama-server with OMP 24 and
    refuses FILLER_THREADS != 24 -> contract sub-quarter, granted 4 cores. The compute process's declared threads win."""
    rid = "yarn-like-job-side-24t"
    d = os.path.join(root, rid)
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job_side.py"), "w").write(YARN_JOB_SIDE)
    open(os.path.join(d, "boot.py"), "w").write("import sys\nimport job_side\nraise SystemExit(job_side.job(19412))\n")
    open(os.path.join(d, "job.sh"), "w").write(f"#!/bin/bash\nD={d}\nexport PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 "
                                                "OPENBLAS_NUM_THREADS=1\nexec taskset -c \"${FILLER_CPUS:?}\" python3 \"$D/boot.py\"\n")
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexec /bin/bash {eng} --id {rid} --class cpu --role build "
                        f"--min-window 3600 --cmd 'bash {d}/job.sh --job' --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter",
            "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:YARN", "first_progress_s": 900}

    def check(row, err):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        bad = []
        if row.get("declared_threads") != 24:
            bad.append(f"threads {row.get('declared_threads')} != 24 (wrapper OMP 1 taken over the compute process's 24)")
        if row.get("shape") != "quarter":
            bad.append(f"shape {row.get('shape')} != quarter")
        return bad
    return spec, check


def _mk_cpu_row(root, rid, job, cmd_extra=""):
    d = os.path.join(root, rid)
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write(job)
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n"
                        f"exec /bin/bash {eng} --id {rid} --class cpu --role build --min-window 900 "
                        f"--cmd \"/usr/bin/python3 -B $D/job.py{cmd_extra}\" --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    return d, lp


def _quarter_only(row, err, rf, want_gpu=False):
    if err is not None:
        return [f"refused at publish: {err[:200]}"]
    c = rf.contract_of(row)
    bad = [] if c["shape"] == "quarter" else [f"shape {c['shape']} != quarter"]
    if any(rf.GPU in x for x in c["options"]) != want_gpu:
        bad.append(f"gpu-quiet in options {c['options'][:1]}")
    return bad


def pub_stt5_cpu_declared_no_gpu(root):
    """STT5 r5 (2026-11-05): --class cpu, device cpu, whisper-cli -ng whose path sits under a HIP-capable tree, -t =
    affinity width; granted holds=c72..c75,gpu-quiet: 4 cores AND the GPU token. A cpu-declared row never holds it."""
    rid = "stt5-like-cpu-declared"
    d, lp = _mk_cpu_row(root, rid, "import os\nBIN='/mnt/raid0/llm/whisper.cpp/build-hip/bin/whisper-cli'\n"
                                    "cmd=[BIN,'-ng','-t',str(len(os.sched_getaffinity(0)))]\n")
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter", "device": "cpu",
            "shape": "quarter", "gpu_fence_override": "owner: t 2026-11-05: -ng, HIP_VISIBLE_DEVICES=-1",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:STT5", "first_progress_s": 600}
    return spec, lambda row, err, rf: _quarter_only(row, err, rf)


def pub_iqk_declared_quarter_floor(root):
    """iqk-q8-prefill-ab/-step0 (2026-11-05): declared shape quarter (CPU timing), smoke measured ~2 threads on its 4
    cpus -> granted 72-75 + 168-171, jobs refused rc 8 "not a whole quarter". A declared quarter is never shrunk."""
    rid = "iqk-like-declared-quarter"
    d, lp = _mk_cpu_row(root, rid, "import os\nassert len(os.sched_getaffinity(0)) == 48, 'not a whole quarter'\n")
    os.makedirs(os.path.join(root, "compute-flags", "dryrun", rid), exist_ok=True)
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter", "shape": "quarter",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:IQK", "first_progress_s": 600}

    def check(row, err, rf):
        return _quarter_only(dict(row or {}, measured_threads=2.2), err, rf)
    return spec, check


def pub_iqk_ab_r3_explicit_q2(root):
    """iqk-q8-prefill-ab-r3-20261105: regions "q2", shape quarter, operator shape_override -> GRANTED 80-83,176-179
    (4 cores on q3). Explicit regions + shape_override are honoured verbatim: exactly q2."""
    rid = "iqk-q8-prefill-ab-r3-like"
    d, lp = _mk_cpu_row(root, rid, "import os\nassert len(os.sched_getaffinity(0)) >= 24, 'not a whole quarter'\n")
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "q2", "shape": "quarter",
            "shape_override": "operator: op 2026-11-05: CPU timing A/B needs one whole quarter",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:IQK", "first_progress_s": 600}

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(dict(row, measured_threads=3.1))
        bad = [] if [set(x) - {rf.GPU} for x in c["options"]] == [{"q2"}] else [f"options {c['options']} != [q2]"]
        g = rf.grant_regions(row, c["options"][0])
        if rf._cpu_set(g) != rf._cpu_set(rf.cpu_list("q2")):
            bad.append(f"grant regions {g} != q2")
        return bad
    return spec, check


def pub_inf75_c6_r2_explicit_override(root):
    """inf75-c5-w3-halfb-census-c6-r2-20261105: regions mi210_0,48-95,144-191 + operator shape_override -> GRANTED
    mi210_0,80-83,176-179; admission refused "missing q2". Granted regions and lock are the declared ones verbatim."""
    spec, _ = pub_inf75_helper_omp(root)
    spec["shape_override"] = "operator: op 2026-11-05: canonical INF-75 half-B placement"

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(dict(row, measured_threads=1.2, declared_threads=1))
        bad = []
        if len(c["options"]) != 1 or not {"q2", "q3", rf.GPU} <= set(c["options"][0]):
            bad.append(f"options {c['options']} do not hold q2+q3+gpu")
        g = rf.grant_regions(row, c["options"][0])
        if g != row["regions"]:
            bad.append(f"grant regions {g} != {row['regions']}")
        if c.get("explicit_cpus") and rf._cpu_set(c["explicit_cpus"]) != rf._cpu_set("48-95,144-191"):
            bad.append(f"lock {c['explicit_cpus']} != 48-95,144-191")
        return bad
    return spec, check


def _wj_spec(root, rid, **kw):
    d, lp = _mk_cpu_row(root, rid, "import os\nassert len(os.sched_getaffinity(0)) >= 48, 'width-agnostic prefill'\n")
    txt = open(lp).read().replace("export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n", "")   # width-agnostic: no thread knob
    open(lp, "w").write(txt)
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter", "shape": "multi-quarter(2)",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:LSA", "first_progress_s": 600}
    spec.update(kw)
    return spec


def pub_wj_justified_accepted(root):
    """lsa-quality-32k-20261106-r4-pca: width-agnostic CPU prefill, multi-quarter(2), width_justification, NO shape_override."""
    spec = _wj_spec(root, "lsa-wj-ok", width_justification="width-agnostic prefill; throughput scales with threads")

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(row)
        return [] if row.get("width_justification") and str(c["shape"]).startswith("multi-quarter") else [f"contract {c['shape']} / no justification"]
    return spec, check


def pub_wj_unjustified_refused(root):
    spec = _wj_spec(root, "lsa-wj-none")

    def check(row, err):
        return [] if err is not None and "books" in err and "width_justification" in err else [f"expected the width refusal, got row={bool(row)} err={err}"]
    return spec, check


def pub_wj_short_refused(root):
    spec = _wj_spec(root, "lsa-wj-short", width_justification="faster")

    def check(row, err):
        return [] if err is not None and "width_justification" in err else [f"expected refusal of a short justification, got {err}"]
    return spec, check



def pub_override_multiquarter_persisted(root):
    spec = _wj_spec(root, "lsa-ovr-ok", shape_override="operator: pestopoppa 2026-11-06: widen LSA pca arm to 2 quarters (longest arm)")

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(row)
        return [] if row.get("shape") == "multi-quarter(2)" and c["shape"] == "multi-quarter(2)" else [f"persisted shape {row.get('shape')} / contract {c['shape']}"]
    return spec, check


def pub_gpu_wj_q0(root):
    d = os.path.join(root, "gpu-wj")
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write("print(1)\n")
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexec /bin/bash {eng} --id gpu-wj --class gpu --no-fold-siblings --gpu-quiet shared "
                        f"--min-window 900 --cmd \"/usr/bin/python3 -B $D/job.py\" --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": "gpu-wj", "owner": "t", "launcher": lp, "lane": "gpu", "regions": "mi210_0,0-23,72-87,184-191",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture", "estimate_s": 3000,
            "handoff_task": "handoffs/active/x.md:GPU", "first_progress_s": 600,
            "width_justification": "correctness reference runs on the ggml CPU backend and needs a quarter"}

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        opt = rf.contract_of(row)["options"][0]
        bad = [] if "q0" in opt else ["justified q0 not booked"]
        if "q3" in opt or {"c72", "c80"} & rf.expand(opt):
            bad.append("q3 72-87 booked")
        return bad
    return spec, check


def pub_gpu_unjustified_q0_refused(root):
    spec, _ = pub_gpu_wj_q0(root)
    spec = {**spec, "regions": "mi210_0,0-23,184-191"}
    spec.pop("width_justification")
    return spec, (lambda row, err: [] if err is not None and "width_justification" in err else [f"expected refusal, got {err}"])


PUBLISH_SCENARIOS = {"publish-override-multiquarter-persisted": pub_override_multiquarter_persisted,
                     "publish-gpu-wj-q0-q2-only": pub_gpu_wj_q0,
                     "publish-gpu-unjustified-q0-refused": pub_gpu_unjustified_q0_refused,
                     "publish-wj-justified-multiquarter-accepted": pub_wj_justified_accepted,
                     "publish-wj-unjustified-multiquarter-refused": pub_wj_unjustified_refused,
                     "publish-wj-short-justification-refused": pub_wj_short_refused,
                     "publish-npd1-step5-accepted": pub_npd1_step5,
                     "publish-helper-omp-not-thread-evidence": pub_inf75_helper_omp,
                     "publish-yarn-compute-process-threads-win": pub_yarn_job_side_threads,
                     "publish-stt5-cpu-declared-never-gpu-quiet": pub_stt5_cpu_declared_no_gpu,
                     "publish-iqk-declared-quarter-never-shrunk": pub_iqk_declared_quarter_floor,
                     "publish-iqk-ab-r3-explicit-q2-verbatim": pub_iqk_ab_r3_explicit_q2,
                     "publish-inf75-c6-r2-explicit-override-verbatim": pub_inf75_c6_r2_explicit_override}


def build_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    return {name: fn(os.path.join(out_dir, name + ".trace.jsonl")) for name, fn in SCENARIOS.items()}
